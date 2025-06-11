# Trading Bot - Multi-Broker Telegram Trading Assistant

A production-grade modular trading backend that integrates with Telegram to enable trading via multiple brokers. Currently supports AngelOne with extensible architecture for adding more brokers.

## 🚀 Features

### Core Features
- **Multi-Broker Support**: Extensible architecture supporting multiple brokers
- **Telegram Integration**: User-friendly bot interface for trading commands
- **Real-time Trading**: Place orders, check positions, holdings, and get live quotes
- **Session Management**: Secure user session handling with state management
- **Production Ready**: Structured logging, error handling, and async architecture

### Trading Capabilities
- 📈 **Order Management**: Place buy/sell orders (market & limit)
- 📊 **Portfolio Tracking**: View holdings and positions with P&L
- 💰 **Fund Management**: Check available funds and margins
- 📋 **Order History**: View and track order status
- 💹 **Live Quotes**: Get real-time market data
- 🔄 **Order Modification**: Modify or cancel existing orders

### Supported Brokers
- ✅ **AngelOne** (Implemented)
- 🔄 **Fyers** (Coming Soon)
- 🔄 **Dhan** (Coming Soon)
- 🔄 **Upstox** (Coming Soon)
- 🔄 **5Paisa** (Coming Soon)

## 🏗️ Architecture

### Project Structure
```
mcp_angelone/
├── src/
│   ├── brokers/          # Broker abstraction and implementations
│   │   ├── base.py       # Abstract broker interface
│   │   └── angelone/     # AngelOne broker implementation (Next)
│   ├── models/           # Data models and schemas
│   │   └── trading.py    # Trading-related data models
│   ├── telegram/         # Telegram bot implementation
│   │   ├── bot.py        # Main bot class
│   │   ├── handlers.py   # Command handlers
│   │   ├── models.py     # Telegram-specific models
│   │   └── session_manager.py
│   ├── utils/            # Utilities and common functions
│   │   ├── logging.py    # Structured logging
│   │   └── exceptions.py # Custom exceptions
│   └── config.py         # Configuration management
├── tests/                # Unit tests (Coming Soon)
├── main.py              # Application entry point
├── requirements.txt     # Dependencies
├── env.example          # Environment variables template
└── README.md           # This file
```

### Design Principles
1. **Broker Abstraction**: Clean interface for adding new brokers
2. **Modular Architecture**: Separate concerns for maintainability
3. **Async First**: Full async/await support for performance
4. **Type Safety**: Pydantic models for data validation
5. **Production Ready**: Logging, error handling, and monitoring

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.9+
- Telegram Bot Token
- AngelOne API Credentials

### 1. Clone Repository
```bash
git clone <repository-url>
cd mcp_angelone
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration
```bash
# Copy the example environment file
cp env.example .env

# Edit .env with your credentials
```

### 4. Configure Environment Variables
Edit `.env` file with your credentials:

```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# AngelOne Broker Configuration
ANGELONE_API_KEY=your_angelone_api_key_here
ANGELONE_USER_ID=your_angelone_user_id_here
ANGELONE_PASSWORD=your_angelone_password_here
ANGELONE_TOTP_SECRET=your_angelone_totp_secret_here

# Application Configuration
LOG_LEVEL=INFO
DEBUG=False
ENVIRONMENT=production
```

### 5. Run the Application
```bash
python main.py
```

## 🤖 Telegram Bot Usage

### Getting Started
1. Start a chat with your bot on Telegram
2. Send `/start` to begin
3. Use `/broker` to select AngelOne
4. Bot will authenticate automatically
5. Start trading with commands!

### Available Commands

#### 🔧 Setup Commands
- `/start` - Welcome & initial setup
- `/broker` - Select or change broker
- `/status` - Check connection status
- `/help` - Show help information

#### 📊 Trading Commands
- `/buy SYMBOL QTY [PRICE]` - Place buy order
- `/sell SYMBOL QTY [PRICE]` - Place sell order
- `/holdings` - View your holdings
- `/positions` - View current positions
- `/orders` - View today's orders
- `/funds` - Check available funds
- `/quote SYMBOL` - Get live price quote

### Command Examples
```
/buy RELIANCE 10          # Market buy 10 shares of Reliance
/buy RELIANCE 10 2500     # Limit buy 10 shares at ₹2500
/sell TCS 5 3200          # Limit sell 5 shares at ₹3200
/quote INFY               # Get INFY live price
/holdings                 # View portfolio
/positions                # View open positions
```

### Natural Language Support
You can also use natural language:
- "buy reliance" → Bot suggests using `/buy` command
- "show my holdings" → Triggers holdings display
- "what's my portfolio" → Shows holdings

## 🔌 Adding New Brokers

The system is designed for easy broker integration. To add a new broker:

### 1. Create Broker Implementation
```python
# src/brokers/newbroker/client.py
from ..base import BaseBroker
from ...models.trading import LoginResponse, BrokerResponse

class NewBrokerClient(BaseBroker):
    def __init__(self):
        super().__init__("NewBroker")
    
    async def login(self) -> LoginResponse:
        # Implement authentication
        pass
    
    async def place_order(self, order_request) -> BrokerResponse:
        # Implement order placement
        pass
    
    # Implement other required methods...
```

### 2. Register Broker
```python
# src/brokers/__init__.py
from .base import BrokerFactory
from .newbroker.client import NewBrokerClient

# Register the new broker
BrokerFactory.register_broker("NewBroker", NewBrokerClient)
```

### 3. Add Configuration
Add broker-specific environment variables to config.py and env.example.

### 4. Test Integration
The broker will automatically appear in the Telegram bot's broker selection menu.

## 🧪 Testing

```bash
# Run tests (Coming Soon)
pytest

# Run with coverage (Coming Soon)
pytest --cov=src --cov-report=html
```

## 📝 Logging

The application uses structured logging with JSON output in production:

```python
from src.utils.logging import get_logger

logger = get_logger(__name__)
logger.info("Trading operation completed", symbol="RELIANCE", quantity=10)
```

Logs include:
- Request/Response tracking
- Error details with context
- Performance metrics
- Security events

## 🔒 Security

### Credentials Management
- All credentials stored in environment variables
- No hardcoded secrets in code
- Secure session management
- Token-based authentication

### API Security
- HTTPS-only communication
- Request rate limiting
- Input validation and sanitization
- Error message sanitization

## 🛣️ Roadmap

### Phase 1: Core Foundation ✅
- [x] Broker abstraction layer
- [x] Telegram bot framework
- [x] Session management
- [x] Basic trading commands
- [ ] AngelOne broker implementation

### Phase 2: Enhanced Features
- [ ] Advanced order types (SL, CO, BO)
- [ ] Portfolio analytics
- [ ] Risk management features
- [ ] Multiple watchlists
- [ ] Price alerts

### Phase 3: Multi-Broker Support
- [ ] Fyers integration
- [ ] Dhan integration
- [ ] Upstox integration
- [ ] 5Paisa integration

### Phase 4: AI & Analytics
- [ ] MCP (Model Context Protocol) integration
- [ ] Natural language processing
- [ ] Trading strategy suggestions
- [ ] Market analysis and insights

### Phase 5: Advanced Features
- [ ] Web dashboard
- [ ] Mobile app
- [ ] Paper trading mode
- [ ] Social trading features

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guidelines
- Add type hints to all functions
- Write comprehensive docstrings
- Include unit tests for new features
- Update documentation as needed

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

For support and questions:
- Create an issue on GitHub
- Join our Discord community (Coming Soon)
- Email: support@tradingbot.com (Coming Soon)

## ⚠️ Disclaimer

This software is for educational and informational purposes only. Trading in financial markets involves substantial risk of loss and is not suitable for all investors. Always consult with a qualified financial advisor before making investment decisions.

## 🙏 Acknowledgments

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) for Telegram integration
- [Pydantic](https://pydantic-docs.helpmanual.io/) for data validation
- [FastAPI](https://fastapi.tiangolo.com/) for async framework patterns
- [Structlog](https://www.structlog.org/) for structured logging

---

**Built with ❤️ for the trading community** 