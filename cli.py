#!/usr/bin/env python3
"""
Binance Futures Testnet Trading Bot — CLI entry point.

Commands:
  order        place a single order
  interactive  step-by-step order wizard
  account      show account balances and positions
  open-orders  list open orders

Examples:
  python cli.py order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
  python cli.py order --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.1 --price 3500
  python cli.py order --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.01 --stop-price 88000
  python cli.py order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01 --dry-run
  python cli.py interactive
  python cli.py account
  python cli.py open-orders --symbol BTCUSDT
"""

from __future__ import annotations

import os
import sys
import argparse
from typing import Optional

sys.path.insert(0, os.path.dirname(__file__))

from bot.logging_config import setup_logging, get_logger
from bot.client import BinanceFuturesClient, BinanceAPIError
from bot.orders import place_order

setup_logging(log_dir="logs")
logger = get_logger("cli")

# terminal colors
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def green(s):  return f"{GREEN}{s}{RESET}"
def red(s):    return f"{RED}{s}{RESET}"
def yellow(s): return f"{YELLOW}{s}{RESET}"
def cyan(s):   return f"{CYAN}{s}{RESET}"
def bold(s):   return f"{BOLD}{s}{RESET}"


BANNER = f"""
{CYAN}{BOLD}
 ██████╗  ██████╗ ████████╗    ████████╗██████╗  █████╗ ██████╗ ███████╗██████╗
 ██╔══██╗██╔═══██╗╚══██╔══╝    ╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔══██╗
 ██████╔╝██║   ██║   ██║          ██║   ██████╔╝███████║██║  ██║█████╗  ██████╔╝
 ██╔══██╗██║   ██║   ██║          ██║   ██╔══██╗██╔══██║██║  ██║██╔══╝  ██╔══██╗
 ██████╔╝╚██████╔╝   ██║          ██║   ██║  ██║██║  ██║██████╔╝███████╗██║  ██║
 ╚═════╝  ╚═════╝    ╚═╝          ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚══════╝╚═╝  ╚═╝
{RESET}{YELLOW}                   Binance Futures Testnet - USDT-M{RESET}
"""


def load_credentials(api_key: Optional[str], api_secret: Optional[str]) -> tuple[str, str]:
    """
    Load API credentials. Checks in this order:
    1. --api-key / --api-secret flags
    2. BINANCE_API_KEY / BINANCE_API_SECRET env vars
    3. .env file in the project root
    """
    key = api_key or os.getenv("BINANCE_API_KEY")
    secret = api_secret or os.getenv("BINANCE_API_SECRET")

    if not (key and secret):
        env_file = os.path.join(os.path.dirname(__file__), ".env")
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("#") or "=" not in line:
                        continue
                    k, _, v = line.partition("=")
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k == "BINANCE_API_KEY" and not key:
                        key = v
                    elif k == "BINANCE_API_SECRET" and not secret:
                        secret = v

    if not key or not secret:
        print(red("\n  API credentials not found.\n"))
        print("  Provide via one of:")
        print("    1. --api-key / --api-secret flags")
        print("    2. BINANCE_API_KEY / BINANCE_API_SECRET env vars")
        print("    3. .env file in the project root\n")
        sys.exit(1)

    return key, secret


def cmd_order(args: argparse.Namespace) -> None:
    print(BANNER)

    # dry run skips real credentials
    if args.dry_run:
        key, secret = "DRY_RUN_KEY", "DRY_RUN_SECRET"
    else:
        key, secret = load_credentials(args.api_key, args.api_secret)

    client = BinanceFuturesClient(api_key=key, api_secret=secret)

    try:
        place_order(
            client=client,
            symbol=args.symbol,
            side=args.side,
            order_type=args.type,
            quantity=args.qty,
            price=args.price,
            stop_price=args.stop_price,
            time_in_force=args.tif,
            reduce_only=args.reduce_only,
            dry_run=args.dry_run,
        )
    except (ValueError, BinanceAPIError, ConnectionError, TimeoutError):
        sys.exit(1)


def cmd_interactive(args: argparse.Namespace) -> None:
    print(BANNER)
    key, secret = load_credentials(args.api_key, args.api_secret)
    client = BinanceFuturesClient(api_key=key, api_secret=secret)

    print(bold("\n  Interactive Order Wizard\n"))

    def prompt(label: str, default: Optional[str] = None, choices: Optional[list] = None) -> str:
        hint = f" [{'/'.join(choices)}]" if choices else ""
        hint += f" (default: {default})" if default else ""
        while True:
            val = input(f"  {label}{hint}: ").strip()
            if not val and default:
                val = default
            if choices and val.upper() not in [c.upper() for c in choices]:
                print(yellow(f"    please choose from: {choices}"))
                continue
            if val:
                return val.upper() if choices else val
            print(yellow("    value cannot be empty."))

    symbol     = prompt("Symbol (e.g. BTCUSDT)").upper()
    side       = prompt("Side", choices=["BUY", "SELL"])
    order_type = prompt("Order Type", choices=["MARKET", "LIMIT", "STOP_MARKET"])
    qty        = prompt("Quantity (e.g. 0.01)")

    price = None
    if order_type == "LIMIT":
        price = prompt("Limit Price")

    stop_price = None
    if order_type in ("STOP_MARKET", "STOP"):
        stop_price = prompt("Stop Price")

    dry_raw = prompt("Dry run? (no real order)", default="n", choices=["y", "n"])
    dry_run = dry_raw.lower() == "y"

    print()
    try:
        place_order(
            client=client,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=qty,
            price=price,
            stop_price=stop_price,
            dry_run=dry_run,
        )
    except (ValueError, BinanceAPIError, ConnectionError, TimeoutError):
        sys.exit(1)


def cmd_account(args: argparse.Namespace) -> None:
    print(BANNER)
    key, secret = load_credentials(args.api_key, args.api_secret)
    client = BinanceFuturesClient(api_key=key, api_secret=secret)

    try:
        account = client.get_account()
    except (BinanceAPIError, ConnectionError) as exc:
        print(red(f"\n  error: {exc}\n"))
        sys.exit(1)

    print(bold("\n  Account Summary\n"))
    print(f"  Total Wallet Balance  : {cyan(account.get('totalWalletBalance', '-'))} USDT")
    print(f"  Unrealized PnL        : {cyan(account.get('totalUnrealizedProfit', '-'))} USDT")
    print(f"  Margin Balance        : {cyan(account.get('totalMarginBalance', '-'))} USDT")
    print(f"  Available Balance     : {cyan(account.get('availableBalance', '-'))} USDT")

    positions = [p for p in account.get("positions", []) if float(p.get("positionAmt", 0)) != 0]
    if positions:
        print(bold(f"\n  Open Positions ({len(positions)}):"))
        for pos in positions:
            amt = float(pos.get("positionAmt", 0))
            direction = green("LONG") if amt > 0 else red("SHORT")
            print(
                f"    {pos['symbol']:12} | {direction} | amt={amt}"
                f" | entry={pos.get('entryPrice')} | PnL={pos.get('unrealizedProfit')}"
            )
    else:
        print("\n  No open positions.")
    print()


def cmd_open_orders(args: argparse.Namespace) -> None:
    print(BANNER)
    key, secret = load_credentials(args.api_key, args.api_secret)
    client = BinanceFuturesClient(api_key=key, api_secret=secret)

    try:
        orders = client.get_open_orders(symbol=args.symbol)
    except (BinanceAPIError, ConnectionError) as exc:
        print(red(f"\n  error: {exc}\n"))
        sys.exit(1)

    if not orders:
        print(yellow("\n  No open orders.\n"))
        return

    print(bold(f"\n  Open Orders ({len(orders)})\n"))
    for o in orders:
        side_str = green(o["side"]) if o["side"] == "BUY" else red(o["side"])
        print(
            f"  ID={o['orderId']} | {o['symbol']} | {side_str}"
            f" | type={o['type']} | qty={o['origQty']}"
            f" | price={o.get('price', '-')} | status={o['status']}"
        )
    print()


def _add_cred_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--api-key",    default=None, help="Binance API key (overrides env)")
    parser.add_argument("--api-secret", default=None, help="Binance API secret (overrides env)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Binance Futures Testnet Trading Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # order subcommand
    p_order = subparsers.add_parser("order", help="Place a single order")
    _add_cred_args(p_order)
    p_order.add_argument("--symbol",      required=True, help="e.g. BTCUSDT")
    p_order.add_argument("--side",        required=True, choices=["BUY", "SELL"], type=str.upper)
    p_order.add_argument("--type",        required=True, dest="type", type=str.upper,
                         choices=["MARKET", "LIMIT", "STOP_MARKET", "STOP", "TAKE_PROFIT", "TAKE_PROFIT_MARKET"])
    p_order.add_argument("--quantity",    required=True, type=str, dest="qty")
    p_order.add_argument("--price",       default=None, type=str, help="required for LIMIT orders")
    p_order.add_argument("--stop-price",  default=None, type=str, dest="stop_price",
                         help="required for STOP_MARKET orders")
    p_order.add_argument("--tif",         default="GTC", choices=["GTC", "IOC", "FOK", "GTX"],
                         help="time-in-force (default: GTC)")
    p_order.add_argument("--reduce-only", action="store_true", dest="reduce_only")
    p_order.add_argument("--dry-run",     action="store_true", dest="dry_run",
                         help="validate only, do not submit the order")
    p_order.set_defaults(func=cmd_order)

    # interactive wizard
    p_inter = subparsers.add_parser("interactive", help="Step-by-step order wizard")
    _add_cred_args(p_inter)
    p_inter.set_defaults(func=cmd_interactive)

    # account info
    p_acc = subparsers.add_parser("account", help="Show account summary")
    _add_cred_args(p_acc)
    p_acc.set_defaults(func=cmd_account)

    # open orders
    p_oo = subparsers.add_parser("open-orders", help="List open orders")
    _add_cred_args(p_oo)
    p_oo.add_argument("--symbol", default=None, help="filter by symbol")
    p_oo.set_defaults(func=cmd_open_orders)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    logger.debug("CLI args: %s", vars(args))
    args.func(args)


if __name__ == "__main__":
    main()
