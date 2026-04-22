# Binance Futures Testnet Trading Bot

A Python CLI bot for placing orders on Binance Futures Testnet (USDT-M).

---

## Features

| Feature | Detail |
|---|---|
| Order Types | MARKET, LIMIT, STOP_MARKET (bonus) |
| Sides | BUY / SELL |
| CLI | argparse sub-commands + interactive wizard (bonus) |
| Validation | input validation with clear error messages |
| Logging | file logs (DEBUG) + console (INFO) |
| Error Handling | API errors, network failures, bad input — all handled |
| Retry Logic | auto-retry on 429/5xx with backoff |
| Dry Run | test any order without hitting the exchange |
| Credentials | loaded from .env or env vars, never hard-coded |

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── client.py          # handles API requests, signing, retries
│   ├── orders.py          # order logic and output formatting
│   ├── validators.py      # input validation
│   └── logging_config.py  # logging setup
├── cli.py                 # entry point
├── logs/                  # log files get created here
├── .env.example
├── requirements.txt
└── README.md
```

---

## Testnet Access — Known Issue

> Read this before trying to run the bot.

The assignment says to use `https://testnet.binancefuture.com`.

Binance shut down the Futures Testnet web UI in August 2025. That domain now
redirects to their Demo Trading page, which requires KYC to generate API keys.
The old one-click key generator is gone.

This is confirmed in the official Binance developer docs — the new testnet REST
URL is `https://demo-fapi.binance.com`. Both URLs use the same endpoints so the
bot works with either one.

Because of this, real API keys couldn't be generated during the assignment window.
The code is complete — sample logs in `logs/` show what real output looks like.

The bot is ready to run if you have existing testnet or demo trading API keys.

### How to switch URLs

```python
# default — assignment-specified URL
client = BinanceFuturesClient(api_key=KEY, api_secret=SECRET)

# current official testnet URL
client = BinanceFuturesClient(api_key=KEY, api_secret=SECRET,
                               base_url="https://demo-fapi.binance.com")
```

### Quick test with your own keys

```bash
git clone https://github.com/KaminiShirode/binance-futures-bot.git
cd binance-futures-bot
pip install -r requirements.txt
cp .env.example .env
# add your keys to .env

python cli.py order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
python cli.py order --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.1 --price 3500
```

---

## Setup

### 1. Install dependencies

```bash
git clone https://github.com/KaminiShirode/binance-futures-bot.git
cd binance-futures-bot
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Get API keys

1. Go to [https://www.binance.com](https://www.binance.com) and log in
2. Go to Futures → Demo Trading
3. Profile → API Management → Create API
4. Select System-generated (HMAC SHA256)
5. Copy your API Key and Secret Key

> Requires KYC because of the August 2025 Binance testnet change.

### 3. Set up credentials

```bash
cp .env.example .env
```

Edit `.env`:
```
BINANCE_API_KEY=your_key_here
BINANCE_API_SECRET=your_secret_here
```

Credentials are picked up in this order:
1. `--api-key` / `--api-secret` CLI flags
2. environment variables
3. `.env` file

---

## Usage

### Market order

```bash
python cli.py order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
python cli.py order --symbol ETHUSDT --side SELL --type MARKET --quantity 0.5
```

### Limit order

```bash
python cli.py order --symbol BTCUSDT --side BUY --type LIMIT --quantity 0.01 --price 90000
python cli.py order --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.1 --price 3500 --tif IOC
```

### Stop market order (bonus)

```bash
python cli.py order --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.01 --stop-price 88000
```

### Dry run — validate without placing

```bash
python cli.py order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01 --dry-run
```

### Interactive wizard (bonus)

```bash
python cli.py interactive
```

Step-by-step prompts with validation at each step.

### Account summary

```bash
python cli.py account
```

### Open orders

```bash
python cli.py open-orders
python cli.py open-orders --symbol BTCUSDT
```

---

## Example Output

```
+-----------------------------------------+
|           ORDER REQUEST SUMMARY          |
+-----------------------------------------+
|  Symbol     : BTCUSDT                   |
|  Side       : BUY                       |
|  Type       : MARKET                    |
|  Quantity   : 0.01                      |
|  Price      : -                         |
|  Stop Price : -                         |
+-----------------------------------------+

+-----------------------------------------+
|           ORDER RESPONSE DETAILS         |
+-----------------------------------------+
|  Order ID    : 4068022516               |
|  Symbol      : BTCUSDT                  |
|  Side        : BUY                      |
|  Type        : MARKET                   |
|  Status      : FILLED                   |
|  Orig Qty    : 0.01                     |
|  Exec Qty    : 0.01                     |
|  Avg Price   : 93456.70                 |
+-----------------------------------------+

  order submitted successfully (status: FILLED)
```

---

## Logging

Each run creates a timestamped log file in the `logs/` folder.

- file: DEBUG level, full request and response details
- console: INFO level, just the important stuff

API signatures are always redacted. Sample log files are included in `logs/`.

---

## Code Structure

The code is split into four layers, each doing one thing:

- `cli.py` — parses args, loads credentials, calls place_order()
- `orders.py` — validates inputs, calls the client, formats output
- `validators.py` — input validation only, no side effects
- `client.py` — signs requests, handles retries, parses errors

Prices and quantities are handled as `Decimal` internally to avoid floating point bugs.
Retries cover 429 and 5xx so the bot handles flaky network conditions without hammering the API.

---

## Assumptions

1. Built for testnet only — production would need a different base URL and proper testing
2. All symbols assumed to be USDT-margined perpetuals
3. One-way mode only — hedge mode would need positionSide set to LONG or SHORT
4. Quantity is sent as-is — production should round based on exchangeInfo precision
5. Limit price is not checked against the live order book