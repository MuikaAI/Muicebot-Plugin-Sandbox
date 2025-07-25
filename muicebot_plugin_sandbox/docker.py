import io
import re
import tarfile
from asyncio import wait_for
from pathlib import Path
from time import perf_counter

import aiodocker
from muicebot.models import Resource
from nonebot import logger

from .config import config
from .utils import convert_path_to_wsl

SANDBOX_PATH = Path(__file__).parent / "sandbox"
DOCKERFILE_PATH = SANDBOX_PATH / "Dockerfile"

IMAGE_TAG = "muicebot/sandbox-python"
IMAGE_VERSION = "v1.2"


class Sandbox:
    def __init__(self) -> None:
        self.client = aiodocker.Docker(url=config.sandbox_docker_base_url)

    def _build_context(self, base_dir: Path) -> io.BytesIO:
        """
        将指定目录打包为 Docker 上下文 tar 包。
        Dockerfile 必须位于 base_dir 根目录中。

        :param base_dir: 需要打包的目录路径
        :return: tar 格式的 BytesIO 流
        """
        if not base_dir.is_dir():
            raise ValueError("base_dir 必须是一个目录")

        tar_stream = io.BytesIO()

        with tarfile.open(fileobj=tar_stream, mode="w") as tar:
            for path in base_dir.rglob("*"):
                if path.is_file():
                    relative_path = path.relative_to(base_dir)
                    tar.add(name=str(path), arcname=str(relative_path))

        tar_stream.seek(0)
        return tar_stream

    async def _build_image(self, total_retry: int = 3):
        """
        构建 Sandbox 镜像

        :param total_retry: 最高重试次数
        """
        logger.debug("正在检查是否需要构建 Docker Sandbox 镜像...")

        for image in await self.client.images.list():
            tag = image["RepoTags"][0] if image["RepoTags"] else ""
            if tag == f"{IMAGE_TAG}:{IMAGE_VERSION}":
                logger.debug("检测到沙盒镜像存在，无需构建")
                return

        logger.info("Building Docker image...")

        ctx_tar = self._build_context(SANDBOX_PATH)

        build_logs = self.client.images.build(
            fileobj=ctx_tar,
            encoding="gzip",
            tag=f"{IMAGE_TAG}:{IMAGE_VERSION}",
            stream=True,
        )

        logger.debug("Build logs:")
        async for line in build_logs:
            if "stream" not in line:
                continue

            logger.debug(line["stream"].strip())

            if not ("Exception" in line["stream"] or "Error" in line["stream"]):
                continue

            logger.error("Docker 镜像构建失败！")
            if not total_retry:
                raise RuntimeError("镜像构建失败！")

            logger.warning("正在重试...")
            await self._build_image(total_retry - 1)
            return

    def _extract_output_file(
        self, container_log: str, exec_dir: Path
    ) -> list[Resource]:
        """
        提取输出文件
        """
        if container_log.find("<output>") == -1:
            return []

        pattern = re.compile(r"<output>(.*?)</output>", re.DOTALL)
        output_files = pattern.findall(container_log)
        outputs = []
        for output in output_files:
            outputs.append(Resource("file", path=exec_dir / output))

        return outputs

    async def run_sandbox(self, exec_dir: Path) -> tuple[str, list[Resource]]:
        """
        运行沙盒

        :return: 沙盒运行日志，输出附件
        """
        await self._build_image()

        try:
            logger.info("正在创建一次性容器...")

            host_path = convert_path_to_wsl(exec_dir)
            container = await self.client.containers.create(
                {
                    "Image": f"{IMAGE_TAG}:{IMAGE_VERSION}",
                    "HostConfig": {
                        "Binds": [f"{host_path}:/workspace:rw"],
                        "AutoRemove": False,
                        "NetworkMode": config.sandbox_container_networkmode,
                        "Memory": 128 * 1024 * 1024,  # 128M
                        "PidsLimit": 32,  # 32 个进程
                    },
                }
            )

            logger.info("启动一次性容器...")
            await container.start()

            logger.info("正等待容器执行完成...")
            start_time = perf_counter()
            try:
                result = await wait_for(
                    container.wait(), config.sandbox_container_waitfor
                )
                logger.debug(
                    f"Container exit code: {result.get('StatusCode', 'unknown')}"
                )
            except TimeoutError:
                logger.warning("容器执行超时，强行退出...")
                # 如果超时，尝试停止容器
                try:
                    await container.kill()
                except Exception as e:
                    logger.warning(f"无法关闭容器或容器已关闭: {e}")
            end_time = perf_counter()

            logger.debug(
                f"容器执行完成，用时 {end_time - start_time}s, 正在获取容器日志"
            )
            logs = await container.log(stdout=True, stderr=True)
            log = "".join(logs) if logs else "(容器无返回或容器执行超时)"
            outputs = self._extract_output_file(log, exec_dir)

            logger.debug("容器执行结果:")
            logger.debug(log)
            logger.debug(f"输出的文件:{outputs}")

            logger.debug("删除一次性容器...")
            await container.delete()
            return log, outputs

        except TimeoutError:
            return "❌ Error: 容器操作超时...", []

        except Exception as e:
            return f"❌ Error: {e}", []
