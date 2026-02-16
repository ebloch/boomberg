
<div align="center"><img width="450" alt="Boomberg" src="https://github.com/user-attachments/assets/47a79e99-b4db-4872-8fab-a192a0c4bb57" /></div>


Real-time financial data, market news, and analytics terminal. Built with Python and [Textual](https://textual.textualize.io/).

<img width="1824" height="1323" alt="image" src="https://github.com/user-attachments/assets/f0f66624-c8f5-4b1b-a9eb-2fd162113d64" />


## Features

- **Real-time Stock Quotes** - Get live quotes for any stock symbol
- **Watchlists** - Create and manage multiple watchlists with persistent storage
- **Financial Statements** - View income statements, balance sheets, and cash flow statements
- **World Equity Indices** - Track major indices across US, Europe, and Asia-Pacific
- **Treasury Yields** - US Treasury rates with yield curve visualization
- **Currency/Forex** - Track major currency ETFs
- **Economic Statistics** - GDP, unemployment, CPI, Fed Funds rate via FRED API
- **News Feed** - Latest market news and symbol-specific news
- **Price Charts** - ASCII-based historical price charts
- **Multi-Currency Support** - Displays prices in local currency for international stocks (USD, EUR, GBP, JPY, etc.)

## Installation

### Prerequisites

- Python 3.11+
- [FMP API Key](https://site.financialmodelingprep.com/developer/docs/) (required)
- [FRED API Key](https://fred.stlouisfed.org/docs/api/api_key.html) (optional, for economic statistics)

### Install from source

```bash
git clone https://github.com/ebloch/boomberg.git
cd boomberg
pip install -e ".[dev]"
```

### Configuration

Create a `.env` file in the project root or set environment variables:

```bash
# Required
FMP_API_KEY=your_fmp_api_key_here

# Optional (for ECST command)
FRED_API_KEY=your_fred_api_key_here
```

## Usage

```bash
boomberg
```

Or run as a module:

```bash
python -m boomberg
```

## Commands

### Quotes & Charts

| Command | Description | Example |
|---------|-------------|---------|
| `Q <symbol>` | Get real-time quote | `Q AAPL` |
| `GP <symbol>` | Price chart (1M default) | `GP TSLA` |
| `GP <symbol> <period>` | Price chart with period | `GP MSFT 1Y` |

Chart periods: `1D`, `1W`, `1M`, `3M`, `6M`, `1Y`, `5Y`

### Financial Data

| Command | Description | Example |
|---------|-------------|---------|
| `FI <symbol>` | Financial ratios & key metrics | `FI AAPL` |
| `FA <symbol>` | Company fundamentals/profile | `FA GOOGL` |
| `IS <symbol>` | Income statement (4 years) | `IS MSFT` |
| `IS <symbol> <years> Q` | Quarterly income statement | `IS AAPL 8 Q` |
| `BS <symbol>` | Balance sheet | `BS AMZN` |
| `CF <symbol>` | Cash flow statement | `CF NVDA` |

### Market Overview

| Command | Description |
|---------|-------------|
| `WEI` | World Equity Indices (US, Europe, Asia-Pacific) |
| `WB` | US Treasury Yields with yield curve |
| `FXIP` | Currency ETFs (EUR, GBP, JPY, etc.) |
| `MOST` | Market movers (top gainers) |
| `ECST` | Economic Statistics (requires FRED API key) |

### News

| Command | Description | Example |
|---------|-------------|---------|
| `N` | Latest market news | `N` |
| `N <symbol>` | News for specific symbol | `N TSLA` |
| `TOP` | Top news headlines | `TOP` |

### Watchlist

| Command | Description | Example |
|---------|-------------|---------|
| `W` | Show default watchlist | `W` |
| `W <name>` | Show named watchlist | `W tech` |
| `WA <symbol>` | Add to default watchlist | `WA AAPL` |
| `WA <symbol> <name>` | Add to named watchlist | `WA NVDA tech` |
| `WR <symbol>` | Remove from watchlist | `WR AAPL` |
| `WC <name>` | Create new watchlist | `WC dividends` |
| `WD <name>` | Delete watchlist | `WD old` |

### Search & Help

| Command | Description | Example |
|---------|-------------|---------|
| `S <query>` | Search for symbols | `S apple` |
| `?` or `HELP` | Show help | `?` |

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `?` | Show help |
| `Escape` | Focus command bar |
| `Ctrl+W` | Show watchlist |
| `q` | Quit |

## International Stocks

Boomberg supports international stocks with proper currency display:

| Exchange | Currency | Example |
|----------|----------|---------|
| NYSE, NASDAQ | $ (USD) | `Q AAPL` |
| LSE (London) | £ (GBP) | `Q VOD.L` |
| XETRA (Germany) | € (EUR) | `Q SAP.DE` |
| JPX (Japan) | ¥ (JPY) | `Q 7203.T` |
| HKSE (Hong Kong) | HK$ | `Q 0700.HK` |
| KSC (Korea) | ₩ (KRW) | `Q 005930.KS` |

## Data Sources

- **[Financial Modeling Prep (FMP)](https://financialmodelingprep.com/)** - Stock quotes, financials, news
- **[FRED (Federal Reserve Economic Data)](https://fred.stlouisfed.org/)** - Economic statistics

## Development

### Running Tests

```bash
pytest
```

### Project Structure

```
boomberg/
├── src/boomberg/
│   ├── api/           # API clients (FMP, FRED)
│   ├── services/      # Business logic
│   ├── storage/       # Data persistence
│   ├── ui/
│   │   ├── widgets/   # UI components
│   │   └── styles/    # CSS styling
│   ├── app.py         # Main application
│   └── config.py      # Configuration
└── tests/             # Unit tests
```

## License

MIT

## Disclaimer

This is a parody project for educational purposes. Not affiliated with Bloomberg L.P. Not financial advice. Use at your own risk.
