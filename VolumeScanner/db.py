import sqlite3
from datetime import datetime

DB_FILE = "volume_scanner.db"

def get_conn():
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = get_conn()
    c = conn.cursor()

    # Store every scan result
    c.execute("""
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            current_volume INTEGER,
            avg_volume INTEGER,
            volume_ratio REAL,
            current_price REAL,
            price_change_pct REAL,
            flagged INTEGER DEFAULT 0
        )
    """)

    # Store only the flagged alerts for easy querying
    c.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            current_volume INTEGER,
            avg_volume INTEGER,
            volume_ratio REAL,
            current_price REAL,
            price_change_pct REAL
        )
    """)

    conn.commit()
    conn.close()
    print(f"[DB] Database initialized: {DB_FILE}")

def insert_scan(ticker, current_volume, avg_volume, volume_ratio, price, price_change_pct, flagged):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO scans (ticker, timestamp, current_volume, avg_volume, volume_ratio, current_price, price_change_pct, flagged)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (ticker, datetime.now().isoformat(), current_volume, avg_volume, volume_ratio, price, price_change_pct, int(flagged)))
    conn.commit()
    conn.close()

def insert_alert(ticker, current_volume, avg_volume, volume_ratio, price, price_change_pct):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO alerts (ticker, timestamp, current_volume, avg_volume, volume_ratio, current_price, price_change_pct)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (ticker, datetime.now().isoformat(), current_volume, avg_volume, volume_ratio, price, price_change_pct))
    conn.commit()
    conn.close()

def get_recent_alerts(limit=50):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT ticker, timestamp, current_volume, avg_volume, volume_ratio, current_price, price_change_pct
        FROM alerts
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

def print_recent_alerts(limit=20):
    alerts = get_recent_alerts(limit)
    if not alerts:
        print("No alerts yet.")
        return
    print(f"\n{'='*70}")
    print(f"{'TICKER':<8} {'TIME':<22} {'VOL':>12} {'AVG VOL':>12} {'RATIO':>7} {'PRICE':>8} {'CHG%':>7}")
    print(f"{'='*70}")
    for row in alerts:
        ticker, ts, vol, avg_vol, ratio, price, chg = row
        ts_short = ts[:19].replace("T", " ")
        print(f"{ticker:<8} {ts_short:<22} {vol:>12,} {avg_vol:>12,} {ratio:>6.1f}x ${price:>7.2f} {chg:>+6.2f}%")
    print(f"{'='*70}\n")
