import os
from datetime import datetime

LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')

def _write_log(module, level, msg):
    os.makedirs(LOG_DIR, exist_ok=True)
    today = datetime.now().strftime('%Y-%m-%d')
    log_file = os.path.join(LOG_DIR, f"{module}_{today}.log")
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] [{level}] {msg}\n")

def write_log(module, msg):
    _write_log(module, 'INFO', msg)
    print(f"[INFO] {msg}")

def info(module, msg):
    _write_log(module, 'INFO', msg)
    print(f"[INFO] {msg}")

def warn(module, msg):
    _write_log(module, 'WARN', msg)
    print(f"[WARN] {msg}")

def error(module, msg):
    _write_log(module, 'ERROR', msg)
    print(f"[ERROR] {msg}")

