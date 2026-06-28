import sqlite3

conn = sqlite3.connect("bluestock_mf.db")
cur = conn.cursor()

sql = "SELECT name FROM sqlite_master WHERE type='table'"
cur.execute(sql)

tables = cur.fetchall()

print("Tables in database:")
print(tables)

conn.close()