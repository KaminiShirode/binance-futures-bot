"Binance Futures REST client — signing, retries, error handling."

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from bot.logging_config import get_logger

logger = get_logger("client")

# NOTE (April 2026):
# Binance deprecated the Futures Testnet web UI in August 2025.
# testnet.binancefuture.com now redirects to Demo Trading and requires KYC
# to generate API keys. The API itself still works fine on both URLs below.
# Official docs now list demo-fapi.binance.com as the current testnet base URL.
TESTNET_BASE_URL = "https://testnet.binancefuture.com"  # assignment-specified
DEMO_BASE_URL    = "https://demo-fapi.binance.com"       # current official testnet URL

DEFAULT_RECV_WINDOW = 5000  # ms — how long the server will accept a signed request
REQUEST_TIMEOUT = 10        # seconds
MAX_RETRIES = 3
BACKOFF_FACTOR = 0.5


class BinanceAPIError(Exception):
    """Raised when Binance returns an error code in the response body."""

    def __init__(self, code: int, message: str, http_status: int = 0):
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(f"Binance API error {code}: {message}")


class BinanceFuturesClient:
    """
    Thin wrapper around the Binance Futures REST API.

    Usage:
        client = BinanceFuturesClient(api_key="...", api_secret="...")
        response = client.place_order(symbol="BTCUSDT", side="BUY", ...)
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = TESTNET_BASE_URL,
        recv_window: int = DEFAULT_RECV_WINDOW,
    ):
        if not api_key or not api_secret:
            raise ValueError("api_key and api_secret must not be empty.")

        self.api_key = api_key
        self._api_secret = api_secret.encode()
        self.base_url = base_url.rstrip("/")
        self.recv_window = recv_window
        self._session = self._build_session()

        logger.info("BinanceFuturesClient initialised (base_url=%s)", self.base_url)

    def _build_session(self) -> requests.Session:
        """Set up a session with retry logic for transient errors."""
        session = requests.Session()
        retry = Retry(
            total=MAX_RETRIES,
            backoff_factor=BACKOFF_FACTOR,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "DELETE"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.headers.update({
            "X-MBX-APIKEY": self.api_key,
            "Content-Type": "application/x-www-form-urlencoded",
        })
        return session

    def _sign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Add timestamp, recvWindow, and HMAC-SHA256 signature to params."""
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = self.recv_window
        query_string = urlencode(params)
        signature = hmac.new(
            self._api_secret, query_string.encode(), hashlib.sha256
        ).hexdigest()
        params["signature"] = signature
        return params

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = True,
    ) -> Dict[str, Any]:
        params = params or {}
        if signed:
            params = self._sign(params)

        url = f"{self.base_url}{endpoint}"
        logger.debug("-> %s %s | params=%s", method.upper(), endpoint, self._redact(params))

        try:
            resp = self._session.request(
                method,
                url,
                params=params if method.upper() == "GET" else None,
                data=params if method.upper() != "GET" else None,
                timeout=REQUEST_TIMEOUT,
            )
        except requests.exceptions.ConnectionError as exc:
            logger.error("network error: %s", exc)
            raise ConnectionError(f"unable to reach Binance testnet: {exc}") from exc
        except requests.exceptions.Timeout:
            logger.error("request timed out after %ss", REQUEST_TIMEOUT)
            raise TimeoutError("request to Binance API timed out.")

        logger.debug("<- HTTP %s | body=%s", resp.status_code, resp.text[:500])
        return self._parse_response(resp)

    @staticmethod
    def _parse_response(resp: requests.Response) -> Dict[str, Any]:
        try:
            data = resp.json()
        except ValueError:
            resp.raise_for_status()
            return {}

        # Binance returns errors as JSON with a negative code field
        if isinstance(data, dict) and "code" in data and data["code"] != 200:
            raise BinanceAPIError(
                code=data.get("code", -1),
                message=data.get("msg", "unknown error"),
                http_status=resp.status_code,
            )

        if not resp.ok:
            raise BinanceAPIError(
                code=resp.status_code,
                message=resp.text,
                http_status=resp.status_code,
            )

        return data

    @staticmethod
    def _redact(params: Dict[str, Any]) -> Dict[str, Any]:
        """Never log the actual signature."""
        redacted = dict(params)
        if "signature" in redacted:
            redacted["signature"] = "***"
        return redacted

    def get_exchange_info(self) -> Dict[str, Any]:
        """Fetch symbol metadata — useful for checking precision rules."""
        return self._request("GET", "/fapi/v1/exchangeInfo", signed=False)

    def get_account(self) -> Dict[str, Any]:
        """Fetch account balances and open positions."""
        return self._request("GET", "/fapi/v2/account")

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: str,
        price: Optional[str] = None,
        stop_price: Optional[str] = None,
        time_in_force: str = "GTC",
        reduce_only: bool = False,
    ) -> Dict[str, Any]:
        """
        Place a new futures order.

        price is required for LIMIT orders.
        stop_price is required for STOP_MARKET / STOP orders.
        """
        params: Dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
        }

        if order_type in ("LIMIT", "STOP", "TAKE_PROFIT"):
            params["timeInForce"] = time_in_force
            if price:
                params["price"] = price

        if order_type in ("STOP_MARKET", "STOP", "TAKE_PROFIT_MARKET", "TAKE_PROFIT"):
            if stop_price:
                params["stopPrice"] = stop_price

        if reduce_only:
            params["reduceOnly"] = "true"

        logger.info(
            "placing order: symbol=%s side=%s type=%s qty=%s price=%s stopPrice=%s",
            symbol, side, order_type, quantity, price, stop_price,
        )
        result = self._request("POST", "/fapi/v1/order", params=params)
        logger.info("order placed: orderId=%s status=%s", result.get("orderId"), result.get("status"))
        return result

    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Cancel an open order by ID."""
        params = {"symbol": symbol, "orderId": order_id}
        return self._request("DELETE", "/fapi/v1/order", params=params)

    def get_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Fetch details of a specific order."""
        params = {"symbol": symbol, "orderId": order_id}
        return self._request("GET", "/fapi/v1/order", params=params)

    def get_open_orders(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Fetch all open orders, optionally filtered by symbol."""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/fapi/v1/openOrders", params=params)
