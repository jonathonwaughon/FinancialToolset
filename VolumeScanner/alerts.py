"""
Run this anytime to see recent volume alerts:
    python3 alerts.py
    python3 alerts.py 50   # show last 50
"""
import sys
from db import init_db, print_recent_alerts

init_db()
limit = int(sys.argv[1]) if len(sys.argv) > 1 else 20
print_recent_alerts(limit)
