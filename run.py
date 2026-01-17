import sys
from streamlit.web import cli as stcli
import os

def main():
    # Pobieramy ścieżkę do gui.py relatywnie do tego pliku
    script_path = os.path.join(os.path.dirname(__file__), "gui.py")
    
    # Ustawiamy argumenty tak, jakbyśmy wpisali "streamlit run gui.py" w terminalu
    sys.argv = ["streamlit", "run", script_path]
    
    # Uruchamiamy Streamlit
    sys.exit(stcli.main())

if __name__ == "__main__":
    main()
