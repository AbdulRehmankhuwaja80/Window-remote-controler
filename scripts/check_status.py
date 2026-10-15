import sqlite3
import urllib.request
import os
import subprocess

print("=== CHECKING BACKEND HEALTH ===")
try:
    with urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3) as r:
        print("Backend response:", r.read().decode())
except Exception as e:
    print("Backend unreachable on 127.0.0.1:8000:", e)

try:
    with urllib.request.urlopen('http://192.168.0.44:8000/health', timeout=3) as r:
        print("Backend response on 192.168.0.44:8000:", r.read().decode())
except Exception as e:
    print("Backend unreachable on 192.168.0.44:8000:", e)

print("\n=== CHECKING PROCESSES (TASKLIST) ===")
res = subprocess.run(['tasklist'], capture_output=True, text=True)
for line in res.stdout.splitlines():
    if any(k in line.lower() for k in ['python', 'uvicorn', 'remodesk', 'dotnet']):
        print(line)

print("\n=== CHECKING DATABASE ===")
db_path = os.path.abspath('remodesk.db')
print("DB Path:", db_path)
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    print("--- USERS ---")
    for row in c.execute("SELECT * FROM users"):
        print(row)
    print("--- DEVICES ---")
    for row in c.execute("SELECT * FROM devices"):
        print(row)
    conn.close()
else:
    print("Database not found!")
