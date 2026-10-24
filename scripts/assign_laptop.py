import sqlite3

conn = sqlite3.connect(r"D:\Antigravity\Window-remote-controler-main\remodesk.db")
cursor = conn.cursor()
cursor.execute("UPDATE devices SET user_id = '3985960f-1147-4a69-979d-9bb2bbef6e89' WHERE device_name = 'LAPTOP-4A9AUPQS'")
conn.commit()
cursor.execute("SELECT id, device_name, pairing_code, user_id FROM devices WHERE device_name = 'LAPTOP-4A9AUPQS'")
print("Updated device:", cursor.fetchall())
conn.close()
