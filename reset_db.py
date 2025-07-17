import os
import sqlite3

DB_FILE = 'rss_data.db'

print("=== RESETARE BAZĂ DE DATE ===")

# Șterge fișierul existent
if os.path.exists(DB_FILE):
    print(f"Șterg baza de date existentă: {DB_FILE}")
    os.remove(DB_FILE)
    print("Baza de date ștearsă cu succes!")
else:
    print("Nu există o bază de date de șters.")

# Creează tabela nouă cu coloana description
print("Creez noua bază de date cu schema actualizată...")

with sqlite3.connect(DB_FILE) as conn:
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        link TEXT,
        published TEXT,
        source TEXT,
        description TEXT,
        UNIQUE(title, link)
    )''')
    conn.commit()
    print("Nouă bază de date creată cu succes!")

# Verifică schema
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(articles)")
columns = cursor.fetchall()

print("\nSchema tabelei 'articles':")
for col in columns:
    print(f"  - {col[1]} ({col[2]})")

print("\n✅ Resetare completă! Acum poți porni serverul.")