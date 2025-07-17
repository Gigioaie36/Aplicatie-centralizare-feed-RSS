import json
import os
import sys
import requests
import feedparser
from urllib.parse import urlparse

CONFIG_FILE = 'feeds_config.json'

def load_config():
    """Încarcă configurația din fișier."""
    if not os.path.exists(CONFIG_FILE):
        print(f" Fișierul {CONFIG_FILE} nu există!")
        print(" Pornește mai întâi serverul pentru a crea configurația implicită.")
        sys.exit(1)
    
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config(config):
    """Salvează configurația în fișier."""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f" Configurația a fost salvată în {CONFIG_FILE}")

def validate_url(url):
    """Validează dacă URL-ul este valid."""
    try:
        parsed = urlparse(url)
        return parsed.scheme in ('http', 'https') and parsed.netloc
    except:
        return False

def test_feed(url):
    """Testează dacă feed-ul funcționează."""
    print(f"Testez feed-ul: {url}")
    
    try:
        # Testează descărcarea
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        response.raise_for_status()
        
        # Testează parsarea
        feed = feedparser.parse(response.text)
        
        if not feed.entries:
            print("Feed-ul nu contine articole")
            return False
        
        feed_title = getattr(feed.feed, 'title', 'Titlu necunoscut')
        articles_count = len(feed.entries)
        
        print(f"Feed functioneaza!")
        print(f"   Titlu: {feed_title}")
        print(f"   Articole: {articles_count}")
        
        if articles_count > 0:
            first_article = feed.entries[0]
            article_title = getattr(first_article, 'title', 'Fara titlu')
            print(f"   Primul articol: {article_title}")
        
        return True
        
    except Exception as e:
        print(f"Eroare la testarea feed-ului: {e}")
        return False

def list_feeds():
    """Afișează lista feed-urilor."""
    try:
        config = load_config()
        feeds = config['feeds']
        
        if not feeds:
            print("Nu sunt feed-uri configurate.")
            return
        
        print(f"\nLista feed-urilor ({len(feeds)} total):")
        print("=" * 80)
        
        for i, feed in enumerate(feeds, 1):
            status = "ACTIV" if feed['active'] else "INACTIV"
            print(f"{i:2d}. [{status}] {feed['name']}")
            print(f"    URL: {feed['url']}")
            print()
            
        # Forțează afișarea pe Windows
        sys.stdout.flush()
        
    except Exception as e:
        print(f"Eroare la afișarea feed-urilor: {e}")
        import traceback
        traceback.print_exc()

def add_feed():
    """Adaugă un feed nou."""
    config = load_config()
    
    print("\n Adăugare feed nou")
    print("=" * 40)
    
    name = input(" Numele feed-ului: ").strip()
    if not name:
        print(" Numele nu poate fi gol!")
        return
    
    url = input("URL-ul feed-ului: ").strip()
    if not url:
        print(" URL-ul nu poate fi gol!")
        return
    
    if not validate_url(url):
        print(" URL-ul nu este valid!")
        return
    
    # Verifică dacă feed-ul există deja
    for feed in config['feeds']:
        if feed['url'] == url:
            print(f" Feed-ul cu acest URL există deja: {feed['name']}")
            return
        if feed['name'] == name:
            print(f" Feed-ul cu acest nume există deja: {feed['url']}")
            return
    
    # Testează feed-ul
    if not test_feed(url):
        response = input("⚠️  Feed-ul nu funcționează. Vrei să-l adaugi oricum? (y/n): ")
        if response.lower() != 'y':
            print(" Operație anulată.")
            return
    
    # Întreabă dacă să fie activ
    active_input = input(" Să fie activ? (y/n, default: y): ").strip().lower()
    active = active_input != 'n'
    
    # Adaugă feed-ul
    new_feed = {
        "name": name,
        "url": url,
        "active": active
    }
    
    config['feeds'].append(new_feed)
    save_config(config)
    
    status = " ACTIV" if active else " INACTIV"
    print(f" Feed adăugat cu succes: {name} ({status})")

def remove_feed():
    """Șterge un feed."""
    config = load_config()
    feeds = config['feeds']
    
    if not feeds:
        print(" Nu sunt feed-uri de șters.")
        return
    
    print("\n  Ștergere feed")
    print("=" * 40)
    
    list_feeds()
    
    try:
        index = int(input("Numărul feed-ului de șters (0 pentru anulare): ")) - 1
        
        if index == -1:
            print(" Operație anulată.")
            return
        
        if index < 0 or index >= len(feeds):
            print(" Număr invalid!")
            return
        
        feed_to_remove = feeds[index]
        
        # Confirmă ștergerea
        response = input(f" Sigur vrei să ștergi '{feed_to_remove['name']}'? (y/n): ")
        if response.lower() != 'y':
            print(" Operație anulată.")
            return
        
        # Șterge feed-ul
        config['feeds'].pop(index)
        save_config(config)
        
        print(f" Feed șters cu succes: {feed_to_remove['name']}")
        
    except ValueError:
        print(" Te rog să introduci un număr valid!")

def toggle_feed():
    """Activează/dezactivează un feed."""
    config = load_config()
    feeds = config['feeds']
    
    if not feeds:
        print(" Nu sunt feed-uri de modificat.")
        return
    
    print("\n Activare/Dezactivare feed")
    print("=" * 40)
    
    list_feeds()
    
    try:
        index = int(input("Numărul feed-ului de modificat (0 pentru anulare): ")) - 1
        
        if index == -1:
            print(" Operație anulată.")
            return
        
        if index < 0 or index >= len(feeds):
            print(" Număr invalid!")
            return
        
        feed = feeds[index]
        new_status = not feed['active']
        
        config['feeds'][index]['active'] = new_status
        save_config(config)
        
        status = " ACTIVAT" if new_status else " DEZACTIVAT"
        print(f" Feed {status}: {feed['name']}")
        
    except ValueError:
        print(" Te rog să introduci un număr valid!")

def edit_settings():
    """Editează setările generale."""
    config = load_config()
    settings = config['settings']
    
    print("\n  Editare setări")
    print("=" * 40)
    print(f"Interval actualizare: {settings['update_interval']} secunde")
    print(f"Articole maxime per feed: {settings['max_articles_per_feed']}")
    print(f"Timeout cereri: {settings['request_timeout']} secunde")
    
    print("\n1. Interval actualizare")
    print("2. Articole maxime per feed")
    print("3. Timeout cereri")
    print("0. Înapoi")
    
    choice = input("Alege setarea de modificat: ").strip()
    
    if choice == '1':
        try:
            new_interval = int(input(f"Interval nou (actual: {settings['update_interval']}): "))
            if new_interval > 0:
                settings['update_interval'] = new_interval
                save_config(config)
                print(f" Interval actualizat la {new_interval} secunde")
            else:
                print(" Intervalul trebuie să fie > 0")
        except ValueError:
            print(" Te rog să introduci un număr valid!")
    
    elif choice == '2':
        try:
            new_max = int(input(f"Număr maxim nou (actual: {settings['max_articles_per_feed']}): "))
            if new_max > 0:
                settings['max_articles_per_feed'] = new_max
                save_config(config)
                print(f" Maxim actualizat la {new_max} articole")
            else:
                print(" Numărul trebuie să fie > 0")
        except ValueError:
            print(" Te rog să introduci un număr valid!")
    
    elif choice == '3':
        try:
            new_timeout = int(input(f"Timeout nou (actual: {settings['request_timeout']}): "))
            if new_timeout > 0:
                settings['request_timeout'] = new_timeout
                save_config(config)
                print(f" Timeout actualizat la {new_timeout} secunde")
            else:
                print(" Timeout-ul trebuie să fie > 0")
        except ValueError:
            print(" Te rog să introduci un număr valid!")

def main():
    """Meniul principal."""
    while True:
        print("\n" + "=" * 50)
        print("RSS FEED MANAGER")
        print("=" * 50)
        print("1. Listează feed-urile")
        print("2. Adaugă feed nou")
        print("3. Șterge feed")
        print("4. Activează/Dezactivează feed")
        print("5. Editează setări")
        print("0. Ieșire")
        print("=" * 50)
        
        choice = input("Alege o opțiune: ").strip()
        
        try:
            if choice == '1':
                list_feeds()
            elif choice == '2':
                add_feed()
            elif choice == '3':
                remove_feed()
            elif choice == '4':
                toggle_feed()
            elif choice == '5':
                edit_settings()
            elif choice == '0':
                print("La revedere!")
                break
            else:
                print("Opțiune invalidă!")
                
        except Exception as e:
            print(f"Eroare: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n Programul a fost întrerupt. La revedere!")
    except Exception as e:
        print(f"\n Eroare neașteptată: {e}")