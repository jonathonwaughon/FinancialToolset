import yfinance as yf
import schedule
import time
import logging
from datetime import datetime
import pytz

from config import (
    WATCHLIST,
    VOLUME_SPIKE_THRESHOLD,
    SCAN_INTERVAL_MINUTES,
    AVERAGE_VOLUME_DAYS,
    LOG_FILE,
    MARKET_OPEN_HOUR,
    MARKET_OPEN_MINUTE,
    MARKET_CLOSE_HOUR,
)
from db import init_db, insert_scan, insert_alert

# --- Logging setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()  # also print to terminal
    ]
)
log = logging.getLogger(__name__)

EASTERN = pytz.timezone("US/Eastern")

def is_market_open():
    now = datetime.now(EASTERN)
    # Skip weekends
    if now.weekday() >= 5:
        return False
    open_time = now.replace(hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MINUTE, second=0)
    close_time = now.replace(hour=MARKET_CLOSE_HOUR, minute=0, second=0)
    return open_time <= now <= close_time

def scan_ticker(ticker):
    try:
        stock = yf.Ticker(ticker)

        # Get today's intraday data (1-minute intervals)
        intraday = stock.history(period="1d", interval="1m")
        if intraday.empty:
            log.warning(f"{ticker}: No intraday data available.")
            return

        # Current volume = total volume traded so far today
        current_volume = int(intraday["Volume"].sum())

        # Get historical daily data to compute average volume
        history = stock.history(period=f"{AVERAGE_VOLUME_DAYS + 5}d", interval="1d")
        if len(history) < 5:
            log.warning(f"{ticker}: Not enough history to compute average.")
            return

        # Average daily volume over last N trading days (exclude today)
        avg_volume = int(history["Volume"].iloc[:-1].tail(AVERAGE_VOLUME_DAYS).mean())

        if avg_volume == 0:
            return

        volume_ratio = current_volume / avg_volume

        # Current price and % change from previous close
        current_price = round(float(intraday["Close"].iloc[-1]), 2)
        prev_close = round(float(history["Close"].iloc[-2]), 2)
        price_change_pct = round(((current_price - prev_close) / prev_close) * 100, 2)

        flagged = volume_ratio >= VOLUME_SPIKE_THRESHOLD

        # Save to DB
        insert_scan(ticker, current_volume, avg_volume, volume_ratio, current_price, price_change_pct, flagged)

        if flagged:
            insert_alert(ticker, current_volume, avg_volume, volume_ratio, current_price, price_change_pct)
            log.info(
                f"🚨 ALERT | {ticker:<6} | "
                f"Vol: {current_volume:>10,} | "
                f"Avg: {avg_volume:>10,} | "
                f"Ratio: {volume_ratio:.1f}x | "
                f"Price: ${current_price} ({price_change_pct:+.2f}%)"
            )
        else:
            log.info(
                f"   OK    | {ticker:<6} | "
                f"Vol: {current_volume:>10,} | "
                f"Avg: {avg_volume:>10,} | "
                f"Ratio: {volume_ratio:.1f}x | "
                f"Price: ${current_price} ({price_change_pct:+.2f}%)"
            )

    except Exception as e:
        log.error(f"{ticker}: Error during scan — {e}")

def run_scan():
    if not is_market_open():
        log.info("Market is closed. Skipping scan.")
        return

    now = datetime.now(EASTERN).strftime("%Y-%m-%d %H:%M:%S ET")
    log.info(f"\n{'='*60}")
    log.info(f"Scan started at {now}")
    log.info(f"{'='*60}")

    for ticker in WATCHLIST:
        scan_ticker(ticker)
        time.sleep(0.5)  # small delay to avoid rate limiting

    log.info("Scan complete.\n")

def main():
    log.info("Initializing database...")
    init_db()

    log.info(f"Volume scanner started. Scanning every {SCAN_INTERVAL_MINUTES} minutes.")
    log.info(f"Watchlist: {', '.join(WATCHLIST)}")
    log.info(f"Spike threshold: {VOLUME_SPIKE_THRESHOLD}x average volume\n")

    # Run immediately on start
    run_scan()

    # Then schedule recurring scans
    schedule.every(SCAN_INTERVAL_MINUTES).minutes.do(run_scan)

    while True:
        schedule.run_pending()
        time.sleep(30)

if __name__ == "__main__":
    main()
