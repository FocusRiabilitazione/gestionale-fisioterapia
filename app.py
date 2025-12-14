import streamlit as st
from pyairtable import Api
import pandas as pd
from requests.exceptions import HTTPError
import altair as alt

# --- 1. CONFIGURAZIONE CONNESSIONE ---
try:
    API_KEY = st.secrets["AIRTABLE_TOKEN"]
    BASE_ID = st.secrets["AIRTABLE_BASE_ID"]
except FileNotFoundError:
    API_KEY = "tua_chiave"
    BASE_ID = "tuo_base_id"

api = Api(API_KEY)

# --- 2. FUNZIONI ---

def get_data(table_name):
    """Scarica i dati da Airtable, incluso l'ID nascosto per poter fare modifiche"""
    try:
        table = api.table(BASE_ID, table_name)
        records = table.all()
        if not records:
            return pd.DataFrame()
        # Qui prendiamo anche l'id del record ('id') oltre ai campi ('fields')
        data = [{'id': r['id'], **r['fields']} for r in records]
        return pd.DataFrame(data)
    except Exception as e:
        return pd.DataFrame()

def save_paziente(nome, cognome, area, disdetto):
    """Salva un nuovo paziente"""
    table = api.table(BASE_ID, "Pazienti")
    record = {
        "Nome": nome,
        "Cognome": cognome,
        "Area": area,
        "Disdetto": disdetto 
    }
    table.create(record, typecast=True)

def update_paziente(record_id, nuovo_stato):
    """Aggiorna lo stato Disdetto di un paziente esistente"""
    table = api.table(BASE_ID, "Pazienti")
    table.update(record_id, {"Disdetto": nuovo_stato})

# --- 3. INTERFACCIA GRAFICA ---

st.set_page_config(page_title="Gestionale Fisio", page_icon="🏥", layout="wide")

# Menu Laterale
st.sidebar.title("Navigazione")
menu = st.sidebar.radio(
    "Vai a:", 
    ["📊 Dashboard & Allarmi", "👥 Gestione Pazienti", "💰 Calcolo Preventivo", "📝 Scadenze Ufficio"]
)
st.sidebar.divider()
st.sidebar.info("App collegata ad Airtable.")

# =========================================================
# SEZIONE 1: DASHBOARD
# =========================================================
if menu == "📊 Dashboard & Allarmi":
    
    try:
        st.image("logo.png", width=300) 
    except FileNotFoundError:
        st.title("Buongiorno! ☕")
        st.warning("ℹ️ Carica 'logo.png' nella cartella per vedere il logo qui.")

    st.write("Panoramica dello studio.")
    
    df = get_data("Pazienti")
    
    if not df.empty:
        if 'Disdetto' not in df.columns:
            df['Disdetto'] = False 

        totali = len(df)
        # Conta disdetti
        disdetti_count = len(df[ (df['Disdetto'] == True) | (df['Disdetto'] == 1) ])
        attivi = totali - disdetti_count
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Totale Anagrafica", totali)
        col2.metric("Pazienti Attivi", attivi)
        col3.metric("Pazienti Disdetti", disdetti_count, delta_color="inverse")
        
        st.divider()
        
        if 'Area' in df.columns:
            st.subheader("📍 Distribuzione per Area Trattata")
            
            all_areas = []
            for item in df['Area'].dropna():
                if isinstance(item, list):
                    all_areas.extend(item)
                elif isinstance(item, str):
                    all_areas.extend([p.strip() for p in item.split(',')])
                else:
                    all_areas.append(str(item))
            
            if all_areas:
                counts = pd.Series(all_areas).value_counts().reset_index()
                counts.columns = ['Area', 'Pazienti']
                
                domain = ["Mano-Polso", "Colonna", "ATM", "Muscolo-Scheletrico", "Gruppi", "Ortopedico"]
                range_ = ["#33A1C9", "#F1C40F", "#2ECC71", "#9B59B6", "#E74C3C", "#7F8C8D"]

                chart = alt.Chart(counts).mark_bar().encode(
                    x=alt.X('Area', sort='-y', title="Area Trattata"),
                    y=alt.Y('Pazienti', title="Numero Pazienti"),
                    color=alt.Color('Area', scale=alt.Scale(domain=domain, range=range_), legend=None),
                    tooltip=['Area', 'Pazienti']
                ).properties(
                    height=400
                )
                
                st.altair_chart(chart, use_container_width=True)
                
    else:
        st.info("Nessun dato pazienti trovato.")

# =========================================================
# SEZIONE 2: GESTIONE PAZIENTI (MODIFICABILE + CERCA)
# =========================================================
elif menu == "👥 Gestione Pazienti":
    st.title("📂 Anagrafica Pazienti")
    
    lista_aree = [
        "Mano-Polso", "Colonna", "ATM", 
        "Muscolo-Scheletrico", "Gruppi", "Ortopedico"
    ]
    
    # --- FORM INSERIMENTO ---
    with st.expander("➕ Nuovo Inserimento (Clicca per aprire)", expanded=False):
        with st.form("form_paziente", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                nome = st.text_input("Nome")
                aree_scelte = st.multiselect("Area Trattata", options=lista_aree)
            with c2:
                cognome = st.text_input("Cognome")
                
            submit = st.form_submit_button("Salva nel Database")
            
            if submit:
                if nome and cognome:
                    try:
                        area_stringa = ", ".join(aree_scelte)
                        save_paziente(nome, cognome, area_stringa, False)
                        st.success(f"✅ {nome} {cognome} salvato!")
                        st.rerun() # Ricarica la pagina per vedere il nuovo dato
                    except HTTPError as e:
                        st.error("❌ Errore Airtable.")
                    except Exception as e:
                        st.error(f"❌ Errore: {e}")
                else:
                    st.warning("⚠️ Nome e Cognome obbligatori.")

    st.divider()
    
    # --- TABELLA INTERATTIVA ---
    st.subheader("Elenco e Modifica Rapida")
    
    # 1. Carichiamo i dati
    df_original = get_data("Pazienti")
    
    if not df_original.empty:
        if 'Disdetto' not in df_original.columns:
            df_original['Disdetto'] = False

        # 2. BARRA DI RICERCA
        search_query = st.text_input("🔍 Cerca Paziente per Cognome", placeholder="Es. Rossi...")
        
        # Filtriamo il dataframe se c'è una ricerca
        if search_query:
            # Filtra dove il cognome contiene il testo cercato (case insensitive)
            df_filtered = df_original[df_original['Cognome'].astype(str).str.contains(search_query, case=False, na=False)]
        else:
            df_filtered = df_original

        # 3. PREPARIAMO LA TABELLA EDITABILE
        # Selezioniamo le colonne da mostrare (incluso l'ID nascosto che ci serve)
        cols_to_show = ['Nome', 'Cognome', 'Area', 'Disdetto', 'id']
        # Mettiamo 'id' per ultimo o comunque ci assicuriamo che esista
        available_cols = [c for c in cols_to_show if c in df_filtered.columns]
        
        # TABELLA MODIFICABILE
        st.info("💡 Spunta la casella 'Disdetto' per cambiare stato. Poi clicca 'Salva Modifiche' in basso.")
        
        edited_df = st.data_editor(
            df_filtered[available_cols],
            column_config={
                "Disdetto": st.column_config.CheckboxColumn(
                    "Disdetto",
                    help="Spunta se il paziente ha disdetto",
                    default=False,
                ),
                "id": None, # Nasconde la colonna ID ma mantiene i dati
            },
            disabled=["Nome", "Cognome", "Area"], # Blocca la modifica di nome/cognome/area
            hide_index=True,
            use_container_width=True,
            key="editor_pazienti"
        )

        # 4. BOTTONE DI SALVATAGGIO
        if st.button("💾 Salva Modifiche su Airtable"):
            changes_count = 0
            
            # Confrontiamo i dati modificati con quelli originali per trovare le differenze
            # Iteriamo su edited_df
            for index, row in edited_df.iterrows():
                record_id = row['id']
                nuovo_stato = row['Disdetto']
                
                # Cerchiamo lo stato originale di questo ID nel dataframe originale
                original_row = df_original[df_original['id'] == record_id]
                
                if not original_row.empty:
                    vecchio_stato = original_row.iloc[0]['Disdetto']
                    # Airtable a volte restituisce None o 0, normalizziamo a booleano
                    vecchio_stato = bool(vecchio_stato)
                    nuovo_stato = bool(nuovo_stato)

                    if vecchio_stato != nuovo_stato:
                        # C'è stato un cambiamento! Aggiorniamo Airtable
                        try:
                            update_paziente(record_id, nuovo_stato)
                            changes_count += 1
                        except Exception as e:
                            st.error(f"Errore aggiornamento ID {record_id}: {e}")
            
            if changes_count > 0:
                st.success(f"✅ Aggiornati {changes_count} pazienti!")
                st.rerun() # Ricarica per aggiornare i dati originali
            else:
                st.info("Nessuna modifica rilevata.")

    else:
        st.info("Database vuoto.")

# =========================================================
# SEZIONE 3: PREVENTIVI
# =========================================================
elif menu == "💰 Calcolo Preventivo":
    st.title("Generatore Preventivi")
    listino = {
        "Valutazione Iniziale": 50, 
        "Seduta Tecar": 35, 
        "Laser Terapia": 30,
        "Rieducazione Motoria": 45, 
        "Massaggio Decontratturante": 50, 
        "Onde d'Urto": 40
    }
    
    c1, c2 = st.columns([2, 1])
    with c1: scelte = st.multiselect("Scegli Trattamenti", list(listino.keys()))
        
    totale = 0
    if scelte:
        st.write("---")
        for t in scelte:
            qty = st.number_input(f"Sedute di {t}", 1, 20, 5, key=t)
            costo = listino[t] * qty
            st.write(f"▫️ {t}: {listino[t]}€ x {qty} = **{costo} €**")
            totale += costo
        st.write("---")
        st.subheader(f"TOTALE: {totale} €")
        
        if totale > 300: 
            st.success(f"SCONTO PACCHETTO: **{int(totale*0.9)} €**")

# =========================================================
# SEZIONE 4: SCADENZE
# =========================================================
elif menu == "📝 Scadenze Ufficio":
    st.title("Checklist Pagamenti")
    df_scad = get_data("Scadenze")
    if not df_scad.empty:
        if 'Data_Scadenza' in df_scad.columns:
            df_scad = df_scad.sort_values("Data_Scadenza")
        st.dataframe(df_scad, use_container_width=True)
    else:
        st.info("Nessuna scadenza trovata.")
