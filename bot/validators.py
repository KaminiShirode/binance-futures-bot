"""Validate order parameters before sending to the API."""

from __future__ import annotations
from decimal import Decimal, InvalidOperation
from typing import Optional

from bot.logging_config import get_logger

logger = get_logger("validators")

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET", "STOP", "TAKE_PROFIT", "TAKE_PROFIT_MARKET"}

# # basic sanity checks
MIN_QUANTITY = Decimal("0.001")
MIN_PRICE = Decimal("0.01")


def validate_symbol(symbol: str) -> str:
    """Check symbol is a non-empty alphanumeric string like BTCUSDT."""
    symbol = symbol.strip().upper()
    if not symbol:
        raise ValueError("symbol cannot be empty.")
    if not symbol.isalnum():
        raise ValueError(f"symbol must be alphanumeric, got: '{symbol}'")
    if len(symbol) < 4 or len(symbol) > 20:
        raise ValueError(f"symbol length out of range (4-20): '{symbol}'")
    logger.debug("symbol validated: %s", symbol)
    return symbol


def validate_side(side: str) -> str:
    """Must be BUY or SELL."""
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValueError(f"side must be one of {VALID_SIDES}, got: '{side}'")
    logger.debug("side validated: %s", side)
    return side


def validate_order_type(order_type: str) -> str:
    """Check order type is something the API actually accepts."""
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValueError(
            f"order type must be one of {VALID_ORDER_TYPES}, got: '{order_type}'"
        )
    logger.debug("order type validated: %s", order_type)
    return order_type


def validate_quantity(quantity: str | float) -> Decimal:
    """Parse quantity and make sure it's a positive number."""
    try:
        qty = Decimal(str(quantity))
    except InvalidOperation:
        raise ValueError(f"quantity is not a valid number: '{quantity}'")
    if qty <= 0:
        raise ValueError(f"quantity must be positive, got: {qty}")
    if qty < MIN_QUANTITY:
        raise ValueError(f"quantity too small (min {MIN_QUANTITY}), got: {qty}")
    logger.debug("quantity validated: %s", qty)
    return qty


def validate_price(price: str | float | None, order_type: str) -> Optional[Decimal]:
    """
    Price is required for LIMIT/STOP/TAKE_PROFIT orders.
    For MARKET orders it's ignored — we log a warning if someone passes it anyway.
    """
    order_type = order_type.strip().upper()
    needs_price = order_type in {"LIMIT", "STOP", "TAKE_PROFIT"}

    if price is None or price == "":
        if needs_price:
            raise ValueError(f"price is required for {order_type} orders.")
        return None

    try:
        p = Decimal(str(price))
    except InvalidOperation:
        raise ValueError(f"price is not a valid number: '{price}'")
    if p <= 0:
        raise ValueError(f"price must be positive, got: {p}")
    if p < MIN_PRICE:
        raise ValueError(f"price too small (min {MIN_PRICE}), got: {p}")

    if not needs_price:
        logger.warning("price %s provided for %s order — it will be ignored.", p, order_type)

    logger.debug("price validated: %s", p)
    return p


def validate_stop_price(stop_price: str | float | None, order_type: str) -> Optional[Decimal]:
    """stop_price is required for STOP_MARKET / STOP / TAKE_PROFIT_MARKET orders."""
    needs_stop = order_type.upper() in {"STOP_MARKET", "STOP", "TAKE_PROFIT_MARKET", "TAKE_PROFIT"}

    if stop_price is None or stop_price == "":
        if needs_stop:
            raise ValueError(f"stop_price is required for {order_type} orders.")
        return None

    try:
        sp = Decimal(str(stop_price))
    except InvalidOperation:
        raise ValueError(f"stop_price is not a valid number: '{stop_price}'")
    if sp <= 0:
        raise ValueError(f"stop_price must be positive, got: {sp}")

    logger.debug("stop price validated: %s", sp)
    return sp


def validate_all(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str | float,
    price: str | float | None = None,
    stop_price: str | float | None = None,
) -> dict:
    """Run all validations and return a clean dict ready to pass to the client."""
    params = {
        "symbol": validate_symbol(symbol),
        "side": validate_side(side),
        "order_type": validate_order_type(order_type),
        "quantity": validate_quantity(quantity),
        "price": validate_price(price, order_type),
        "stop_price": validate_stop_price(stop_price, order_type),
    }
    logger.debug("all parameters validated: %s", params)
    return params
