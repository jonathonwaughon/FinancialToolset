# --- Your stock watchlist ---
WATCHLIST = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
    "META", "TSLA", "AMD", "PLTR", "SPY",
    "QQQ", "SOFI", "RIVN", "LCID", "F",
    "BAC", "JPM", "C", "WFC", "GS",
]

# How many times above average volume counts as "unusual"
VOLUME_SPIKE_THRESHOLD = 2.5  # 2.5x average = flagged

# How often to scan during market hours (in minutes)
SCAN_INTERVAL_MINUTES = 15

# Average volume is calculated over this many days
AVERAGE_VOLUME_DAYS = 20

# Log file location
LOG_FILE = "volume_alerts.log"

# Market hours (Eastern Time)
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 30
MARKET_CLOSE_HOUR = 16
