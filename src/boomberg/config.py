"""Configuration settings for Boomberg CLI."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def get_default_data_dir() -> Path:
    """Get the default data directory for the application."""
    data_dir = Path.home() / ".boomberg"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    fmp_api_key: str
    fmp_base_url: str = "https://financialmodelingprep.com/stable"
    fred_api_key: str = ""
    fred_base_url: str = "https://api.stlouisfed.org/fred"
    eodhd_api_key: str = ""
    eodhd_base_url: str = "https://eodhd.com/api"
    refresh_interval: float = 10.0  # seconds between auto-refresh
    watchlist_path: str = str(get_default_data_dir() / "watchlists.json")


def get_settings() -> Settings:
    """Get application settings singleton."""
    return Settings()
