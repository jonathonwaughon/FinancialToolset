# Import libraries
import yfinance as yf
import argparse

# Set up argument parser
parser = argparse.ArgumentParser(description="Fetch stock data using yfinance")

# Add a flag for ticker (e.g., -t AAPL or --ticker AAPL)
parser.add_argument("-t", "--ticker", required=True, help="Stock ticker symbol")

# Parse arguments
args = parser.parse_args()

# Use the provided ticker
ticker_symbol = args.ticker.upper()

# Fetch stock data
stock = yf.Ticker(ticker_symbol)
info = stock.info

# Print data
print(f"Name: {info.get('longName')}")
print(f"Symbol: {ticker_symbol}")
print(f"Current Price: {info.get('currentPrice')}")
print(f"Market Cap: {info.get('marketCap')}")
print(f"52 Week High: {info.get('fiftyTwoWeekHigh')}")
print(f"52 Week Low: {info.get('fiftyTwoWeekLow')}")
