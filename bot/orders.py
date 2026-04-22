"""Order placement and response formatting."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, Dict, Optional

from bot.client import BinanceFuturesClient, BinanceAPIError
from bot.validators import validate_all
from bot.logging_config import get_logger

logger = get_logger("orders")


def _fmt(value: Any, default: str = "-") -> str:
    """Return dash if value is None or empty, otherwise return as string."""
    if value is None or value == "":
        return default
    return str(value)


def format_order_summary(params: dict) -> str:
    """Print a box showing what we're about to send."""
    lines = [
        "",
        "+-----------------------------------------+",
        "|           ORDER REQUEST SUMMARY          |",
        "+-----------------------------------------+",
        f"|  Symbol     : {_fmt(params.get('symbol')):<26}|",
        f"|  Side       : {_fmt(params.get('side')):<26}|",
        f"|  Type       : {_fmt(params.get('order_type')):<26}|",
        f"|  Quantity   : {_fmt(params.get('quantity')):<26}|",
        f"|  Price      : {_fmt(params.get('price')):<26}|",
        f"|  Stop Price : {_fmt(params.get('stop_price')):<26}|",
        "+-----------------------------------------+",
    ]
    return "\n".join(lines)


def format_order_response(response: dict) -> str:
    """Print the key fields from the API response."""
    lines = [
        "",
        "+-----------------------------------------+",
        "|           ORDER RESPONSE DETAILS         |",
        "+-----------------------------------------+",
        f"|  Order ID    : {_fmt(response.get('orderId')):<25}|",
        f"|  Client OID  : {_fmt(response.get('clientOrderId')):<25}|",
        f"|  Symbol      : {_fmt(response.get('symbol')):<25}|",
        f"|  Side        : {_fmt(response.get('side')):<25}|",
        f"|  Type        : {_fmt(response.get('type')):<25}|",
        f"|  Status      : {_fmt(response.get('status')):<25}|",
        f"|  Orig Qty    : {_fmt(response.get('origQty')):<25}|",
        f"|  Exec Qty    : {_fmt(response.get('executedQty')):<25}|",
        f"|  Avg Price   : {_fmt(response.get('avgPrice')):<25}|",
        f"|  Price       : {_fmt(response.get('price')):<25}|",
        f"|  Stop Price  : {_fmt(response.get('stopPrice')):<25}|",
        f"|  Time In Frc : {_fmt(response.get('timeInForce')):<25}|",
        f"|  Update Time : {_fmt(response.get('updateTime')):<25}|",
        "+-----------------------------------------+",
    ]
    return "\n".join(lines)


def place_order(
    client: BinanceFuturesClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: str | float,
    price: Optional[str | float] = None,
    stop_price: Optional[str | float] = None,
    time_in_force: str = "GTC",
    reduce_only: bool = False,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Validate inputs, place the order, and return the API response.

    If dry_run=True, validates and prints the summary but skips the API call.
    Raises ValueError on bad input, BinanceAPIError on API failures.
    """
    # validate everything first before touching the network
    validated = validate_all(
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=price,
        stop_price=stop_price,
    )

    print(format_order_summary(validated))
    logger.info("order request: %s", json.dumps(
        {k: str(v) for k, v in validated.items()}, indent=2
    ))

    # stop here if dry run
    if dry_run:
        logger.warning("dry run — order not submitted to API.")
        print("\n  DRY RUN — order was not submitted to the exchange.\n")
        return {"dry_run": True, **{k: str(v) for k, v in validated.items()}}

    # place the order
    try:
        response = client.place_order(
            symbol=str(validated["symbol"]),
            side=str(validated["side"]),
            order_type=str(validated["order_type"]),
            quantity=str(validated["quantity"]),
            price=str(validated["price"]) if validated["price"] else None,
            stop_price=str(validated["stop_price"]) if validated["stop_price"] else None,
            time_in_force=time_in_force,
            reduce_only=reduce_only,
        )
    except BinanceAPIError as exc:
        logger.error("API error: code=%s msg=%s", exc.code, exc.message)
        print(f"\n  API ERROR [{exc.code}]: {exc.message}\n")
        raise
    except (ConnectionError, TimeoutError) as exc:
        logger.error("network error: %s", exc)
        print(f"\n  NETWORK ERROR: {exc}\n")
        raise

    print(format_order_response(response))

    status = response.get("status", "UNKNOWN")
    if status in ("FILLED", "PARTIALLY_FILLED", "NEW"):
        print(f"\n  order submitted successfully (status: {status})\n")
    else:
        print(f"\n  order status: {status}\n")

    logger.info("order response: %s", json.dumps(response, indent=2))
    return response
