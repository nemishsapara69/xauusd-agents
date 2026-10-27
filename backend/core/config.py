"""Application configuration loaded from YAML files and environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any

import yaml
from dotenv import dotenv_values, load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = BACKEND_DIR / "config"


def load_environment(path: Path | None = None) -> None:
    """Load env vars from a .env file while tolerating UTF-8 BOMs."""
    env_path = (path or BACKEND_DIR / ".env").resolve()
    if not env_path.exists():
        return
    try:
        raw = env_path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        raw = env_path.read_text(encoding="utf-8")
    values = dotenv_values(stream=StringIO(raw))
    for key, value in values.items():
        if key is None or value is None:
            continue
        normalized_key = key.lstrip("\ufeff")
        os.environ.setdefault(normalized_key, value)
    load_dotenv(dotenv_path=env_path, override=False)


class ConfigurationError(RuntimeError):
    """Raised when required application configuration is invalid."""


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}
    except OSError as exc:
        raise ConfigurationError(f"Unable to read configuration file: {path}") from exc
    if not isinstance(data, dict):
        raise ConfigurationError(f"Configuration file must contain a mapping: {path}")
    return data


@dataclass(frozen=True)
class AppConfig:
    symbol: str
    default_timeframe: str
    candle_count: int
    ema_periods: tuple[int, ...]
    log_level: str
    risk_rules: dict[str, Any]
    mt5_server: str
    mt5_login: int
    mt5_password: str
    mt5_path: Path
    execution_enabled: bool


def load_config() -> AppConfig:
    """Load non-secret YAML settings and MT5 credentials from the environment."""
    load_environment()
    settings = _read_yaml(CONFIG_DIR / "settings.yaml")
    risk_rules = _read_yaml(CONFIG_DIR / "risk_rules.yaml")

    required = ("MT5_SERVER", "MT5_LOGIN", "MT5_PASSWORD", "MT5_PATH")
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise ConfigurationError(f"Missing required environment variables: {', '.join(missing)}")

    try:
        login = int(os.environ["MT5_LOGIN"])
    except ValueError as exc:
        raise ConfigurationError("MT5_LOGIN must be an integer") from exc

    path = Path(os.environ["MT5_PATH"])
    if not path.is_absolute():
        raise ConfigurationError("MT5_PATH must be an absolute path")

    periods = tuple(int(period) for period in settings.get("ema_periods", [20, 50, 200]))
    if not periods or any(period <= 0 for period in periods):
        raise ConfigurationError("ema_periods must contain positive integers")

    return AppConfig(
        symbol=str(settings.get("symbol", "XAUUSD")),
        default_timeframe=str(settings.get("default_timeframe", "H1")).upper(),
        candle_count=int(settings.get("candle_count", 500)),
        ema_periods=periods,
        log_level=str(settings.get("log_level", "INFO")).upper(),
        risk_rules=risk_rules,
        mt5_server=os.environ["MT5_SERVER"],
        mt5_login=login,
        mt5_password=os.environ["MT5_PASSWORD"],
        mt5_path=path,
        execution_enabled=os.getenv("MT5_EXECUTION_ENABLED", "false").lower() == "true",
    )
