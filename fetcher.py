import requests
from bs4 import BeautifulSoup
import re
import json
import time
import random

def uruchom_olx(frazy, max_ofert=20, verbose=False):
    """
    Pobiera oferty z OLX dla podanych fraz.
    
    Args:
        frazy (list): Lista fraz do wyszukania.
        max_ofert (int): Maksymalna liczba ofert na frazę (ignorowane w tej prostej wersji, pobiera 1 stronę).
        verbose (bool): Czy wypisywać logi (print).
        
    Returns:
        list: Lista słowników z ofertami.
    """
    wszystkie_oferty = []
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7'
    }

    for fraza in frazy:
        # Przygotowanie URL - proste formatowanie
        query = fraza.replace(' ', '-').lower()
        url = f"https://www.olx.pl/oferty/q-{query}/"
        
        if verbose:
            print(f"[INFO] Pobieram: {url}")
            
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # --- JSON EXTRACTION LOGIC START ---
            offers_data_map = {}
            try:
                script_elem = soup.find('script', id='olx-init-config')
                if script_elem and script_elem.string:
                    # Look for window.__PRERENDERED_STATE__= "..."
                    match = re.search(r'window\.__PRERENDERED_STATE__\s*=\s*"(.*?)";', script_elem.string, re.DOTALL)
                    if match:
                        raw_json_str = match.group(1)
                        # Decode the JS string to get the JSON string
                        # We wrap it in quotes to make it a valid JSON string literal
                        json_str = json.loads(f'"{raw_json_str}"')
                        # Now parse the actual JSON data
                        data = json.loads(json_str)
                        
                        ads = data.get('listing', {}).get('listing', {}).get('ads', [])
                        for ad in ads:
                            # Map by ID (stringified)
                            if 'id' in ad:
                                offers_data_map[str(ad['id'])] = ad
                            # Also map by URL as backup
                            if 'url' in ad:
                                offers_data_map[ad['url']] = ad
                                
                        if verbose:
                            print(f"[INFO] Wyekstrahowano {len(ads)} ofert z JSON.")
                            
            except Exception as e:
                if verbose:
                    print(f"[WARN] Błąd parsowania JSON config (kontynuuję tylko z HTML): {e}")
            # --- JSON EXTRACTION LOGIC END ---

            # Główny kontener ofert (bazując na analizie HTML)
            oferty_html = soup.select('div[data-cy="l-card"]')
            
            count = 0
            for oferta_div in oferty_html:
                if count >= max_ofert:
                    break
                
                try:
                    # Tytuł
                    title_elem = oferta_div.select_one('h6')
                    if not title_elem:
                         title_elem = oferta_div.select_one('h4')
                    
                    if not title_elem:
                        continue 

                    title = title_elem.get_text(strip=True)
                    
                    # Link
                    link_elem = oferta_div.select_one('a')
                    link = link_elem['href'] if link_elem else None
                    if link and not link.startswith('http'):
                        link = f"https://www.olx.pl{link}"
                    
                    # Cena
                    price_elem = oferta_div.select_one('p[data-testid="ad-price"]')
                    price = price_elem.get_text(strip=True) if price_elem else 'Brak ceny'
                    
                    # Lokalizacja i data
                    loc_date_elem = oferta_div.select_one('p[data-testid="location-date"]')
                    location = loc_date_elem.get_text(strip=True) if loc_date_elem else 'Polska'
                    
                    # Zdjęcie
                    image_url = None
                    
                    # 1. Próba znalezienia w danych JSON (najlepsza jakość i pewność)
                    offer_id = oferta_div.get('id') # ID div-a często odpowiada ID oferty
                    json_offer = None
                    
                    if offer_id and str(offer_id) in offers_data_map:
                        json_offer = offers_data_map[str(offer_id)]
                    elif link and link in offers_data_map:
                         json_offer = offers_data_map[link]
                    
                    if json_offer:
                        photos = json_offer.get('photos', [])
                        if photos and len(photos) > 0:
                            # Zazwyczaj pierwsze zdjęcie jest główne
                            image_url = photos[0]
                            # Czasem photos to lista URLi, czasem obiektów? Sprawdzam raw_config.txt:
                            # "photos":["https://...", ...] - to lista stringów!
                            
                    # 2. Jeśli nie znaleziono w JSON, fallback do HTML parsing
                    if not image_url:
                        img_elem = oferta_div.select_one('img')
                        if img_elem:
                            src = img_elem.get('src')
                            data_src = img_elem.get('data-src')
                            srcset = img_elem.get('srcset')
                            data_srcset = img_elem.get('data-srcset')

                            urls_to_check = []
                            
                            def parse_srcset(ss):
                                if not ss: return []
                                parts = ss.split(',')
                                if parts:
                                    last_part = parts[-1].strip().split(' ')[0]
                                    return [last_part]
                                return []

                            urls_to_check.extend(parse_srcset(data_srcset))
                            urls_to_check.extend(parse_srcset(srcset))
                            if data_src: urls_to_check.append(data_src)
                            if src: urls_to_check.append(src)

                            for url in urls_to_check:
                                if url and 'http' in url and 'no_thumbnail' not in url and not url.startswith('data:'):
                                    image_url = url
                                    break
                                
                    # Filtrowanie placeholderów końcowe
                    if image_url and ('no_thumbnail' in image_url or image_url.startswith('data:') or not image_url.startswith('http')):
                         image_url = None

                    oferta_dict = {
                        'title': title,
                        'price': price,
                        'url': link,
                        'location': location,
                        'image_url': image_url,
                        'search_query': fraza
                    }
                    
                    wszystkie_oferty.append(oferta_dict)
                    count += 1
                    
                except Exception as e:
                    if verbose:
                        print(f"[WARN] Błąd parsowania oferty: {e}")
                    continue
                    
            time.sleep(random.uniform(0.5, 1.5)) # Lekkie opóźnienie między frazami
            
        except Exception as e:
            if verbose:
                print(f"[ERROR] Błąd pobierania {url}: {e}")
                
    return wszystkie_oferty
