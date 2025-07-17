import socket
import threading
import json
import time
import feedparser
import sqlite3
import requests
import ssl
import os

HOST = '0.0.0.0'
PORT = 5000
DB_FILE = 'rss_data.db'
CONFIG_FILE = 'feeds_config.json'

# Headers pentru a evita blocarea
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'application/rss+xml, application/xml, text/xml',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
}

# Variabile globale pentru configurare
current_config = None
last_config_check = 0


def create_default_config():
    """Creează fișierul de configurare implicit dacă nu există."""
    default_config = {
        "feeds": [
            {
                "name": "BBC News",
                "url": "http://feeds.bbci.co.uk/news/rss.xml",
                "active": True
            },
            {
                "name": "New York Times",
                "url": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
                "active": True
            },
            {
                "name": "Reuters Top News",
                "url": "https://feeds.reuters.com/reuters/topNews",
                "active": False
            },
            {
                "name": "CNN RSS",
                "url": "https://rss.cnn.com/rss/edition.rss",
                "active": False
            }
        ],
        "settings": {
            "update_interval": 300,
            "max_articles_per_feed": 50,
            "request_timeout": 15
        }
    }
    
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(default_config, f, indent=2, ensure_ascii=False)
    
    print(f"Fișier de configurare creat: {CONFIG_FILE}")
    return default_config


def load_config():
    """Încarcă configurația din fișier."""
    global current_config
    
    try:
        if not os.path.exists(CONFIG_FILE):
            print("Fișierul de configurare nu există. Creez unul nou...")
            current_config = create_default_config()
            return current_config
        
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            current_config = json.load(f)
        
        # Validează configurația
        if not validate_config(current_config):
            print("Configurarea este invalidă. Creez una nouă...")
            current_config = create_default_config()
        
        print(f"Configurație încărcată: {len(current_config['feeds'])} feed-uri definite")
        return current_config
    
    except Exception as e:
        print(f"Eroare la încărcarea configurației: {e}")
        print("Creez configurație implicită...")
        current_config = create_default_config()
        return current_config


def validate_config(config):
    """Validează structura configurației."""
    try:
        # Verifică structura de bază
        if not isinstance(config, dict):
            return False
        
        if 'feeds' not in config or 'settings' not in config:
            return False
        
        if not isinstance(config['feeds'], list):
            return False
        
        # Verifică fiecare feed
        for feed in config['feeds']:
            if not isinstance(feed, dict):
                return False
            
            required_keys = ['name', 'url', 'active']
            if not all(key in feed for key in required_keys):
                return False
        
        return True
    
    except Exception:
        return False


def get_active_feeds():
    """Returnează lista feed-urilor active."""
    global current_config
    
    if not current_config:
        load_config()
    
    active_feeds = []
    for feed in current_config['feeds']:
        if feed.get('active', False):
            active_feeds.append(feed)
    
    return active_feeds


def reload_config_if_needed():
    """Reîncarcă configurația dacă fișierul s-a schimbat."""
    global current_config, last_config_check
    
    try:
        current_time = time.time()
        
        # Verifică doar la fiecare 30 de secunde
        if current_time - last_config_check < 30:
            return
        
        last_config_check = current_time
        
        if os.path.exists(CONFIG_FILE):
            file_mtime = os.path.getmtime(CONFIG_FILE)
            
            # Dacă fișierul s-a modificat, reîncarcă-l
            if not hasattr(reload_config_if_needed, 'last_mtime'):
                reload_config_if_needed.last_mtime = file_mtime
            
            if file_mtime > reload_config_if_needed.last_mtime:
                print("Configurația s-a schimbat. Reîncărcare...")
                load_config()
                reload_config_if_needed.last_mtime = file_mtime
    
    except Exception as e:
        print(f"Eroare la verificarea configurației: {e}")


def init_db():
    """Inițializează baza de date."""
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


def fetch_feed_content(url, timeout=15):
    """Descarcă conținutul feed-ului cu requests pentru a evita problemele SSL."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout, verify=False)
        response.raise_for_status()
        return response.text
    
    except requests.exceptions.RequestException as e:
        print(f"Eroare la descărcarea feed-ului {url}: {e}")
        return None


def update_feeds():
    """Actualizează feed-urile în buclă."""
    global current_config
    
    while True:
        try:
            # Reîncarcă configurația dacă s-a schimbat
            reload_config_if_needed()
            
            # Obține feed-urile active
            active_feeds = get_active_feeds()
            
            if not active_feeds:
                print("Nu sunt feed-uri active în configurație!")
                time.sleep(60)
                continue
            
            print(f"Începem actualizarea pentru {len(active_feeds)} feed-uri active la {time.strftime('%H:%M:%S')}")
            
            # Obține setările
            settings = current_config.get('settings', {})
            timeout = settings.get('request_timeout', 15)
            max_articles = settings.get('max_articles_per_feed', 50)
            
            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                total_new_articles = 0
                
                for feed_config in active_feeds:
                    try:
                        feed_name = feed_config['name']
                        feed_url = feed_config['url']
                        
                        print(f"Procesez feed: {feed_name}")
                        
                        # Descarcă conținutul
                        feed_content = fetch_feed_content(feed_url, timeout)
                        if not feed_content:
                            continue
                        
                        # Parsează cu feedparser
                        feed = feedparser.parse(feed_content)
                        
                        if not feed.entries:
                            print(f"Nu s-au găsit articole în feed-ul {feed_name}")
                            continue
                        
                        # Limitează numărul de articole
                        entries_to_process = feed.entries[:max_articles]
                        
                        print(f"Procesez {len(entries_to_process)} articole de la {feed_name}")
                        
                        new_articles_count = 0
                        for entry in entries_to_process:
                            try:
                                title = getattr(entry, 'title', 'Fără titlu')
                                link = getattr(entry, 'link', '')
                                published = getattr(entry, 'published', '')
                                description = getattr(entry, 'description', '')
                                
                                # Folosește numele din configurație în loc de feed.feed.title
                                cursor.execute('''INSERT OR IGNORE INTO articles 
                                                (title, link, published, source, description)
                                                VALUES (?, ?, ?, ?, ?)''',
                                             (title, link, published, feed_name, description))
                                
                                if cursor.rowcount > 0:
                                    new_articles_count += 1
                                    
                            except Exception as e:
                                print(f"Eroare la inserarea articolului: {e}")
                        
                        total_new_articles += new_articles_count
                        print(f"Adăugate {new_articles_count} articole noi de la {feed_name}")
                        
                    except Exception as e:
                        print(f"Eroare la procesarea feed-ului {feed_config.get('name', 'necunoscut')}: {e}")
                
                conn.commit()
                print(f"Actualizare completă: {total_new_articles} articole noi în total")
            
            # Folosește intervalul din configurație
            update_interval = settings.get('update_interval', 300)
            print(f"Următoarea actualizare în {update_interval} secunde...")
            time.sleep(update_interval)
            
        except Exception as e:
            print(f"Eroare critică în update_feeds: {e}")
            time.sleep(60)  # Așteaptă 1 minut înainte de a încerca din nou


def handle_client(conn, addr):
    """Gestionează cererile clienților."""
    try:
        data = conn.recv(1024).decode().strip()
        if data == 'GET_FEED':
            with sqlite3.connect(DB_FILE) as db:
                cursor = db.cursor()
                cursor.execute('''SELECT title, link, published, source, description 
                                FROM articles ORDER BY id DESC LIMIT 50''')
                rows = cursor.fetchall()
                
                articles = []
                for row in rows:
                    articles.append({
                        'title': row[0],
                        'link': row[1],
                        'published': row[2],
                        'source': row[3],
                        'description': row[4]
                    })
                
                payload = json.dumps({'articles': articles})
                conn.sendall(payload.encode())
                print(f"Trimise {len(articles)} articole către client {addr}")
        
        elif data == 'GET_CONFIG':
            # Opțional: permite clientului să vadă configurația
            active_feeds = get_active_feeds()
            config_info = {
                'active_feeds': [{'name': f['name'], 'url': f['url']} for f in active_feeds],
                'total_feeds': len(current_config['feeds']),
                'settings': current_config['settings']
            }
            payload = json.dumps(config_info)
            conn.sendall(payload.encode())
            
        else:
            conn.sendall(json.dumps({'error': 'Comanda necunoscută'}).encode())
            
    except Exception as e:
        print(f"Eroare la client {addr}: {e}")
    finally:
        conn.close()


def start_server():
    """Pornește serverul."""
    print("=== RSS FEED SERVER ===")
    print("Încărcare configurație...")
    load_config()
    
    print("Inițializez baza de date...")
    init_db()
    
    print("Pornesc thread-ul de actualizare feed-uri...")
    threading.Thread(target=update_feeds, daemon=True).start()
    
    print(f"Pornesc serverul pe {HOST}:{PORT}...")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        print(f" Server pornit pe {HOST}:{PORT}")
        print(f" Configurație: {CONFIG_FILE}")
        print(f"  Baza de date: {DB_FILE}")
        print(f" Feed-uri active: {len(get_active_feeds())}")
        print("\n Pentru a schimba feed-urile, editează fișierul feeds_config.json")
        print(" Serverul va reîncărca automat configurația la modificări\n")
        
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


if __name__ == '__main__':
    # Dezactivează warnings pentru SSL
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    start_server()