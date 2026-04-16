import argparse
import yfinance as yf


def print_basic_info(ticker_symbol):
    stock = yf.Ticker(ticker_symbol)
    info = stock.info

    print(f"\n=== {ticker_symbol} ===")
    print(f"Name: {info.get('longName', 'N/A')}")
    print(f"Symbol: {ticker_symbol}")
    print(f"Current Price: {info.get('currentPrice', 'N/A')}")
    print(f"Market Cap: {info.get('marketCap', 'N/A')}")
    print(f"52 Week High: {info.get('fiftyTwoWeekHigh', 'N/A')}")
    print(f"52 Week Low: {info.get('fiftyTwoWeekLow', 'N/A')}")

    return stock, info


def print_verbose_info(stock, info):
    print("--- Verbose Data ---")
    print(f"Forward P/E: {info.get('forwardPE', 'N/A')}")
    print(f"Trailing P/E: {info.get('trailingPE', 'N/A')}")
    print(f"Dividend Yield: {info.get('dividendYield', 'N/A')}")
    print(f"Beta: {info.get('beta', 'N/A')}")
    print(f"Average Volume: {info.get('averageVolume', 'N/A')}")
    print(f"Volume: {info.get('volume', 'N/A')}")

    # Implied volatility comes from options data, not regular stock info
    try:
        expirations = stock.options

        if not expirations:
            print("Implied Volatility: No options data available")
            return

        first_expiry = expirations[0]
        option_chain = stock.option_chain(first_expiry)

        calls = option_chain.calls
        puts = option_chain.puts

        print(f"Options Expiration Used: {first_expiry}")

        if not calls.empty:
            call_iv = calls["impliedVolatility"].dropna()
            if not call_iv.empty:
                print(f"Sample Call Implied Volatility: {call_iv.iloc[0]}")
            else:
                print("Sample Call Implied Volatility: N/A")
        else:
            print("Sample Call Implied Volatility: N/A")

        if not puts.empty:
            put_iv = puts["impliedVolatility"].dropna()
            if not put_iv.empty:
                print(f"Sample Put Implied Volatility: {put_iv.iloc[0]}")
            else:
                print("Sample Put Implied Volatility: N/A")
        else:
            print("Sample Put Implied Volatility: N/A")

    except Exception as e:
        print(f"Implied Volatility: Unable to fetch ({e})")


def main():
    parser = argparse.ArgumentParser(description="Fetch stock data with yfinance")
    parser.add_argument(
        "-t",
        "--ticker",
        nargs="+",
        required=True,
        help="One or more stock ticker symbols"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show more detailed stock data, including option IV if available"
    )

    args = parser.parse_args()

    for ticker_symbol in args.ticker:
        ticker_symbol = ticker_symbol.upper()

        try:
            stock, info = print_basic_info(ticker_symbol)

            if args.verbose:
                print_verbose_info(stock, info)

        except Exception as e:
            print(f"\n=== {ticker_symbol} ===")
            print(f"Error fetching data: {e}")


if __name__ == "__main__":
    main()
