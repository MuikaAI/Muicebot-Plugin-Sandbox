import aiodocker
import re
from .config import config
from pathlib import Path
from nonebot import logger
from muicebot.models import Resource
from asyncio import wait_for
import tarfile
import io
from .utils import convert_path_to_wsl

SANDBOX_PATH = Path(__file__).parent / "sandbox"
DOCKERFILE_PATH = SANDBOX_PATH / "Dockerfile"

IMAGE_TAG = "muicebot/sandbox-python"
IMAGE_VERSION = "v1.1"

class Sandbox:
    def __init__(self) -> None:
        self.client = aiodocker.Docker(url = config.runner_docker_base_url)

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
        for image in (await self.client.images.list()):
            tag = image['RepoTags'][0] if image['RepoTags'] else ''
            if tag == f"{IMAGE_TAG}:{IMAGE_VERSION}":
                logger.debug("Skip build image")
                return

        logger.info("Building Docker image...")

        ctx_tar = self._build_context(SANDBOX_PATH)

        build_logs = self.client.images.build(
                fileobj=ctx_tar,
                encoding="gzip",
                tag=f"{IMAGE_TAG}:{IMAGE_VERSION}",
                stream=True
            )

        logger.debug("Build logs:")
        async for line in build_logs:
            if "stream" not in line:
                continue

            logger.debug(line["stream"].strip())

            if not("Exception" in line["stream"] or "Error" in line["stream"]):
                continue

            logger.error("Docker 镜像构建失败！")
            if not total_retry:
                raise RuntimeError("镜像构建失败！")
            
            logger.warning(f"正在重试...")
            await self._build_image(total_retry - 1)
            return

    def _extract_output_file(self, container_log:str, exec_dir: Path) -> list[Resource]:
        """
        提取输出文件
        """
        if container_log.find("<output>") == -1:
            return []

        pattern = re.compile(r"<output>(.*?)</output>", re.DOTALL)
        output_files = pattern.findall(container_log)
        outputs = []
        for output in output_files:
            outputs.append(
                Resource("file", path = exec_dir / output)
            )

        return outputs

    async def run_sandbox(self, exec_dir: Path) -> tuple[str, list[Resource]]:
        """
        运行沙盒

        :return: 沙盒运行日志，输出附件
        """
        await self._build_image()

        try:
            logger.debug("Creating container...")

            host_path = convert_path_to_wsl(exec_dir)
            container = await self.client.containers.create({
                "Image": f"{IMAGE_TAG}:{IMAGE_VERSION}",
                "HostConfig": {
                    "Binds": [f"{host_path}:/workspace:rw"],
                    "AutoRemove": False,
                    "NetworkMode": config.runner_container_networkmode,
                    "Memory": 128 * 1024 * 1024,  # 128M
                    "PidsLimit": 32  # 32 个进程
                }
            })

            logger.debug("Starting container...")
            await container.start()

            logger.debug("Waiting for container to finish...")
            try:
                # 等待容器退出
                result = await wait_for(container.wait(), config.runner_container_waitfor)
                logger.debug(f"Container exit code: {result.get('StatusCode', 'unknown')}")
            except TimeoutError:
                logger.debug("Container execution timed out, trying to get logs anyway...")
                # 如果超时，尝试停止容器
                try:
                    await container.kill()
                except Exception as e:
                    pass

            logger.debug("Getting container logs...")
            logs = await container.log(stdout=True, stderr=True)
            log = "".join(logs) if logs else ""
            outputs = self._extract_output_file(log, exec_dir)

            logger.debug("容器执行结果:")
            logger.debug(log)
            logger.debug(f"输出的文件:{outputs}")
            
            await container.delete()
            return log, outputs
        
        except TimeoutError:
            return "❌ Error: 容器操作超时...", []

        except Exception as e:
            return f"❌ Error: {e}", []
