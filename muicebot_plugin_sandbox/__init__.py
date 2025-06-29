import tempfile
from pathlib import Path
from typing import Optional

from muicebot.llm import ModelCompletions, ModelRequest
from muicebot.models import Message, Resource
from muicebot.plugin import PluginMetadata
from muicebot.plugin.func_call import on_function_call
from muicebot.plugin.hook import (
    on_after_completion,
    on_before_completion,
    on_before_pretreatment,
)
from nonebot import get_driver
from nonebot.adapters import Event
from pydantic import BaseModel, Field

from .config import Config
from .docker import Sandbox
from .utils import read_attachment

__plugin_meta__ = PluginMetadata(
    name="Muicebot-Plugin-Sandbox",
    description="基于 Docker 容器的 Muicebot Function Call 插件，可让 LLM 在沙盒中执行 Python 代码",
    usage="配置好 Docker 环境即可",
    config=Config,
)

_file_ids: dict[str, dict[str, Resource]] = {}
"""文件 IDs 存储字典"""
_output_files: dict[str, list[Resource]] = {}
"""临时输出文件字典"""

sandbox_manager: Optional[Sandbox] = None

driver = get_driver()


@driver.on_startup
async def _():
    global sandbox_manager
    sandbox_manager = Sandbox()


class Paramparameters(BaseModel):
    code: str = Field(description="Python 代码")
    file_ids: Optional[list[str]] = Field(
        description="（可选）要操作的完整文件名(id_filename.suffix)列表", default=None
    )
    requirements: Optional[list[str]] = Field(
        description="(可选)第三方依赖列表，默认已安装numpy pandas matplotlib",
        default=None,
    )


@on_function_call(
    "可用于运行 Python 代码的工具，具体代码将在 docker 沙盒环境安全运行。"
    "是否允许联网取决于用户具体设置，默认情况下沙盒环境不允许联网。"
    "要操作文件，请从 `./attachments/` 文件夹下通过文件名访问。"
    "要输出文件，请在代码中添加一条打印语句以输出<output>./path/filename.suffix</output>的输出标签，标签内部为输出文件的路径"
    "不要在最终发给用户的输出中包含任何标签和程序细节，标签只存在于用户输入和程序输出中",
    params=Paramparameters,
)
async def run_python_code(
    event: Event,
    code: str,
    file_ids: Optional[list[str]] = None,
    requirements: Optional[list[str]] = None,
) -> str:
    assert sandbox_manager
    session_id = event.get_session_id()

    exec_dir = Path(tempfile.mkdtemp(prefix="sandbox_"))

    # write code
    (exec_dir / "input_code.py").write_text(code, encoding="utf-8")

    # write attachments
    attachments_dir = exec_dir / "attachments"
    attachments_dir.mkdir(exist_ok=True)
    for file_id in file_ids or []:
        if file_id not in _file_ids[session_id].keys():
            return "Files ID 不存在！"

        file = _file_ids[session_id][file_id]
        content = read_attachment(file)
        (attachments_dir / file_id).write_bytes(content)

    # write requirements.txt
    if requirements:
        requirements_data = "\n".join(requirements)
        requirements_file = exec_dir / "requirements.txt"
        requirements_file.write_text(requirements_data, encoding="utf-8")

    result, files = await sandbox_manager.run_sandbox(exec_dir)
    if files:
        session_id = event.get_session_id()
        _output_files[session_id] = files

    return result


@on_before_pretreatment(priority=100)
async def collect_files(message: Message, event: Event):
    file_id = 0
    session_id = event.get_session_id()

    for file in message.resources:
        filename = Path(file.path).name
        user_files = _file_ids.setdefault(session_id, {})
        user_files[f"{file_id}_{filename}"] = file
        message.message += f"<file>{file_id}_{filename}</file>"
        file_id += 1


@on_before_completion(priority=100)
async def add_system_prompt(request: ModelRequest, event: Event):
    session_id = event.get_session_id()
    if not _file_ids.get(session_id, None):
        return

    if request.system:
        request.system += "\n\n---\n"
        request.system += "除此之外，你还将收到由<file>id_filename.suffix</file>的文件标签，标签中的内容可用于调用工具对这些文件进行操作\n"
    else:
        request.system = "除此之外，你还将收到由<file>id_filename.suffix</file>的文件标签，标签中的内容可用于调用工具对这些文件进行操作"


@on_after_completion(priority=100)
async def check_if_outputs(completions: ModelCompletions, event: Event):
    session_id = event.get_session_id()

    outputs = _output_files.pop(session_id, None)
    if outputs:
        completions.resources.extend(outputs)

    _file_ids.pop(session_id, None)
