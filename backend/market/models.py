"""The price update shape shared by the cache, the SSE stream and the API."""

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Literal

Direction = Literal["up", "down", "flat"]


def iso_timestamp(epoch_seconds: float) -> str:
    """Format Unix seconds as ISO 8601 UTC with milliseconds and a `Z` suffix."""
    moment = datetime.fromtimestamp(epoch_seconds, UTC)
    return moment.isoformat(timespec="milliseconds").replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class PriceUpdate:
    """One ticker's latest price, exactly the SSE event payload."""

    ticker: str
    price: float
    previous_price: float
    open_price: float
    direction: Direction
    timestamp: str

    def to_dict(self) -> dict:
        """Plain dict for JSON encoding."""
        return asdict(self)
