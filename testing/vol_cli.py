"""
File name: stock_vol_cli.py
Created: 2026-04-16
Purpose: CLI tool for stock volatility data using Alpha Vantage
Notes:
    - Supports current ATM IV, historical ATM IV, historical volatility, and realized volatility
    - Requires an Alpha Vantage API key
Used:
    python stock_vol_cli.py -t AAPL
    python stock_vol_cli.py -t AAPL MSFT --hv 30 --iv
    python stock_vol_cli.py -t TSLA --rv 30 -v
    python stock_vol_cli.py -t NVDA --hist-iv 2025-12-15
"""

import argparse
import math
import os
import sys
from typing import Optional, Tuple

import numpy as np
import pandas as pd
import requests


BASE_URL = "https://www.alphavantage.co/query"


def fetch_json(params: dict) -> dict:
    response = requests.get(BASE_URL, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    if "Note" in data:
        raise RuntimeError(f"API limit/message: {data['Note']}")
    if "Information" in data:
        raise RuntimeError(f"API info: {data['Information']}")
    if "Error Message" in data:
        raise RuntimeError(f"API error: {data['Error Message']}")

    return data


def fetch_daily_prices(symbol: str, api_key: str) -> pd.DataFrame:
    data = fetch_json({
        "function": "TIME_SERIES_DAILY",
        "symbol": symbol,
        "apikey": api_key,
    })

    key = "Time Series (Daily)"
    if key not in data:
        raise RuntimeError(f"Unexpected daily response for {symbol}: {data}")

    df = pd.DataFrame.from_dict(data[key], orient="index")
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    df = df.rename(columns={
        "1. open": "open",
        "2. high": "high",
        "3. low": "low",
        "4. close": "close",
        "5. volume": "volume",
    })

    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def fetch_intraday_prices(symbol: str, api_key: str, interval: str = "5min") -> pd.DataFrame:
    data = fetch_json({
        "function": "TIME_SERIES_INTRADAY",
        "symbol": symbol,
        "interval": interval,
        "outputsize": "full",
        "apikey": api_key,
    })

    key = f"Time Series ({interval})"
    if key not in data:
        raise RuntimeError(f"Unexpected intraday response for {symbol}: {data}")

    df = pd.DataFrame.from_dict(data[key], orient="index")
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    df = df.rename(columns={
        "1. open": "open",
        "2. high": "high",
        "3. low": "low",
        "4. close": "close",
        "5. volume": "volume",
    })

    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def fetch_realtime_options(symbol: str, api_key: str) -> list:
    data = fetch_json({
        "function": "REALTIME_OPTIONS",
        "symbol": symbol,
        "require_greeks": "true",
        "apikey": api_key,
    })

    if "data" not in data:
        raise RuntimeError(f"Unexpected realtime options response for {symbol}: {data}")

    return data["data"]


def fetch_historical_options(symbol: str, api_key: str, date: str) -> list:
    data = fetch_json({
        "function": "HISTORICAL_OPTIONS",
        "symbol": symbol,
        "date": date,
        "apikey": api_key,
    })

    if "data" not in data:
        raise RuntimeError(f"Unexpected historical options response for {symbol}: {data}")

    return data["data"]


def annualized_hv_from_daily(df: pd.DataFrame, window: int) -> Optional[float]:
    closes = df["close"].dropna()
    if len(closes) < window + 1:
        return None

    returns = np.log(closes / closes.shift(1)).dropna()
    window_returns = returns.tail(window)

    if len(window_returns) < window:
        return None

    return float(window_returns.std(ddof=1) * math.sqrt(252))


def annualized_rv_from_intraday(df: pd.DataFrame, window: int) -> Optional[float]:
    closes = df["close"].dropna()
    if len(closes) < window + 1:
        return None

    returns = np.log(closes / closes.shift(1)).dropna()
    window_returns = returns.tail(window)

    if len(window_returns) < window:
        return None

    bars_per_year = 252 * 78  # rough annualization for 5-minute regular-session bars
    return float(np.sqrt(np.sum(np.square(window_returns))) * math.sqrt(bars_per_year / window))


def parse_float(value) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def days_to_expiry(expiration_str: str) -> Optional[int]:
    try:
        expiration = pd.to_datetime(expiration_str).date()
        today = pd.Timestamp.today().date()
        return (expiration - today).days
    except Exception:
        return None


def choose_atm_contract(options_data: list) -> Tuple[Optional[dict], Optional[float]]:
    if not options_data:
        return None, None

    underlying_price = None

    for row in options_data:
        for key in ("underlying_price", "underlyingPrice"):
            if key in row:
                underlying_price = parse_float(row.get(key))
                if underlying_price is not None:
                    break
        if underlying_price is not None:
            break

    if underlying_price is None:
        strike_candidates = [parse_float(row.get("strike")) for row in options_data]
        strike_candidates = [x for x in strike_candidates if x is not None]
        if not strike_candidates:
            return None, None
        underlying_price = float(np.median(strike_candidates))

    best_row = None
    best_score = None

    for row in options_data:
        strike = parse_float(row.get("strike"))
        iv = parse_float(row.get("implied_volatility") or row.get("impliedVolatility"))
        expiration = row.get("expiration")

        if strike is None or iv is None or expiration is None:
            continue

        dte = days_to_expiry(expiration)
        if dte is None or dte < 0:
            continue

        score = (abs(strike - underlying_price), dte)

        if best_score is None or score < best_score:
            best_score = score
            best_row = row

    return best_row, underlying_price


def format_percent(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.2f}%"


def print_basic_price_info(symbol: str, daily_df: Optional[pd.DataFrame]) -> None:
    print(f"\n=== {symbol} ===")

    if daily_df is None or daily_df.empty:
        print("Last Close: N/A")
        return

    last_close = daily_df["close"].dropna().iloc[-1]
    last_date = daily_df["close"].dropna().index[-1].date()
    print(f"Last Close: {last_close:.2f} ({last_date})")


def main():
    parser = argparse.ArgumentParser(description="Stock volatility CLI using Alpha Vantage")

    parser.add_argument(
        "-t",
        "--ticker",
        nargs="+",
        required=True,
        help="One or more ticker symbols"
    )
    parser.add_argument(
        "-k",
        "--api-key",
        default=os.getenv("ALPHAVANTAGE_API_KEY"),
        help="Alpha Vantage API key (or set ALPHAVANTAGE_API_KEY)"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show extra details"
    )
    parser.add_argument(
        "--hv",
        type=int,
        help="Compute annualized historical volatility from daily closes over N days"
    )
    parser.add_argument(
        "--rv",
        type=int,
        help="Compute annualized realized volatility from intraday closes over N bars"
    )
    parser.add_argument(
        "--rv-interval",
        default="5min",
        choices=["1min", "5min", "15min", "30min", "60min"],
        help="Intraday interval for RV (default: 5min)"
    )
    parser.add_argument(
        "--iv",
        action="store_true",
        help="Fetch current ATM implied volatility from realtime options"
    )
    parser.add_argument(
        "--hist-iv",
        metavar="YYYY-MM-DD",
        help="Fetch historical ATM implied volatility for a specific date"
    )

    args = parser.parse_args()

    if not args.api_key:
        print("Error: provide an Alpha Vantage API key with -k or ALPHAVANTAGE_API_KEY")
        sys.exit(1)

    for symbol in args.ticker:
        symbol = symbol.upper()

        daily_df = None
        intraday_df = None

        try:
            if args.hv or args.verbose:
                daily_df = fetch_daily_prices(symbol, args.api_key)

            print_basic_price_info(symbol, daily_df)

            if args.hv:
                hv = annualized_hv_from_daily(daily_df, args.hv)
                print(f"{args.hv}-day HV: {format_percent(hv)}")

            if args.rv:
                intraday_df = fetch_intraday_prices(symbol, args.api_key, args.rv_interval)
                rv = annualized_rv_from_intraday(intraday_df, args.rv)
                print(f"{args.rv}-bar RV ({args.rv_interval}): {format_percent(rv)}")

            if args.iv:
                realtime_options = fetch_realtime_options(symbol, args.api_key)
                atm_row, underlying_price = choose_atm_contract(realtime_options)

                if atm_row is None:
                    print("Current ATM IV: N/A")
                else:
                    iv = parse_float(atm_row.get("implied_volatility") or atm_row.get("impliedVolatility"))
                    strike = parse_float(atm_row.get("strike"))
                    expiration = atm_row.get("expiration")
                    option_type = atm_row.get("type", "N/A")
                    print(f"Current ATM IV: {format_percent(iv)}")

                    if args.verbose:
                        print(f"ATM contract type: {option_type}")
                        print(f"ATM strike: {strike}")
                        print(f"ATM expiration: {expiration}")
                        print(f"Underlying reference price: {underlying_price}")

            if args.hist_iv:
                hist_options = fetch_historical_options(symbol, args.api_key, args.hist_iv)
                atm_row, underlying_price = choose_atm_contract(hist_options)

                if atm_row is None:
                    print(f"Historical ATM IV ({args.hist_iv}): N/A")
                else:
                    iv = parse_float(atm_row.get("implied_volatility") or atm_row.get("impliedVolatility"))
                    strike = parse_float(atm_row.get("strike"))
                    expiration = atm_row.get("expiration")
                    option_type = atm_row.get("type", "N/A")
                    print(f"Historical ATM IV ({args.hist_iv}): {format_percent(iv)}")

                    if args.verbose:
                        print(f"Historical ATM contract type: {option_type}")
                        print(f"Historical ATM strike: {strike}")
                        print(f"Historical ATM expiration: {expiration}")
                        print(f"Underlying reference price: {underlying_price}")

        except Exception as e:
            print(f"Error for {symbol}: {e}")


if __name__ == "__main__":
    main()
