# Quant Options Trading System

Sistema de trading de opções desenvolvido por **Francisco Pinheiro** (Médico Interno | Trader | Portugal) como parte de um portfolio de candidatura à [Liberta Investimentos / TraderUP](https://traderup.com.br).

Implementa duas estratégias em conta real:
- **Wheel Strategy** — Venda de puts cash-secured + covered calls em ciclo contínuo
- **Compra a Seco (Momentum Breakout)** — Setup do Stormer implementado em opções ATM, 2H chart

Integração com **TastyTrade API** (conta real) e **Alpaca API** (paper trading / backtesting). Flask dashboard com modo paper/sandbox/live e confirmação obrigatória antes de executar em capital real.

---

## 📚 The Papers That Built Quant Finance

This system is inspired by the five foundational papers in quantitative finance:

1. **Bachelier (1900)** - *Theory of Speculation*
   - Introduced Brownian motion to finance
   - Foundation of stochastic processes in markets
   - Implemented in price movement modeling

2. **Sharpe (1964)** - *Capital Asset Pricing Model*
   - Systematic vs idiosyncratic risk
   - Beta and alpha concepts
   - Used in risk management and diversification

3. **Black-Scholes (1973)** - *Option Pricing*
   - Risk-neutral pricing framework
   - Implied volatility calculation
   - Delta-based strike selection

4. **Dupire (1994)** - *Local Volatility*
   - Volatility surface modeling
   - Smile and skew handling
   - Strike selection optimization

5. **Carr-Madan (1999)** - *FFT Option Pricing*
   - Efficient pricing methodology
   - Fast transform techniques
   - Used in scenario analysis

## 🎯 The Wheel Strategy

The Wheel is an income-generating options strategy that cycles through positions:

1. **Own Stock** → Sell Covered Calls (collect premium)
   - If assigned: stock sold, move to step 2
   - If expires: keep stock, repeat step 1

2. **No Stock** → Sell Cash-Secured Puts (collect premium)
   - If assigned: buy stock, return to step 1
   - If expires: remain in cash, repeat step 2

3. **Repeat** the cycle indefinitely

### Key Principle
- Sell calls **above** cost basis (profitable if assigned)
- Sell puts to **enter** positions at desired prices
- Collect premium in both states of the world

## � Compra a Seco (Momentum Breakout Strategy)

An intraday momentum strategy using **call options** on 2-hour charts:

### Pattern Detection
1. **Bull Run** - Price above EMA 8 & EMA 80 (uptrend confirmed)
2. **Propulsion Candle** - Large bullish candle (2x average size, close near high)
3. **Pin Bar** - Small body candle showing indecision/consolidation
4. **Breakout** - Next candle breaks above pin bar high → **BUY ATM CALL**

### Trade Rules
- **Entry:** Buy ATM Call (30 DTE) at breakout
- **Stop:** Sell if stock hits pin bar LOW
- **Target:** Sell if stock reaches 2x propulsion amplitude
- **Time Stop:** Sell Thursday of expiration week
- **Position Size:** Fixed $1,000 risk per trade (2% of $50K)

### Why Options?
- **Leverage:** Control 100 shares per contract
- **Defined Risk:** Max loss = premium paid
- **No assignment risk** (long options)

---

## �🚀 Features

### Core Trading
- ✅ Delta-based strike selection (configurable target delta)
- ✅ Automatic option chain resolution
- ✅ Volume-weighted strike ranking
- ✅ Real-time P&L tracking
- ✅ Scenario analysis for assignment/expiration

### Risk Management
- ✅ Position concentration limits (max 20% per position)
- ✅ Portfolio delta exposure monitoring
- ✅ Assignment probability tracking
- ✅ Cash requirement calculations
- ✅ Margin utilization monitoring

### Visualization
- ✅ Real-time position chart (spot vs cost basis)
- ✅ Visual strike selection (calls in green, puts in red)
- ✅ Portfolio overview dashboard
- ✅ Scenario analysis panel
- ✅ Trade recommendation engine

### API Integration
- ✅ Alpaca API (paper & live trading)
- ✅ yfinance fallback for historical data
- ✅ Local data caching (43 symbols)
- ✅ Real-time market data streaming
- ✅ Order execution
- ✅ Portfolio synchronization

## 📦 Installation

### Prerequisites
- Python 3.9+
- Alpaca account (paper trading recommended for testing)
- Windows, macOS, or Linux
- 50MB disk space for cached data

### Setup

1. **Clone the repository**
```bash
git clone https://github.com/fpinheiro921/quant-options-trading.git
cd quant-options-trading
```

2. **Create virtual environment**
```bash
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure credentials**
```bash
copy .env.example .env
# Edit .env with your Alpaca API keys
```

## 🔧 Configuration

Edit `.env` file:

```env
# Alpaca API Credentials (Paper Trading)
ALPACA_API_KEY=your_key_here
ALPACA_API_SECRET=your_secret_here

# Trading Configuration
DEFAULT_DELTA_THRESHOLD=0.20
MIN_PREMIUM_THRESHOLD=0.50
MAX_POSITION_PCT=0.20
RISK_FREE_RATE=0.045
```

## 🎮 Usage

### Quick Backtesting (Recommended)

```bash
# Run portfolio Wheel backtest (43 stocks, ONE position)
python scripts/backtest_wheel_portfolio.py

# Run 2-year backtest on NVDA
python scripts/backtest_2year.py NVDA

# Generate comparison report
python scripts/backtest_report.py TSLA 30

# Check cached data
python scripts/check_cache.py

# Download more symbols
python scripts/download_portfolio_data.py --symbols AMD JPM
```

### Run Dashboard (Web Interface)

```bash
python main.py
```

Then open your browser to `http://localhost:5000`

### Run CLI Mode

```bash
python cli.py
```

Follow the interactive prompts to:
1. Scan for opportunities
2. Run scenario analysis
3. Execute trades (paper trading)

### Analyze a Symbol

```bash
python main.py --analyze NVDA
```

### Check Configuration

```bash
python main.py --check
```

## 📊 Dashboard Features

### 1. Symbol Analysis
Enter a symbol to view:
- Current position state in the wheel cycle
- Cost basis vs spot price visualization
- Stock P&L tracking
- Active option positions

### 2. Option Chain Resolver
- Set target delta (default: 0.30)
- View top candidates for each expiration
- Volume-weighted ranking
- Real-time quote updates

### 3. Trade Recommendations
- Context-aware suggestions based on position state
- Covered call recommendations when owning stock
- Cash-secured put recommendations when flat
- Expected premium and max profit calculations

### 4. Scenario Analysis
- Premium collection estimates
- Assignment P&L calculations
- New cost basis if assigned on puts
- Cash obligation for short puts

### 5. Portfolio View
- All positions at a glance
- Aggregate P&L
- State distribution
- Risk metrics

## 🧮 Delta-Based Strike Selection

The system uses delta as the primary strike selection metric:

```
Target Delta: 0.30 (30 delta)
- For calls: Select strikes with ~0.30 delta (OTM)
- For puts: Select strikes with ~-0.30 delta (OTM)

Volume Weighting:
- Higher volume = better liquidity
- Prefer listed strikes (multiples of 2.5 or 5)
- Rank by: |actual_delta - target_delta| adjusted for volume
```

Delta represents the probability of assignment:
- 30 delta ≈ 30% probability of ITM at expiration
- Also represents share equivalent exposure

## ⚠️ Risk Management

### Position Limits
- **Max Position Size**: 20% of portfolio per symbol
- **Concentration Alert**: Triggers at 25%
- **Cash Reserve**: Minimum 10% recommended

### Assignment Risk
- **High Risk Alert**: >50% delta (ITM options)
- **Roll Recommendation**: Near expiration with high assignment risk

### Portfolio Heat
- **Net Delta**: Tracks directional exposure
- **Theta Income**: Daily income from option decay
- **Vega Exposure**: Volatility sensitivity

## 📈 P&L Calculation

### Covered Call P&L (if assigned)
```
Stock P&L = (Call Strike - Cost Basis) × Shares Owned
Option Premium = Premium × Contracts × 100
Total P&L = Stock P&L + Option Premium
```

### Cash-Secured Put (if assigned)
```
New Cost Basis = (Strike × 100 - Premium × 100) / 100
Cash Required = Strike × Contracts × 100
Effective Entry = Strike - Premium
```

## 🔬 Mathematical Models

### Black-Scholes Delta
```python
delta = N(d1)  # for calls
delta = N(d1) - 1  # for puts

where:
d1 = (ln(S/K) + (r + σ²/2)T) / (σ√T)
```

Used for:
- Strike selection
- Assignment probability estimation
- Risk exposure calculation

### Local Volatility Surface
The system implicitly uses market implied volatilities from the option chain rather than assuming constant volatility.

## 🛡️ Safety Features

1. **Paper Trading Mode**: Test before going live
2. **Confirmation Dialogs**: All trades require confirmation
3. **Bid-Ask Validation**: Warns on wide spreads
4. **Position Limits**: Enforced in code
5. **Cash Checks**: Verifies sufficient cash before put sales

## � 5-Year Backtest Results (2021-2026)

### Combined Strategies (Wheel + Momentum Options)

| Portfolio | Wheel Return | Momentum Return | **Combined** | Total Trades |
|-----------|-------------|-----------------|--------------|--------------|
| **NASDAQ** | +5.91% | **+138.38%** | **+72.15%** 🏆 | 515 |
| **High Vol** | +6.81% | +234.85% | +120.83% | 491 |
| **Small Cap** | +3.63% | +155.17% | +79.40% | 470 |
| **Sector** | +16.59% | +84.20% | +50.40% | 524 |
| **Dividend** | +11.33% | +86.60% | +48.97% | 512 |
| **S&P 500** | +17.47% | +83.95% | +50.71% | 509 |

**Setup:** $100K total ($50K per strategy), ONE position at a time per strategy

### Strategy Characteristics

**Wheel Strategy:**
- Monthly cycles (30 DTE)
- 20 Delta puts (~80% win probability)
- Premium collection focus
- Conservative, steady income

**Momentum Options:**
- Real-time pattern detection on 2H charts
- Portfolio scan across all symbols
- ATM calls with fixed $1,000 risk per trade
- Higher volatility, higher returns

---

## �📁 Project Structure

```
quant-options-trading/
├── scripts/                     # ⭐ Executable backtest scripts
│   ├── backtest_wheel_portfolio.py
│   ├── backtest_2year.py
│   ├── backtest_report.py
│   ├── download_portfolio_data.py
│   └── check_cache.py
├── api/
│   ├── __init__.py
│   ├── alpaca_client.py         # Alpaca API client
│   └── massive_client.py        # Local data cache client
├── trading/
│   ├── __init__.py
│   ├── wheel_strategy.py        # Wheel strategy
│   ├── momentum_breakout.py     # Compra a Seco strategy
│   └── strike_resolver.py       # Delta-based strike selection
│   └── wheel_strategy.py        # Wheel strategy implementation
├── utils/
│   ├── __init__.py
│   └── risk_manager.py          # Risk management
├── dashboard/
│   ├── __init__.py
│   └── app.py                   # Flask web application
├── templates/
│   ├── base.html                # Base template
│   └── index.html               # Main dashboard
├── config.py                    # Configuration
├── main.py                      # Entry point
├── requirements.txt             # Dependencies
├── .env.example                 # Example environment
└── README.md                    # This file
```

## ⚙️ Advanced Configuration

### Custom Delta Targets
```python
# In config.py or .env
DEFAULT_DELTA_THRESHOLD = 0.25  # More conservative
# or
DEFAULT_DELTA_THRESHOLD = 0.40  # More aggressive
```

### Strike Selection Range
```python
STRIKE_RANGE_PCT = 0.15  # Only look at strikes within 15% of spot
```

### DTE Preferences
```python
DEFAULT_DTE = 7    # Weekly options
MAX_DTE = 45       # Maximum expiration
```

## 🐛 Troubleshooting

### Authentication Issues
```bash
python main.py --check
```
Verify credentials in `.env` file.

### API Rate Limits
The system implements caching for option chains (5-minute TTL).

### Connection Issues
Check Alpaca API status at https://alpaca.markets/ and ensure API keys are correct.

## 📚 Further Reading

### Quant Finance Foundations
- "The Papers That Built Quant Finance" - Roman Paolucci, Quant Guild
- "Option Volatility and Pricing" - Sheldon Natenberg
- "Dynamic Hedging" - Nassim Taleb

### Wheel Strategy
- "The Wheel Strategy Explained" - OptionsPlay / YouTube
- "Covered Calls vs Cash-Secured Puts" - Options Industry Council

### Python for Trading
- "Python for Finance" - Yves Hilpisch
- "Algorithmic Trading" - Ernest Chan

## ⚠️ Disclaimer

**IMPORTANT**: This software is for educational and research purposes only.

- Trading options involves substantial risk of loss
- Past performance does not guarantee future results
- Always test with paper trading before using real capital
- The authors assume no liability for trading losses
- Consult a financial advisor before making investment decisions

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- Roman Paolucci and Quant Guild for the educational content
- Alpaca for the paper trading API
- The quantitative finance researchers who built the foundation

## 📞 Support

For issues, questions, or contributions:
- GitHub Issues: https://github.com/fpinheiro921/quant-options-trading/issues
- Portfolio: https://fp-trading-portfolio.vercel.app

---

**Built with respect for the quant trading community**
