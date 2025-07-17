import socket
import json
import time
import curses
import webbrowser
import textwrap
from datetime import datetime

SERVER_HOST = '127.0.0.1'  
SERVER_PORT = 5000         
REFRESH_INTERVAL = 60      


def fetch_feed():
    """
    Se conectează la server și primește ultimele știri în format JSON.
    """
    try:
        with socket.create_connection((SERVER_HOST, SERVER_PORT), timeout=5) as sock:
            sock.sendall(b'GET_FEED')
            data = b''
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                data += chunk
            
            # Verifică dacă avem date
            if not data:
                return {'error': 'Nu s-au primit date de la server'}
            
            # Încearcă să decodeze JSON
            try:
                return json.loads(data.decode())
            except json.JSONDecodeError as e:
                # Încearcă să afișeze ce a primit pentru debug
                received_text = data.decode()[:200]  # Primele 200 caractere
                return {'error': f'Răspuns invalid de la server: {received_text}...'}
                
    except (ConnectionRefusedError, socket.timeout) as e:
        return {'error': f'Nu se poate contacta serverul: {e}'}
    except Exception as e:
        return {'error': f'Eroare neașteptată: {e}'}


def format_published_date(date_str):
    """Formatează data de publicare într-un format mai lizibil."""
    try:
        # Încearcă să parseze data în diverse formate
        for fmt in ['%a, %d %b %Y %H:%M:%S %z', '%a, %d %b %Y %H:%M:%S %Z', 
                   '%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%d %H:%M:%S']:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.strftime('%d.%m.%Y %H:%M')
            except ValueError:
                continue
        return date_str[:16]  # Returnează primele 16 caractere dacă nu poate parsa
    except:
        return "Data necunoscută"


def wrap_text(text, width):
    """Împarte textul în linii de lățimea specificată."""
    return textwrap.fill(text, width=width, break_long_words=False, break_on_hyphens=False)


def draw_header(stdscr, title, current_time):
    """Desenează header-ul aplicației."""
    try:
        max_y, max_x = stdscr.getmaxyx()
        
        # Verifică dacă avem dimensiuni valide
        if max_y < 3 or max_x < 10:
            return
        
        # Linie de separare (folosește caractere ASCII pentru compatibilitate)
        stdscr.addstr(0, 0, "=" * max_x, curses.A_BOLD)
        
        # Titlu centrat
        title_text = f" {title} "
        title_x = max(0, (max_x - len(title_text)) // 2)
        if title_x + len(title_text) < max_x:
            stdscr.addstr(0, title_x, title_text, curses.A_BOLD | curses.A_REVERSE)
        
        # Ora curentă în dreapta
        time_text = f" {current_time} "
        if len(time_text) < max_x:
            stdscr.addstr(0, max_x - len(time_text), time_text, curses.A_BOLD)
    except curses.error:
        pass  # Ignoră erorile de afișare


def draw_footer(stdscr, mode="list"):
    """Desenează footer-ul cu comenzile disponibile."""
    try:
        max_y, max_x = stdscr.getmaxyx()
        
        # Verifică dacă avem dimensiuni valide
        if max_y < 3 or max_x < 10:
            return
        
        if mode == "list":
            commands = "UP/DOWN: Navigare | ENTER: Detalii | R: Refresh | Q: Iesire"
        else:  # detail mode
            commands = "ESC/B: Inapoi | O: Deschide link | Q: Iesire"
        
        # Linie de separare (folosește caractere ASCII pentru compatibilitate)
        stdscr.addstr(max_y - 2, 0, "=" * max_x, curses.A_BOLD)
        
        # Comenzi centrate
        if len(commands) < max_x:
            commands_x = max(0, (max_x - len(commands)) // 2)
            stdscr.addstr(max_y - 1, commands_x, commands, curses.A_BOLD)
    except curses.error:
        pass  # Ignoră erorile de afișare


def draw_article_list(stdscr, articles, selected_index, scroll_offset):
    """Desenează lista de articole cu evidențierea selecției."""
    try:
        max_y, max_x = stdscr.getmaxyx()
        
        # Verifică dacă avem dimensiuni valide
        if max_y < 5 or max_x < 20:
            return
        
        # Spațiul disponibil pentru articole (minus header și footer)
        available_height = max_y - 4
        start_y = 2
        
        # Calculează câte articole se pot afișa
        visible_count = min(len(articles), available_height)
        
        for i in range(visible_count):
            article_index = i + scroll_offset
            if article_index >= len(articles):
                break
                
            article = articles[article_index]
            y_pos = start_y + i
            
            # Pregătește textul pentru afișare
            source = article.get('source', 'Necunoscut')
            title = article.get('title', 'Fără titlu')
            date = format_published_date(article.get('published', ''))
            
            # Formatează linia
            prefix = f"[{source}] "
            suffix = f" ({date})"
            
            # Calculează cât spațiu rămâne pentru titlu
            available_width = max_x - len(prefix) - len(suffix) - 8
            if available_width > 0 and len(title) > available_width:
                title = title[:available_width-3] + "..."
            
            line_text = f"{prefix}{title}{suffix}"
            
            # Limitează lungimea liniei la lățimea ecranului
            line_text = line_text[:max_x-6]
            
            # Afișează linia cu evidențierea selecției
            if article_index == selected_index:
                stdscr.addstr(y_pos, 2, "> ", curses.A_BOLD | curses.A_REVERSE)
                stdscr.addstr(y_pos, 4, line_text, curses.A_REVERSE)
            else:
                stdscr.addstr(y_pos, 2, "  ")
                stdscr.addstr(y_pos, 4, line_text)
        
        # Afișează indicatorul de scroll dacă e necesar
        if len(articles) > available_height:
            scroll_info = f"({scroll_offset + 1}-{min(scroll_offset + available_height, len(articles))} din {len(articles)})"
            if len(scroll_info) < max_x - 2:
                stdscr.addstr(1, max_x - len(scroll_info) - 2, scroll_info, curses.A_DIM)
    except curses.error:
        pass  # Ignoră erorile de afișare


def draw_article_detail(stdscr, article):
    """Desenează detaliile unui articol."""
    try:
        max_y, max_x = stdscr.getmaxyx()
        
        # Verifică dacă avem dimensiuni valide
        if max_y < 5 or max_x < 20:
            return
        
        # Spațiul disponibil pentru conținut
        available_height = max_y - 4
        content_width = max_x - 4
        
        y_pos = 2
        
        # Titlu
        title = article.get('title', 'Fără titlu')
        wrapped_title = wrap_text(title, content_width)
        for line in wrapped_title.split('\n'):
            if y_pos < max_y - 2:
                stdscr.addstr(y_pos, 2, line[:content_width], curses.A_BOLD)
                y_pos += 1
        
        y_pos += 1
        
        # Informații despre articol
        source = article.get('source', 'Necunoscut')
        date = format_published_date(article.get('published', ''))
        info_line = f"Sursa: {source} | Data: {date}"
        
        if y_pos < max_y - 2:
            stdscr.addstr(y_pos, 2, info_line[:content_width], curses.A_DIM)
            y_pos += 1
        
        y_pos += 1
        
        # Link
        link = article.get('link', '')
        if link and y_pos < max_y - 2:
            link_text = f"Link: {link}"
            if len(link_text) > content_width:
                link_text = link_text[:content_width-3] + "..."
            stdscr.addstr(y_pos, 2, link_text[:content_width], curses.A_UNDERLINE)
            y_pos += 1
        
        # Separator (folosește caractere ASCII pentru compatibilitate)
        if y_pos < max_y - 2:
            separator = "-" * min(content_width - 2, max_x - 4)
            stdscr.addstr(y_pos, 2, separator)
            y_pos += 1
        
        # Descriere (dacă există)
        description = article.get('description', 'Nu este disponibilă o descriere.')
        if y_pos < max_y - 2:
            wrapped_desc = wrap_text(description, content_width)
            for line in wrapped_desc.split('\n'):
                if y_pos < max_y - 2:
                    stdscr.addstr(y_pos, 2, line[:content_width])
                    y_pos += 1
                else:
                    break
    except curses.error:
        pass  # Ignoră erorile de afișare


def main(stdscr):
    # Configurare curses cu protecție maximă pentru Windows
    try:
        curses.curs_set(0)  # Ascunde cursorul
    except curses.error:
        pass  # Ignoră dacă terminalul nu suportă
    
    try:
        stdscr.nodelay(True)  # Fă getch() non-blocking
        stdscr.timeout(1000)  # Timeout de 1 secundă pentru getch()
    except curses.error:
        pass  # Folosește setările implicite dacă nu merge
    
    # Inițializează culorile dacă sunt disponibile
    try:
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
    except curses.error:
        pass  # Ignoră dacă terminalul nu suportă culorile
    
    # Variabile de stare
    selected_index = 0
    scroll_offset = 0
    current_mode = "list"  # "list" sau "detail"
    current_article = None
    articles = []
    last_refresh = 0
    
    while True:
        current_time = time.time()
        
        # Reîmprospătează datele la intervale regulate sau la cerere
        if current_time - last_refresh > REFRESH_INTERVAL or not articles:
            feed_data = fetch_feed()
            if 'articles' in feed_data:
                articles = feed_data['articles']
                last_refresh = current_time
                # Resetează selecția dacă depășește numărul de articole
                if selected_index >= len(articles):
                    selected_index = max(0, len(articles) - 1)
        
        # Curăță ecranul
        try:
            stdscr.clear()
        except curses.error:
            pass
        
        # Desenează interfața în funcție de modul curent
        if current_mode == "list":
            draw_header(stdscr, "RSS Feed Reader", datetime.now().strftime('%H:%M:%S'))
            
            if 'error' in feed_data:
                try:
                    stdscr.addstr(3, 2, f"Eroare: {feed_data['error']}", curses.A_BOLD)
                except curses.error:
                    pass
            elif articles:
                draw_article_list(stdscr, articles, selected_index, scroll_offset)
            else:
                try:
                    stdscr.addstr(3, 2, "Nu sunt articole disponibile.", curses.A_DIM)
                except curses.error:
                    pass
            
            draw_footer(stdscr, "list")
            
        elif current_mode == "detail" and current_article:
            draw_header(stdscr, "Detalii Articol", datetime.now().strftime('%H:%M:%S'))
            draw_article_detail(stdscr, current_article)
            draw_footer(stdscr, "detail")
        
        try:
            stdscr.refresh()
        except curses.error:
            pass
        
        # Procesează input-ul utilizatorului
        try:
            key = stdscr.getch()
            
            if key == ord('q') or key == ord('Q'):
                break
            
            elif current_mode == "list":
                if key == curses.KEY_UP and articles:
                    selected_index = max(0, selected_index - 1)
                    # Ajustează scroll-ul dacă e necesar
                    if selected_index < scroll_offset:
                        scroll_offset = selected_index
                        
                elif key == curses.KEY_DOWN and articles:
                    selected_index = min(len(articles) - 1, selected_index + 1)
                    # Ajustează scroll-ul dacă e necesar
                    max_y, max_x = stdscr.getmaxyx()
                    available_height = max_y - 4
                    if selected_index >= scroll_offset + available_height:
                        scroll_offset = selected_index - available_height + 1
                        
                elif key == ord('\n') or key == ord('\r'):  # Enter
                    if articles and 0 <= selected_index < len(articles):
                        current_article = articles[selected_index]
                        current_mode = "detail"
                        
                elif key == ord('r') or key == ord('R'):  # Refresh manual
                    last_refresh = 0  # Forțează refresh-ul la următoarea iterație
            
            elif current_mode == "detail":
                if key == 27 or key == ord('b') or key == ord('B'):  # ESC sau B
                    current_mode = "list"
                    current_article = None
                    
                elif key == ord('o') or key == ord('O'):  # Deschide link
                    if current_article and current_article.get('link'):
                        try:
                            webbrowser.open(current_article['link'])
                        except:
                            pass  # Ignoră erorile la deschiderea browser-ului
        
        except curses.error:
            pass  # Ignoră erorile de input


if __name__ == '__main__':
    curses.wrapper(main)