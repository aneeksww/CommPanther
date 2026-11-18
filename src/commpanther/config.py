import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Paths:
    """Standard paths for CommPanther on Windows."""

    @property
    def base_dir(self) -> Path:
        # %LOCALAPPDATA%\CommPanther
        local_app_data = os.getenv("LOCALAPPDATA")
        if not local_app_data:
            raise RuntimeError("LOCALAPPDATA environment variable not found.")
        return Path(local_app_data) / "CommPanther"

    @property
    def logs_dir(self) -> Path:
        return self.base_dir / "logs"

    @property
    def runtime_dir(self) -> Path:
        return self.base_dir / "runtime"

    @property
    def auth_dir(self) -> Path:
        return self.base_dir / "auth"

    @property
    def lock_file_path(self) -> Path:
        return self.runtime_dir / "service.lock"

    @property
    def log_file_path(self) -> Path:
        return self.logs_dir / "commpanther.log"


paths = Paths()


def ensure_dirs_exist():
    """Create necessary directories if they don't exist."""
    paths.logs_dir.mkdir(parents=True, exist_ok=True)
    paths.runtime_dir.mkdir(parents=True, exist_ok=True)
    paths.auth_dir.mkdir(parents=True, exist_ok=True)