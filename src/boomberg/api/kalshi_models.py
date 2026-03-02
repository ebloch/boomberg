"""Pydantic models for Kalshi API responses."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class KalshiMarket(BaseModel):
    """Kalshi prediction market."""

    model_config = ConfigDict(populate_by_name=True)

    ticker: str
    title: str
    status: str
    yes_bid: Optional[int] = Field(default=None)
    no_bid: Optional[int] = Field(default=None)
    yes_ask: Optional[int] = Field(default=None)
    no_ask: Optional[int] = Field(default=None)
    last_price: Optional[int] = Field(default=None)
    previous_price: Optional[int] = Field(default=None)
    volume_24h: int = Field(default=0)
    open_interest: Optional[int] = Field(default=None)
    close_time: Optional[str] = Field(default=None)
    series_ticker: Optional[str] = Field(default=None)

    @property
    def yes_price_dollars(self) -> Optional[float]:
        """Return yes bid price in dollars (cents / 100)."""
        if self.yes_bid is None:
            return None
        return self.yes_bid / 100

    @property
    def no_price_dollars(self) -> Optional[float]:
        """Return no bid price in dollars (cents / 100)."""
        if self.no_bid is None:
            return None
        return self.no_bid / 100

    @property
    def last_price_dollars(self) -> Optional[float]:
        """Return last price in dollars (cents / 100)."""
        if self.last_price is None:
            return None
        return self.last_price / 100

    @property
    def change_cents(self) -> int:
        """Return price change in cents."""
        if self.last_price is None or self.previous_price is None:
            return 0
        return self.last_price - self.previous_price
