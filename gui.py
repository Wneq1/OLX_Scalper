import streamlit as st
import pandas as pd
from fetcher import uruchom_olx
import database
import time
import threading
import os

# Funkcja monitorująca aktywność sesji
def watch_sessions():
    time.sleep(3) # Daj czas na start
    while True:
        try:
            from streamlit.runtime import get_instance
            runtime = get_instance()
            if runtime:
                sessions = runtime._session_mgr.list_active_sessions()
                if not sessions:
                    # Dodatkowe sprawdzenie po chwili (np. przy odświeżaniu F5)
                    time.sleep(2)
                    if not runtime._session_mgr.list_active_sessions():
                        os._exit(0)
        except Exception:
            pass
        time.sleep(2)

# Start wątku monitorującego (tylko raz)
if 'watchdog_active' not in st.session_state:
    st.session_state.watchdog_active = True
    t = threading.Thread(target=watch_sessions, daemon=True)
    t.start()

# Inicjalizacja bazy danych przy starcie
database.init_db()

# Konfiguracja strony
st.set_page_config(
    page_title="Scalper OLX",
    page_icon="🔍",
    layout="wide"
)

# Custom CSS dla lepszego wyglądu
# Custom CSS dla lepszego wyglądu
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        background-color: #ff5a00;
        color: white;
    }
    .price-tag {
        font-weight: bold;
        color: #ff5a00;
        font-size: 1.2em;
    }
    /* Nowe style dla kafelków */
    .img-container {
        height: 200px;
        width: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: #ffffff;
        margin-bottom: 10px;
        overflow: hidden;
        border-radius: 4px;
    }
    .img-container img {
        max-height: 100%;
        max-width: 100%;
        object-fit: contain;
    }
    .img-placeholder {
        height: 200px; 
        width: 100%; 
        background-color: #f0f2f6; 
        display: flex; 
        align-items: center; 
        justify-content: center; 
        color: #888;
        border-radius: 4px;
        margin-bottom: 10px;
    }
    .offer-title {
        height: 3.6em; /* ok. 3 linie tekstu */
        line-height: 1.2em;
        overflow: hidden;
        text-overflow: ellipsis;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        font-weight: 600;
        font-size: 1rem;
        margin-bottom: 0.5rem;
        color: #262730; /* Streamlit default dark text */
    }
    /* Tryb ciemny - dostosowanie tekstu */
    @media (prefers-color-scheme: dark) {
        .offer-title {
            color: #fafafa;
        }
    }
    
    /* Sticky Search Header */
    /* Targetujemy diva, który jest rodzicem naszego markera */
    div[data-testid="stVerticalBlock"] > div:has(.sticky-search-marker) {
        position: sticky;
        top: 0;
        z-index: 999;
        background-color: var(--background-color, white);
        padding-top: 0.5rem;   /* Mniejszy padding góra */
        padding-bottom: 0.5rem; /* Mniejszy padding dół */
        border-bottom: 1px solid rgba(49, 51, 63, 0.1);
        margin-bottom: 1rem;
    }
    /* Fix dla dark mode tła */
    @media (prefers-color-scheme: dark) {
         div[data-testid="stVerticalBlock"] > div:has(.sticky-search-marker) {
            background-color: #0e1117; /* Streamlit dark default */
            border-bottom: 1px solid rgba(250, 250, 250, 0.1);
         }
    }
    </style>
""", unsafe_allow_html=True)

def main():
    st.title("🔍 Scalper OLX - Wyszukiwarka Ofert")
    
    # Tworzymy zakładki
    tab1, tab2 = st.tabs(["🔎 Wyszukiwanie", "📜 Historia i Wizualizacja"])
    
    with tab1:
        # Layout: Kolumna lewa (Ustawienia) i Prawa (Wyszukiwarka + Wyniki)
        col_settings, col_results = st.columns([1, 3])
        
        with col_settings:
            st.markdown("### Ustawienia")
            
            # Przeniesione filtry na lewo
            max_ofert = st.slider(
                "Max ofert/frazę",
                min_value=5,
                max_value=100,
                value=20,
                step=5
            )
            
            st.markdown("---")
            widok = st.radio("Widok:", ["Siatka", "Lista"], index=0)
            
            st.markdown("---")
            sortowanie = st.selectbox(
                "Sortuj:",
                ["Domyślnie (Trafność)", "Cena: rosnąco", "Cena: malejąco"]
            )
            
            # Usunięto przycisk "Zakończ" zgodnie z prośbą

        with col_results:
            # Wyszukiwarka - "Sticky" (przyklejona u góry)
            # Używamy kontenera, który spróbujemy "przykleić" za pomocą CSS
            search_container = st.container()
            with search_container:
                st.markdown('<div class="sticky-search-marker"></div>', unsafe_allow_html=True)
                col_search_input, col_search_btn = st.columns([4, 1])
                
                with col_search_input:
                    # Zmiana na text_input dla mniejszej wysokości (jak przycisk)
                    frazy_input = st.text_input(
                        "Wpisz frazy (oddzielone przecinkami)",
                        value="iphone 13, ps4 pro",
                        help="Wpisz nazwy przedmiotów, których szukasz.",
                        label_visibility="collapsed",
                        placeholder="Wpisz frazy np. iphone 13, ps4 pro..."
                    )
                
                with col_search_btn:
                    # Pusty element niepotrzebny przy text_input bo mają podobną wysokość
                    # ewentualnie mały margin-top jeśli się rozjeżdża, ale zazwyczaj text_input == button
                    szukaj_btn = st.button("🔎 Szukaj", use_container_width=True)
                
                st.markdown("---") # Oddzielenie od wyników

            # Logika wyszukiwania
            if 'search_results' not in st.session_state:
                st.session_state.search_results = []
            if 'search_performed' not in st.session_state:
                st.session_state.search_performed = False

            if szukaj_btn:
                frazy = [f.strip() for f in frazy_input.split(",") if f.strip()]
                
                if not frazy:
                    st.warning("⚠️ Proszę wpisać przynajmniej jedną frazę.")
                else:
                    with st.spinner('Pobieram oferty z OLX...'):
                        wyniki = uruchom_olx(frazy, max_ofert=max_ofert, verbose=True)
                    
                    if not wyniki:
                        st.session_state.search_results = []
                        st.info("Nie znaleziono żadnych ofert dla podanych fraz.")
                    else:
                        st.session_state.search_results = wyniki
                        st.session_state.search_performed = True
                        
                        # Zapisywanie do bazy
                        nowe_count = 0
                        for oferta in wyniki:
                            if database.add_offer(oferta):
                                nowe_count += 1
                        
                        if nowe_count > 0:
                            st.success(f"Znaleziono {len(wyniki)} ofert. Dodano {nowe_count} nowych do bazy!")
                        else:
                            st.info(f"Znaleziono {len(wyniki)} ofert (wszystkie już były w bazie).")

            # Wyświetlanie wyników
            if st.session_state.search_results:
                wyniki_to_display = st.session_state.search_results.copy()
                
                # Sortowanie
                if sortowanie != "Domyślnie (Trafność)":
                    def parse_price(offer):
                        try:
                            p = str(offer.get('price', '0'))
                            p = p.lower().replace('zł', '').replace(' ', '').replace(',', '.')
                            import re
                            match = re.search(r'(\d+\.?\d*)', p)
                            return float(match.group(1)) if match else 0.0
                        except:
                            return 0.0

                    reverse_sort = sortowanie == "Cena: malejąco"
                    wyniki_to_display.sort(key=parse_price, reverse=reverse_sort)

                if widok == "Siatka":
                    for i in range(0, len(wyniki_to_display), 3):
                        batch = wyniki_to_display[i:i+3]
                        cols = st.columns(3)
                        
                        for j, oferta in enumerate(batch):
                            with cols[j]:
                                with st.container(border=True):
                                    img_url = oferta.get('image_url')
                                    if img_url:
                                        st.markdown(f'<div class="img-container"><img src="{img_url}"></div>', unsafe_allow_html=True)
                                    else:
                                        st.markdown('<div class="img-placeholder">Brak zdjęcia</div>', unsafe_allow_html=True)
                                    
                                    title = oferta.get('title', 'Brak tytułu').replace('"', '&quot;')
                                    st.markdown(f'<div class="offer-title" title="{title}">{title}</div>', unsafe_allow_html=True)
                                    
                                    cena = oferta.get('price', '???')
                                    st.markdown(f"<div class='price-tag'>{cena} zł</div>", unsafe_allow_html=True)
                                    
                                    if 'location' in oferta:
                                        st.caption(f"📍 {oferta['location']}")
                                    
                                    st.markdown("---")
                                    url = oferta.get('url', '#')
                                    st.link_button("Zobacz ofertę", url, use_container_width=True)
                
                else:
                    # Lista
                    for oferta in wyniki_to_display:
                        with st.container(border=True):
                            col_img, col_info, col_action = st.columns([2, 4, 2])
                            
                            with col_img:
                                img_url = oferta.get('image_url')
                                if img_url:
                                    try:
                                        st.image(img_url, use_container_width=True)
                                    except:
                                        st.write("Brak zdjęcia")
                                else:
                                    st.markdown("<div style='height: 100px; display:flex; align-items:center; justify-content:center; background:#eee;'>Brak</div>", unsafe_allow_html=True)
                            
                            with col_info:
                                st.subheader(oferta.get('title', 'Brak tytułu'))
                                if 'location' in oferta:
                                    st.write(f"📍 {oferta['location']}")
                            
                            with col_action:
                                cena = oferta.get('price', '???')
                                st.markdown(f"<div class='price-tag' style='text-align:right;'>{cena} zł</div>", unsafe_allow_html=True)
                                url = oferta.get('url', '#')
                                st.link_button("Zobacz ofertę", url, use_container_width=True)
            elif st.session_state.search_performed and not st.session_state.search_results:
                 st.info("Brak wyników do wyświetlenia.")

    with tab2:
        st.header("📜 Historia z Bazy Danych")
        
        if st.button("Odśwież historię"):
            st.rerun()
            
        df = database.get_all_offers_df()
        
        if df.empty:
            st.info("Baza danych jest pusta. Wykonaj wyszukiwanie, aby dodać oferty.")
        else:
            # Wizualizacja: Liczba ofert w czasie (wg search_query)
            st.subheader("📊 Statystyki")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("Liczba ofert wg frazy:")
                st.bar_chart(df['search_query'].value_counts())
                
            with col2:
                # Próba konwersji ceny na liczbę do wykresu (proste czyszczenie)
                try:
                    df['price_num'] = df['price'].astype(str).str.replace(' ', '').str.replace('zł', '').str.replace(',', '.').str.extract(r'(\d+\.?\d*)').astype(float)
                    st.write("Rozkład cen (wszystkie oferty):")
                    st.scatter_chart(data=df, x='created_at', y='price_num', color='search_query')
                except Exception as e:
                    st.warning("Nie udało się wygenerować wykresu cen (możliwe błędy w formacie danych).")

            st.subheader("📋 Tabela danych")
            st.dataframe(df.sort_values(by='created_at', ascending=False), use_container_width=True)
            
            # Galeria z historii (opcjonalnie)
            st.subheader("🖼️ Galeria ostatnich ofert")
            cols_hist = st.columns(4)
            for i, row in df.head(8).iterrows():
                 with cols_hist[i % 4]:
                    if row.get('image_url'):
                        try:
                            # Tutaj też można by użyć poprawionego CSS, ale galeria była ok
                            st.image(row['image_url'], caption=f"{row['price']} zł", use_container_width=True)
                        except:
                            st.markdown(f"**{row['title']}**<br>{row['price']}", unsafe_allow_html=True)
                    else:
                        st.markdown(f"**{row['title']}**<br>{row['price']}", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
