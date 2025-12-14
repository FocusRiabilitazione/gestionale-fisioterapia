import streamlit as st
from pyairtable import Api
import pandas as pd
from requests.exceptions import HTTPError

# --- 1. CONFIGURAZIONE CONNESSIONE ---
try:
    API_KEY = st.secrets["AIRTABLE_TOKEN"]
    BASE_ID = st.secrets["AIRTABLE_BASE_ID"]
except FileNotFoundError:
    # Chiavi di riserva per test locale (se non usi secrets)
    API_KEY = "tua_chiave"
    BASE_ID = "tuo_base_id"

api = Api(API_KEY)

# --- 2. FUNZIONI ---

def get_data(table_name):
    """Scarica i dati da Airtable"""
    try:
        table = api.table(BASE_ID, table_name)
        records = table.all()
        if not records:
            return pd.DataFrame()
        data = [r['fields'] for r in records]
        return pd.DataFrame(data)
    except Exception as e:
        return pd.DataFrame()

def save_paziente(nome, cognome, area, disdetto):
    """Salva solo i 4 dati richiesti"""
    table = api.table(BASE_ID, "Pazienti")
    
    # I nomi a sinistra devono essere identici alle colonne su Airtable
    record = {
        "Nome": nome,
        "Cognome": cognome,
        "Area": area,
        "Disdetto": disdetto  # Invierà True (spuntato) o False (vuoto)
    }
    
    table.create(record, typecast=True)

# --- 3. INTERFACCIA GRAFICA ---

st.set_page_config(page_title="Gestionale Semplificato", page_icon="📋", layout="wide")

st.title("📂 Gestione Pazienti")
st.info("Campi attivi: Nome, Cognome, Area, Disdetto")

# --- MODULO DI INSERIMENTO ---
with st.container(border=True):
    st.subheader("Nuovo Inserimento")
    with st.form("form_semplice", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            nome = st.text_input("Nome")
            area = st.text_input("Area (es. Lombare, Cervicale)")
        
        with col2:
            cognome = st.text_input("Cognome")
            # Checkbox per disdetto
            disdetto = st.checkbox("Disdetto (Spunta se il paziente ha disdetto)")

        submit = st.form_submit_button("Salva Paziente")

        if submit:
            if nome and cognome:
                try:
                    save_paziente(nome, cognome, area, disdetto)
                    st.success(f"✅ {nome} {cognome} salvato correttamente!")
                except HTTPError as e:
                    st.error("❌ Errore Airtable. Controlla che le colonne 'Nome', 'Cognome', 'Area', 'Disdetto' esistano.")
                    st.code(e.response.text)
                except Exception as e:
                    st.error(f"Errore generico: {e}")
            else:
                st.warning("⚠️ Nome e Cognome sono obbligatori.")

# --- VISUALIZZAZIONE DATI ---
st.divider()
st.subheader("📋 Elenco Pazienti")

df = get_data("Pazienti")

if not df.empty:
    # Filtro rapido (opzionale)
    filtro_disdetti = st.toggle("Mostra solo i disdetti")
    
    # Assicuriamoci che la colonna Disdetto esista nel dataframe per evitare errori
    if 'Disdetto' not in df.columns:
        df['Disdetto'] = False # Se manca, assumiamo nessuno sia disdetto

    if filtro_disdetti:
        df_show = df[df['Disdetto'] == True]
    else:
        df_show = df

    # Mostriamo la tabella ordinata
    st.dataframe(
        df_show, 
        column_config={
            "Disdetto": st.column_config.CheckboxColumn("Disdetto", default=False)
        },
        use_container_width=True
    )
    
    # Contatori semplici
    totale = len(df)
    disdetti_count = len(df[df['Disdetto'] == True])
    st.caption(f"Totale in lista: {totale} | Disdetti: {disdetti_count}")

else:
    st.info("Nessun paziente trovato nel database.")
