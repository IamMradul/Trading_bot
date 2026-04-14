# Binance Futures Testnet Trading Bot

A clean, production-style Python CLI application that places orders on the
**Binance USDT-M Futures Testnet** via the REST API.

---

## Features

| Capability | Details |
|---|---|
| Order types | `MARKET`, `LIMIT`, `STOP_MARKET` (bonus) |
| Sides | `BUY` / `SELL` |
| CLI | Click-powered with coloured output & validation |
| Logging | Rotating file (DEBUG) + console (INFO+) |
| Error handling | Typed exceptions for API, network, auth, and input errors |
| Code structure | Separate client / orders / validators / logging layers |

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py         # Package exports
│   ├── client.py           # Binance REST client (signing, HTTP, error types)
│   ├── orders.py           # High-level order logic (market, limit, stop)
│   ├── validators.py       # Input validation with clear error messages
│   └── logging_config.py   # Rotating file + console logging setup
├── cli.py                  # Click CLI entry point (5 commands)
├── logs/
│   └── trading_bot.log     # Auto-created; sample included in repo
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Clone / unzip the project

```bash
git clone https://github.com/<your-username>/trading-bot.git
cd trading-bot
```

### 2. Create & activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Get Binance Futures Testnet credentials

1. Go to <https://testnet.binancefuture.com>
2. Log in (GitHub OAuth works out of the box).
3. Click **API Key** → **Generate Key**.
4. Copy the **API Key** and **Secret Key**.

### 5. Set environment variables

**Linux / macOS:**
```bash
export BINANCE_API_KEY="your_api_key_here"
export BINANCE_API_SECRET="your_secret_key_here"
```

**Windows (cmd):**
```cmd
set BINANCE_API_KEY=your_api_key_here
set BINANCE_API_SECRET=your_secret_key_here
```

Or create a `.env` file in the project root:
```dotenv
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_secret_key_here
```
Then load it:
```bash
source .env          # or: set -a; source .env; set +a
```

---

## Running the Bot

All commands are run from the project root.

### Global options

```
--log-level  DEBUG|INFO|WARNING|ERROR   (default: INFO)
```

### Check connectivity

```bash
python cli.py server-time
```

### Place a MARKET order

```bash
# Buy 0.001 BTC at market price
python cli.py place-order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

# Sell 0.01 ETH at market price
python cli.py place-order --symbol ETHUSDT --side SELL --type MARKET --quantity 0.01
```

### Place a LIMIT order

```bash
# Sell 0.001 BTC at $60,000 (Good-Till-Cancel)
python cli.py place-order \
  --symbol BTCUSDT \
  --side SELL \
  --type LIMIT \
  --quantity 0.001 \
  --price 60000

# Buy with Immediate-Or-Cancel fill policy
python cli.py place-order \
  --symbol BTCUSDT \
  --side BUY \
  --type LIMIT \
  --quantity 0.001 \
  --price 50000 \
  --tif IOC
```

### Place a STOP_MARKET order (bonus)

```bash
# Trigger a market BUY when ETHUSDT hits $3,100
python cli.py place-order \
  --symbol ETHUSDT \
  --side BUY \
  --type STOP_MARKET \
  --quantity 0.01 \
  --stop-price 3100
```

### View account balance

```bash
python cli.py account
python cli.py account --full    # prints raw JSON
```

### List open orders

```bash
python cli.py open-orders
python cli.py open-orders --symbol BTCUSDT
```

### Cancel an order

```bash
python cli.py cancel-order --symbol BTCUSDT --order-id 4038491247
```

### Verbose debug output

```bash
python cli.py --log-level DEBUG place-order --symbol BTCUSDT --side BUY \
  --type MARKET --quantity 0.001
```

---

## Example Output

```
──────────────────────────────────────────────────
  ORDER REQUEST
──────────────────────────────────────────────────
  Symbol:               BTCUSDT
  Side:                 BUY
  Type:                 MARKET
  Quantity:             0.001

──────────────────────────────────────────────────
  ORDER RESPONSE
──────────────────────────────────────────────────
  Order ID:             4038475901
  Status:               FILLED
  Type:                 MARKET
  Side:                 BUY
  Orig Qty:             0.001
  Executed Qty:         0.001
  Avg Price:            57423.10
  Limit Price:          —
  Stop Price:           —
  Time-in-Force:        GTC
  Client OID:           x-abc123

✓ Order placed successfully!
```

---

## Log Files

Logs are written to `logs/trading_bot.log`.

- **Console** shows `INFO` and above (clean, human-readable).
- **Log file** captures everything at `DEBUG` level, including full request
  parameters (minus signature) and raw response bodies (truncated at 400 chars).
- The file rotates at 5 MB and retains 3 backups.

Sample log entries are included in `logs/trading_bot.log`.

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Missing `--price` on LIMIT | Validator raises `ValueError` before API call |
| Invalid symbol / bad params | `BinanceAPIError` with Binance error code + message |
| Network timeout / DNS failure | `BinanceNetworkError` with descriptive message |
| Missing API credentials | `BinanceAuthError` with setup instructions |

---

## Assumptions

1. All orders are placed on **USDT-M Futures Testnet** only.
2. Quantity precision must match the symbol's `LOT_SIZE` filter — on the testnet
   `0.001` BTC and `0.01` ETH are accepted; use `exchange-info` (available via the client) for exact filters.
3. `STOP_MARKET` orders require the stop price to be above/below the current market price depending on side — the Testnet will return `-4061` if not.
4. Credentials are intentionally **not** hard-coded; they are read from the environment.
5. `python-dotenv` is listed as a dependency but **not** auto-loaded. Load your `.env` manually with `source .env` to keep the scope explicit.

---

## Dependencies

| Package | Purpose |
|---|---|
| `requests` | HTTP REST calls to Binance API |
| `click` | CLI parsing, validation, coloured output |
| `python-dotenv` | Optional `.env` file support |

All are pure Python and install in seconds.
