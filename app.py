import streamlit as st
from pyairtable import Api
import pandas as pd
from requests.exceptions import HTTPError
import altair as alt
from datetime import date, timedelta

# --- 1. CONFIGURAZIONE CONNESSIONE ---
try:
    API_KEY = st.secrets["AIRTABLE_TOKEN"]
    BASE_ID = st.secrets["AIRTABLE_BASE_ID"]
except FileNotFoundError:
    API_KEY = "tua_chiave"
    BASE_ID = "tuo_base_id"

api = Api(API_KEY)

# --- 2. FUNZIONI ---

@st.cache_data(ttl=60)
def get_data(table_name):
    """Scarica i dati da Airtable e li converte in DataFrame"""
    try:
        table = api.table(BASE_ID, table_name)
        records = table.all()
        if not records:
            return pd.DataFrame()
        
        data = [{'id': r['id'], **r['fields']} for r in records]
        df = pd.DataFrame(data)
        return df
    except Exception as e:
        # In produzione puoi commentare il print se vuoi la console pulita
        print(f"Errore caricamento {table_name}: {e}")
        return pd.DataFrame()

def save_paziente(nome, cognome, area, disdetto):
    """Salva un nuovo paziente su Airtable"""
    table = api.table(BASE_ID, "Pazienti")
    record = {
        "Nome": nome,
        "Cognome": cognome,
        "Area": area,
        "Disdetto": disdetto 
    }
    # Puliamo la cache per vedere subito il nuovo dato
    get_data.clear()
    table.create(record, typecast=True)

def update_paziente_completo(record_id, dati_aggiornati):
    """
    Funzione unica per aggiornare qualsiasi campo del paziente.
    Accetta un dizionario: {'Colonna': Valore}
    """
    table = api.table(BASE_ID, "Pazienti")
    
    # Pulizia date: Se il valore è NaT o vuoto, lo forziamo a None per Airtable
    fields_to_send = {}
    for k, v in dati_aggiornati.items():
        if "Data" in k: # Se è una colonna data
            if pd.isna(v) or str(v) == "NaT" or v == "":
                fields_to_send[k] = None
            else:
                fields_to_send[k] = str(v)
        else:
            fields_to_send[k] = v
            
    table.update(record_id, fields_to_send, typecast=True)

def delete_paziente(record_id):
    """Elimina definitivamente il paziente da Airtable"""
    table = api.table(BASE_ID, "Pazienti")
    table.delete(record_id)

# --- 3. INTERFACCIA GRAFICA ---

st.set_page_config(page_title="Gestionale Fisio", page_icon="🏥", layout="wide")

st.sidebar.title("Navigazione")
menu = st.sidebar.radio(
    "Vai a:", 
    ["📊 Dashboard & Allarmi", "👥 Gestione Pazienti", "💰 Calcolo Preventivo", "📝 Scadenze Ufficio"]
)
st.sidebar.divider()
st.sidebar.info("App collegata ad Airtable.")

# =========================================================
# SEZIONE 1: DASHBOARD (CON TUTTI GLI ALERT)
# =========================================================
if menu == "📊 Dashboard & Allarmi":
    
    try:
        st.image("logo.png", width=250) 
    except FileNotFoundError:
        st.title("🏥 Dashboard Studio")

    st.write("---")

    df = get_data("Pazienti")
    
    if not df.empty:
        # --- PREPARAZIONE DATI ---
        # 1. Disdetti
        if 'Disdetto' not in df.columns: df['Disdetto'] = False
        else: df['Disdetto'] = df['Disdetto'].fillna(False)
        
        if 'Data_Disdetta' not in df.columns: df['Data_Disdetta'] = None
        df['Data_Disdetta'] = pd.to_datetime(df['Data_Disdetta'], errors='coerce').dt.date

        # 2. Visite Esterne
        if 'Visita_Esterna' not in df.columns: df['Visita_Esterna'] = False
        else: df['Visita_Esterna'] = df['Visita_Esterna'].fillna(False)
        
        if 'Data_Visita' not in df.columns: df['Data_Visita'] = None
        df['Data_Visita'] = pd.to_datetime(df['Data_Visita'], errors='coerce').dt.date

        # Calcoli base
        totali = len(df)
        df_disdetti = df[ (df['Disdetto'] == True) | (df['Disdetto'] == 1) ]
        cnt_disdetti = len(df_disdetti)
        
        # Consideriamo "Attivi" quelli non disdetti (anche se sono in visita esterna, tecnicamente sono ancora in carico)
        cnt_attivi = totali - cnt_disdetti
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Pazienti Attivi", cnt_attivi)
        k2.metric("Disdetti Totali", cnt_disdetti)

        # --- LOGICHE DI ALLARME ---
        oggi = date.today()
        
        # A. DISDETTE DA RICHIAMARE (>10 gg)
        limite_recall = oggi - timedelta(days=10)
        da_richiamare = df_disdetti[
            (df_disdetti['Data_Disdetta'].notna()) & 
            (df_disdetti['Data_Disdetta'] <= limite_recall)
        ]
        cnt_recall = len(da_richiamare)
        k3.metric("Recall Disdette", cnt_recall, delta_color="inverse")

        # B. VISITE ESTERNE
        # Filtriamo chi ha Visita Esterna = True
        df_visite = df[ (df['Visita_Esterna'] == True) | (df['Visita_Esterna'] == 1) ]
        
        # Alert 1: Visita Imminente (Oggi o Domani)
        domani = oggi + timedelta(days=1)
        visite_imminenti = df_visite[
            (df_visite['Data_Visita'].notna()) & 
            (df_visite['Data_Visita'] >= oggi) &
            (df_visite['Data_Visita'] <= domani)
        ]
        
        # Alert 2: Visita passata da > 7 giorni (da riprogrammare)
        sette_giorni_fa = oggi - timedelta(days=7)
        visite_passate = df_visite[
            (df_visite['Data_Visita'].notna()) & 
            (df_visite['Data_Visita'] <= sette_giorni_fa)
        ]

        st.divider()

        # --- VISUALIZZAZIONE ALERT ---

        # 1. ALERT VISITE ESTERNE IMMINENTI (GIALLO)
        if not visite_imminenti.empty:
            st.warning(f"👨‍⚕️ **VISITE MEDICHE IMMINENTI ({len(visite_imminenti)})** - Ricordati di sentire il dottore!")
            for i, row in visite_imminenti.iterrows():
                data_v = row['Data_Visita'].strftime('%d/%m')
                st.write(f"🔹 **{row['Nome']} {row['Cognome']}** -> Visita il **{data_v}**")

        # 2. ALERT VISITE PASSATE DA RI-PROGRAMMARE (ARANCIONE)
        if not visite_passate.empty:
            st.error(f"📅 **VISITE PASSATE DA > 1 SETTIMANA ({len(visite_passate)})** - Paziente rientrato?")
            for i, row in visite_passate.iterrows():
                rec_id = row['id']
                data_v = row['Data_Visita'].strftime('%d/%m')
                
                col_text, col_btn = st.columns([3, 1])
                with col_text:
                    st.write(f"🔸 **{row['Nome']} {row['Cognome']}** (Visita del {data_v})")
                with col_btn:
                    if st.button("✅ Rientrato", key=f"rientro_{rec_id}"):
                        # Togliamo la spunta Visita Esterna e puliamo la data
                        update_paziente_completo(rec_id, {"Visita_Esterna": False, "Data_Visita": None})
                        st.toast("Paziente riattivato!")
                        get_data.clear()
                        st.rerun()
            st.divider()

        # 3. ALERT DISDETTE (ROSSO)
        if cnt_recall > 0:
            st.error(f"📞 **RECALL DISDETTE ({cnt_recall})** - Disdetta > 10 giorni fa")
            for i, row in da_richiamare.iterrows():
                rec_id = row['id']
                nome = f"{row['Nome']} {row['Cognome']}"
                data_s = row['Data_Disdetta'].strftime('%d/%m')
                
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2,1,1])
                    c1.markdown(f"**{nome}** (dal {data_s})")
                    
                    if c2.button("✅ Recuperato", key=f"rec_{rec_id}", use_container_width=True):
                        update_paziente_completo(rec_id, {"Disdetto": False, "Data_Disdetta": None})
                        get_data.clear()
                        st.rerun()
                        
                    if c3.button("⏳ Rimanda", key=f"post_{rec_id}", use_container_width=True):
                        # Resetta la data a Oggi così sparisce dall'alert per 10 giorni
                        update_paziente_completo(rec_id, {"Disdetto": True, "Data_Disdetta": date.today()})
                        get_data.clear()
                        st.rerun()
        
        # Messaggio se è tutto pulito
        if visite_imminenti.empty and visite_passate.empty and cnt_recall == 0:
            st.success("✅ Nessun alert attivo. Tutto sotto controllo!")

        st.write("---")

        # GRAFICO (Solo pazienti attivi)
        if 'Area' in df.columns:
            st.subheader("📍 Carico di Lavoro (Attivi)")
            df_attivi = df[ (df['Disdetto'] == False) | (df['Disdetto'] == 0) ]
            
            all_areas = []
            for item in df_attivi['Area'].dropna():
                if isinstance(item, list): all_areas.extend(item)
                elif isinstance(item, str): all_areas.extend([p.strip() for p in item.split(',')])
                else: all_areas.append(str(item))
            
            if all_areas:
                counts = pd.Series(all_areas).value_counts().reset_index()
                counts.columns = ['Area', 'Pazienti']
                domain = ["Mano-Polso", "Colonna", "ATM", "Muscolo-Scheletrico", "Gruppi", "Ortopedico"]
                range_ = ["#33A1C9", "#F1C40F", "#2ECC71", "#9B59B6", "#E74C3C", "#7F8C8D"]
                
                chart = alt.Chart(counts).mark_bar().encode(
                    x=alt.X('Pazienti'), y=alt.Y('Area', sort='-x'),
                    color=alt.Color('Area', scale=alt.Scale(domain=domain, range=range_), legend=None)
                ).properties(height=350)
                st.altair_chart(chart, use_container_width=True)

    else:
        st.info("Nessun dato pazienti trovato.")

# =========================================================
# SEZIONE 2: GESTIONE PAZIENTI (COMPLETA)
# =========================================================
elif menu == "👥 Gestione Pazienti":
    st.title("📂 Anagrafica Pazienti")
    
    lista_aree = ["Mano-Polso", "Colonna", "ATM", "Muscolo-Scheletrico", "Gruppi", "Ortopedico"]
    
    # Form Inserimento
    with st.expander("➕ Nuovo Inserimento", expanded=False):
        with st.form("form_paziente", clear_on_submit=True):
            c1, c2 = st.columns(2)
            c1.text_input("Nome", key="new_name")
            c1.multiselect("Area", lista_aree, key="new_area")
            c2.text_input("Cognome", key="new_surname")
            if st.form_submit_button("Salva"):
                if st.session_state.new_name and st.session_state.new_surname:
                    area_s = ", ".join(st.session_state.new_area)
                    save_paziente(st.session_state.new_name, st.session_state.new_surname, area_s, False)
                    st.success("Salvato!")
                    st.rerun()

    st.divider()
    
    df_original = get_data("Pazienti")
    
    if not df_original.empty:
        # Preparazione colonne
        cols_bool = ['Disdetto', 'Visita_Esterna', 'Dimissione']
        cols_date = ['Data_Disdetta', 'Data_Visita']
        
        # Gestione mancanza colonne o valori nulli
        for c in cols_bool:
            if c not in df_original.columns: df_original[c] = False
            if c == 'Dimissione': df_original[c] = False 
            df_original[c] = df_original[c].fillna(False).infer_objects(copy=False)
            
        for c in cols_date:
            if c not in df_original.columns: df_original[c] = None
            df_original[c] = pd.to_datetime(df_original[c], errors='coerce').dt.date

        if 'Area' in df_original.columns:
             df_original['Area'] = df_original['Area'].apply(lambda x: x[0] if isinstance(x, list) and len(x)>0 else (str(x) if x else "")).str.strip() 
        df_original['Area'] = df_original['Area'].astype("category")

        # Search bar
        search = st.text_input("🔍 Cerca...", placeholder="Cognome...")
        if search:
            df_filt = df_original[df_original['Cognome'].astype(str).str.contains(search, case=False, na=False)]
        else:
            df_filt = df_original

        # Tabella Editor
        cols_show = ['Nome', 'Cognome', 'Area', 'Disdetto', 'Data_Disdetta', 'Visita_Esterna', 'Data_Visita', 'Dimissione', 'id']
        valid_cols = [c for c in cols_show if c in df_filt.columns]

        st.info("💡 **Disdetto**: Paziente perso. **Visita Esterna**: Alert follow-up. **Dimissione**: CANCELLA il record.")
        
        edited = st.data_editor(
            df_filt[valid_cols],
            column_config={
                "Disdetto": st.column_config.CheckboxColumn("Disdetto", width="small"),
                "Data_Disdetta": st.column_config.DateColumn("Data Disd.", format="DD/MM/YYYY", width="medium"),
                "Visita_Esterna": st.column_config.CheckboxColumn("Visita Ext.", help="Spunta se va dallo specialista", width="small"),
                "Data_Visita": st.column_config.DateColumn("Data Visita", format="DD/MM/YYYY", width="medium"),
                "Dimissione": st.column_config.CheckboxColumn("🗑️", width="small"),
                "Area": st.column_config.SelectboxColumn("Area", options=lista_aree),
                "id": None
            },
            disabled=["Nome", "Cognome"],
            hide_index=True,
            use_container_width=True,
            key="editor_main"
        )

        if st.button("💾 Salva Modifiche"):
            count_upd = 0
            count_del = 0
            
            for i, row in edited.iterrows():
                rec_id = row['id']
                
                # 1. CANCELLAZIONE
                if row.get('Dimissione') == True:
                    delete_paziente(rec_id)
                    count_del += 1
                    continue

                # 2. AGGIORNAMENTO
                # Recuperiamo la riga originale per confrontare i valori
                orig = df_original[df_original['id'] == rec_id].iloc[0]
                
                changes = {}
                
                # --- Logica Disdetto ---
                curr_dis = row['Disdetto']
                old_dis = True if orig['Disdetto'] in [True, 1, "True"] else False
                curr_date_dis = row['Data_Disdetta']
                
                # Automazione: se spuntato e data vuota -> Oggi
                if curr_dis and (pd.isna(curr_date_dis) or str(curr_date_dis) == "NaT"):
                    curr_date_dis = date.today()
                    changes['Data_Disdetta'] = curr_date_dis

                if curr_dis != old_dis: changes['Disdetto'] = curr_dis
                if str(curr_date_dis) != str(orig['Data_Disdetta']): changes['Data_Disdetta'] = curr_date_dis
                
                # --- Logica Visita Esterna ---
                curr_vis = row['Visita_Esterna']
                old_vis = True if orig['Visita_Esterna'] in [True, 1, "True"] else False
                curr_date_vis = row['Data_Visita']
                
                if curr_vis != old_vis: changes['Visita_Esterna'] = curr_vis
                if str(curr_date_vis) != str(orig['Data_Visita']): changes['Data_Visita'] = curr_date_vis
                
                # --- Logica Area ---
                if row['Area'] != orig['Area']:
                    changes['Area'] = row['Area']

                # Se ci sono modifiche, aggiorniamo
                if changes:
                    update_paziente_completo(rec_id, changes)
                    count_upd += 1

            if count_upd > 0 or count_del > 0:
                get_data.clear()
                st.success(f"Fatto! Aggiornati: {count_upd}, Eliminati: {count_del}")
                st.rerun()
            else:
                st.warning("Nessuna modifica.")

# =========================================================
# SEZIONE 3: PREVENTIVI
# =========================================================
elif menu == "💰 Calcolo Preventivo":
    st.title("Generatore Preventivi")
    df_listino = get_data("Servizi") 
    listino = {}
    
    if not df_listino.empty and 'Servizio' in df_listino.columns:
        for index, row in df_listino.iterrows():
            if row['Servizio']: listino[str(row['Servizio'])] = float(row.get('Prezzo', 0) or 0)
    
    c1, c2 = st.columns([2, 1])
    scelte = c1.multiselect("Trattamenti", sorted(list(listino.keys())))
    tot = 0
    if scelte:
        st.write("---")
        for t in scelte:
            qty = st.number_input(f"n. {t}", 1, 20, 5, key=t)
            costo = listino[t] * qty
            st.write(f"{t}: {listino[t]}€ x {qty} = **{costo}€**")
            tot += costo
        st.subheader(f"TOTALE: {tot} €")
        if tot > 300: 
            st.success(f"SCONTO PACCHETTO (10%): **{int(tot*0.9)} €**")

# =========================================================
# SEZIONE 4: SCADENZE
# =========================================================
elif menu == "📝 Scadenze Ufficio":
    st.title("Checklist Pagamenti")
    df_scad = get_data("Scadenze")
    if not df_scad.empty and 'Data_Scadenza' in df_scad.columns:
        df_scad['Data_Scadenza'] = pd.to_datetime(df_scad['Data_Scadenza'], errors='coerce')
        st.dataframe(df_scad.sort_values("Data_Scadenza").style.format({"Data_Scadenza": lambda t: t.strftime("%d/%m/%Y") if t else ""}), use_container_width=True)
    else:
        st.info("Nessuna scadenza.")
        
