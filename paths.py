import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent


def resource_path(*parts):
    base = Path(getattr(sys, "_MEIPASS", PROJECT_DIR))
    return base.joinpath(*parts)


def data_dir():
    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else PROJECT_DIR
    folder = base / "data"
    folder.mkdir(exist_ok=True)
    return folder
