import sqlite3
import pandas as pd
import datetime

DB_NAME = "oferty.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            price TEXT,
            url TEXT UNIQUE,
            location TEXT,
            image_url TEXT,
            search_query TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def add_offer(offer):
    """
    Dodaje ofertę do bazy. Zwraca True jeśli dodano nową, False jeśli już istniała.
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    try:
        c.execute('''
            INSERT INTO offers (title, price, url, location, image_url, search_query, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            offer.get('title'),
            offer.get('price'),
            offer.get('url'),
            offer.get('location'),
            offer.get('image_url'),
            offer.get('search_query', 'unknown'),
            datetime.datetime.now()
        ))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Oferta z tym URL już istnieje
        return False
    finally:
        conn.close()

def get_all_offers_df():
    """
    Zwraca wszystkie oferty jako pandas DataFrame
    """
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM offers ORDER BY created_at DESC", conn)
    conn.close()
    return df
