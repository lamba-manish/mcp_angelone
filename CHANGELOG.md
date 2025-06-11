# Trading Bot Changelog

## Version 1.2.0 - Market Depth & Chart Generation Updates

### 🎯 New Features

#### 📊 Enhanced Market Depth Display
- **Improved Visual Format**: Market depth now displays in a clean tabular format with better column alignment
- **Smart Data Filtering**: Automatically filters out zero-value orders to show only meaningful market data
- **Better Organization**: Split market depth display into separate messages for better readability
- **Unicode Table Borders**: Added proper table formatting with Unicode characters for professional appearance

#### 📈 Candlestick Chart Generation (`/graph` command)
- **New Command**: `/graph SYMBOL TIMEFRAME` - Generate beautiful candlestick charts
- **Multiple Timeframes Supported**:
  - `1M` - 1 Minute intervals
  - `3M` - 3 Minute intervals  
  - `5M` - 5 Minute intervals
  - `10M` - 10 Minute intervals
  - `15M` - 15 Minute intervals
  - `30M` - 30 Minute intervals
  - `1H` - 1 Hour intervals
  - `1D` - 1 Day intervals
- **Auto-Optimized Data Range**: Automatically fetches ~100 candles for each timeframe
- **High-Quality Charts**: 150 DPI charts with volume indicators and professional styling
- **Real-time Data**: Uses AngelOne's historical API for accurate OHLC data

### 🔧 Technical Improvements

#### 📡 AngelOne Broker Integration
- **New Historical Data API**: Added `get_historical_data()` method
- **Smart Date Range Calculation**: Automatically calculates optimal date ranges for each timeframe
- **Robust Error Handling**: Comprehensive error handling for API failures and data issues
- **Timestamp Parsing**: Handles multiple timestamp formats from AngelOne API

#### 🎨 Chart Generation Engine
- **matplotlib Integration**: Added matplotlib and mplfinance dependencies
- **Custom Styling**: Green/red candlesticks with professional appearance
- **Volume Indicators**: Shows volume data below price charts
- **Memory Efficient**: Uses BytesIO buffers for efficient image handling
- **Async Chart Generation**: Non-blocking chart creation for better user experience

#### 🤖 Bot Command Enhancements
- **Updated Help System**: Added graph command to help documentation
- **Enhanced Command Menu**: Updated bot command menu with new chart functionality
- **Better Error Messages**: Improved error handling and user feedback
- **Input Validation**: Validates timeframe inputs with clear error messages

### 📋 Usage Examples

```bash
# Generate 5-minute candlestick chart for Reliance
/graph RELIANCE 5M

# View market depth with improved formatting
/market_depth ITC

# Generate daily chart for TCS
/graph TCS 1D

# Generate hourly chart for HDFC Bank
/graph HDFCBANK 1H
```

### 🛠 Dependencies Added
- `matplotlib==3.8.2` - Chart generation library
- `mplfinance==0.12.10b0` - Financial charting library specialized for candlestick charts

### 📈 Performance
- **Optimized Data Fetching**: Smart date range calculation reduces API calls
- **Efficient Chart Generation**: Uses memory buffers for fast image generation
- **Better User Experience**: Separate messages for market depth prevent formatting issues

### 🔄 Breaking Changes
- Market depth display now sends multiple messages instead of one long message
- Added new required dependencies for chart generation

### 🐛 Bug Fixes
- Fixed market depth table formatting issues
- Improved error handling for symbols not found
- Better handling of empty market depth data

---

## Previous Versions

### Version 1.1.0
- AngelOne broker integration
- Basic trading commands
- Market data functionality

### Version 1.0.0  
- Initial trading bot release
- Multi-broker architecture
- Telegram bot integration 