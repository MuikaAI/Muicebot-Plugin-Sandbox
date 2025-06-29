from pydantic import BaseModel
from nonebot import get_plugin_config
from typing import Literal, Optional

class Config(BaseModel):
    runner_docker_base_url: str = "unix:///var/run/docker.sock"
    runner_enable_multimodal: bool = False
    runner_container_networkmode: Literal["bridge", "host", "none"] = "bridge"
    runner_container_waitfor: float = 30.0

config = get_plugin_config(Config)