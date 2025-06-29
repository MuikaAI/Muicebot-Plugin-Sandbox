from typing import Literal

from nonebot import get_plugin_config
from pydantic import BaseModel


class Config(BaseModel):
    sandbox_docker_base_url: str = "unix:///var/run/docker.sock"
    sandbox_container_networkmode: Literal["bridge", "host", "none"] = "bridge"
    sandbox_container_waitfor: float = 30.0


config = get_plugin_config(Config)
