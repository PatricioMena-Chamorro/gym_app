import sqlite3

DB_PATH = "gym.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("DELETE FROM set_logs;")
cur.execute("DELETE FROM workout_sessions;")

conn.commit()
conn.close()

print("✅ Listo: se limpiaron set_logs y workout_sessions.")

#python .\reset_logs.py