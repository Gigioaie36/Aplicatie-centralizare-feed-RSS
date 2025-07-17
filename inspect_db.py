import sqlite3

conn = sqlite3.connect("rss_data.db")
cursor = conn.cursor()

# Afișează toate tabelele din baza de date
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Tabele găsite:", tables)

# Afișează primele 5 rânduri din fiecare tabel
for table_name, in tables:
    print(f"\nDate din tabelul: {table_name}")
    cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
    rows = cursor.fetchall()
    for row in rows:
        print(row)

conn.close()
