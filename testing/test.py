# Import yfinance
import yfinance as yf

# Define the stock ticker (e.g., Apple)
ticker_symbol = "AAPL"

# Create a Ticker object
stock = yf.Ticker(ticker_symbol)

# Fetch basic info
info = stock.info

# Print some simple data
print(f"Name: {info.get('longName')}")
print(f"Symbol: {ticker_symbol}")
print(f"Current Price: {info.get('currentPrice')}")
print(f"Market Cap: {info.get('marketCap')}")
print(f"52 Week High: {info.get('fiftyTwoWeekHigh')}")
print(f"52 Week Low: {info.get('fiftyTwoWeekLow')}")
