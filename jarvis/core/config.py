"""Config loader. Reads YAML, expands ~ and env vars, exposes a Config object."""
from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Any

import yaml

log = logging.getLogger(__name__)


def _xdg(var: str, default_sub: str) -> Path:
    base = os.environ.get(var)
    if base:
        return Path(base)
    return Path.home() / default_sub


DEFAULT_CONFIG_PATH = _xdg("XDG_CONFIG_HOME", ".config") / "jarvis" / "config.yaml"
PACKAGED_DEFAULT = Path(__file__).resolve().parents[2] / "config" / "default_config.yaml"


class Config:
    """Thin wrapper around a nested dict. Supports dotted-path get/set + save."""

    def __init__(self, data: dict, path: Path):
        self.data = data
        self.path = path

    # --- dotted-path access -------------------------------------------------
    def get(self, dotted: str, default: Any = None) -> Any:
        cur: Any = self.data
        for part in dotted.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return default
            cur = cur[part]
        return cur

    def set(self, dotted: str, value: Any) -> None:
        parts = dotted.split(".")
        cur = self.data
        for part in parts[:-1]:
            if part not in cur or not isinstance(cur[part], dict):
                cur[part] = {}
            cur = cur[part]
        cur[parts[-1]] = value

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(self.data, f, sort_keys=False, allow_unicode=True)
        log.info("Config saved to %s", self.path)

    # --- resolved paths -----------------------------------------------------
    def data_dir(self) -> Path:
        override = self.get("paths.data_dir")
        if override:
            return Path(os.path.expanduser(override))
        return _xdg("XDG_DATA_HOME", ".local/share") / "jarvis"

    def log_dir(self) -> Path:
        override = self.get("paths.log_dir")
        if override:
            return Path(os.path.expanduser(override))
        return self.data_dir() / "logs"

    def resolve_secret(self, dotted_key: str, dotted_env: str) -> str:
        """Read a secret from config; if blank, read from env var named in config."""
        direct = self.get(dotted_key, "") or ""
        if direct:
            return direct
        env_name = self.get(dotted_env, "") or ""
        if env_name:
            return os.environ.get(env_name, "")
        return ""


def load_config(path: str | None = None) -> Config:
    cfg_path = Path(os.path.expanduser(path)) if path else DEFAULT_CONFIG_PATH

    # First run: copy packaged default into XDG config dir.
    if not cfg_path.exists():
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        if PACKAGED_DEFAULT.exists():
            shutil.copy(PACKAGED_DEFAULT, cfg_path)
            log.info("Initialised config at %s from packaged default", cfg_path)
        else:
            cfg_path.write_text("{}\n", encoding="utf-8")

    with cfg_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    cfg = Config(data, cfg_path)
    cfg.data_dir().mkdir(parents=True, exist_ok=True)
    cfg.log_dir().mkdir(parents=True, exist_ok=True)
    return cfg
