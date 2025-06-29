import platform
from io import BytesIO
from pathlib import Path

from muicebot.models import Resource


def read_attachment(file: Resource) -> bytes:
    """
    读取附件
    """
    file_obj = file.get_file()
    if isinstance(file_obj, str):
        return Path(file_obj).read_bytes()
    elif isinstance(file_obj, BytesIO):
        return file_obj.read()
    else:
        return file_obj


def convert_path_to_wsl(path: Path) -> str:
    path = path.resolve()
    if platform.system() == "Windows":
        drive = path.drive.lower().replace(":", "")
        rest = path.parts[1:]  # Remove drive
        return f"/mnt/{drive}/{'/'.join(rest)}"
    else:
        return str(path)
