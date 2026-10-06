import sqlite3

conn = sqlite3.connect("gamewatch.db")
c = conn.cursor()
c.execute("SELECT id, name, active FROM tvs")
print("TVs:", c.fetchall())

c.execute("PRAGMA table_info(users)")
print("Users schema:", [col[1] for col in c.fetchall()])

c.execute("SELECT id, full_name, email, role FROM users")
print("Users:", c.fetchall())
