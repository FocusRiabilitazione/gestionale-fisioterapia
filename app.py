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
    get_data.clear()
    table.create(record, typecast=True)

def update_generic(table_name, record_id, dati_aggiornati):
    """Funzione universale per aggiornare qualsiasi tabella."""
    table = api.table(BASE_ID, table_name)
    fields_to_send = {}
    for k, v in dati_aggiornati.items():
        if "Data" in k: 
            if pd.isna(v) or str(v) == "NaT" or v == "":
                fields_to_send[k] = None
            else:
                if hasattr(v, 'strftime'):
                    fields_to_send[k] = v.strftime('%Y-%m-%d')
                else:
                    fields_to_send[k] = str(v)
        else:
            fields_to_send[k] = v
    table.update(record_id, fields_to_send, typecast=True)

def delete_generic(table_name, record_id):
    """Elimina un record da una tabella qualsiasi"""
    table = api.table(BASE_ID, table_name)
    table.delete(record_id)

def save_prestito(paziente, oggetto, data_prestito):
    """Registra un nuovo prestito"""
    table = api.table(BASE_ID, "Prestiti")
    data_str = data_prestito.strftime('%Y-%m-%d') if hasattr(data_prestito, 'strftime') else str(data_prestito)
    record = {
        "Paziente": paziente,
        "Oggetto": oggetto,
        "Data_Prestito": data_str,
        "Restituito": False
    }
    get_data.clear()
    table.create(record, typecast=True)

def save_prodotto(prodotto, quantita):
    """Aggiunge un prodotto all'inventario"""
    table = api.table(BASE_ID, "Inventario")
    record = {"Prodotto": prodotto, "Quantita": quantita}
    get_data.clear()
    table.create(record, typecast=True)

# --- 3. INTERFACCIA GRAFICA ---

st.set_page_config(page_title="Gestionale Fisio", page_icon="logo.png", layout="wide")

st.sidebar.title("Navigazione")
menu = st.sidebar.radio(
    "Vai a:", 
    ["📊 Dashboard & Allarmi", "👥 Gestione Pazienti", "💰 Calcolo Preventivo", "📦 Inventario Materiali", "🤝 Materiali Prestati", "📝 Scadenze Ufficio"]
)
st.sidebar.divider()
st.sidebar.info("App collegata ad Airtable.")

# =========================================================
# SEZIONE 1: DASHBOARD
# =========================================================
if menu == "📊 Dashboard & Allarmi":
    
    try:
        st.image("logo.png", width=250) 
    except FileNotFoundError:
        st.title("🏥 Dashboard Studio")

    st.write("---")

    df = get_data("Pazienti")
    
    if not df.empty:
        # --- PULIZIA DATI ---
        # Garantiamo che le colonne esistano sempre
        for col in ['Disdetto', 'Visita_Esterna']:
            if col not in df.columns: df[col] = False
            df[col] = df[col].fillna(False)

        for col in ['Data_Disdetta', 'Data_Visita']:
            if col not in df.columns: df[col] = None
            df[col] = pd.to_datetime(df[col], errors='coerce')
            
        if 'Area' not in df.columns: df['Area'] = None

        # --- CALCOLI KPI ---
        totali = len(df)
        df_disdetti = df[ (df['Disdetto'] == True) | (df['Disdetto'] == 1) ]
        cnt_attivi = totali - len(df_disdetti)
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Pazienti Attivi", cnt_attivi)
        k2.metric("Disdetti Totali", len(df_disdetti))

        # --- ALERT LOGIC ---
        oggi = pd.Timestamp.now().normalize()
        
        # 1. Recall Disdette
        limite_recall = oggi - pd.Timedelta(days=10)
        da_richiamare = df_disdetti[ (df_disdetti['Data_Disdetta'].notna()) & (df_disdetti['Data_Disdetta'] <= limite_recall) ]
        cnt_recall = len(da_richiamare)
        k3.metric("Recall Disdette", cnt_recall, delta_color="inverse")

        # 2. Visite
        df_visite = df[ (df['Visita_Esterna'] == True) | (df['Visita_Esterna'] == 1) ]
        domani = oggi + pd.Timedelta(days=1)
        visite_imminenti = df_visite[ (df_visite['Data_Visita'].notna()) & (df_visite['Data_Visita'] >= oggi) & (df_visite['Data_Visita'] <= domani) ]
        
        sette_giorni_fa = oggi - pd.Timedelta(days=7)
        visite_passate = df_visite[ (df_visite['Data_Visita'].notna()) & (df_visite['Data_Visita'] <= sette_giorni_fa) ]

        # 3. Prestiti
        df_prestiti = get_data("Prestiti")
        prestiti_scaduti = pd.DataFrame()
        if not df_prestiti.empty and 'Data_Prestito' in df_prestiti.columns:
            df_prestiti['Data_Prestito'] = pd.to_datetime(df_prestiti['Data_Prestito'], errors='coerce')
            limite_prestiti = oggi - pd.Timedelta(days=30)
            if 'Restituito' not in df_prestiti.columns: df_prestiti['Restituito'] = False
            prestiti_scaduti = df_prestiti[ (df_prestiti['Restituito'] != True) & (df_prestiti['Data_Prestito'] <= limite_prestiti) ]

        st.divider()

        # --- VISUALIZZAZIONE ALERT ---
        alert_shown = False
        
        if not visite_imminenti.empty:
            st.warning(f"👨‍⚕️ **VISITE MEDICHE IMMINENTI ({len(visite_imminenti)})**")
            for i, row in visite_imminenti.iterrows():
                d_vis = row['Data_Visita'].strftime('%d/%m')
                st.write(f"🔹 **{row['Nome']} {row['Cognome']}** -> {d_vis}")
            alert_shown = True

        if not visite_passate.empty:
            st.error(f"📅 **VISITE PASSATE DA > 1 SETTIMANA**")
            for i, row in visite_passate.iterrows():
                rec_id = row['id']
                d_vis = row['Data_Visita'].strftime('%d/%m')
                c_txt, c_btn = st.columns([3, 1])
                c_txt.write(f"🔸 **{row['Nome']} {row['Cognome']}** (Visita: {d_vis})")
                if c_btn.button("✅ Rientrato", key=f"rientro_{rec_id}"):
                    update_generic("Pazienti", rec_id, {"Visita_Esterna": False, "Data_Visita": None})
                    get_data.clear()
                    st.rerun()
            alert_shown = True

        if cnt_recall > 0:
            st.error(f"📞 **RECALL DISDETTE ({cnt_recall})**")
            for i, row in da_richiamare.iterrows():
                rec_id = row['id']
                nome = f"{row['Nome']} {row['Cognome']}"
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2,1,1])
                    c1.markdown(f"**{nome}**")
                    if c2.button("✅ Recuperato", key=f"rec_{rec_id}"):
                        update_generic("Pazienti", rec_id, {"Disdetto": False, "Data_Disdetta": None})
                        get_data.clear()
                        st.rerun()
                    if c3.button("⏳ Rimanda", key=f"post_{rec_id}"):
                        update_generic("Pazienti", rec_id, {"Disdetto": True, "Data_Disdetta": date.today()})
                        get_data.clear()
                        st.rerun()
            alert_shown = True
        
        if not prestiti_scaduti.empty:
            st.warning(f"📦 **MATERIALI NON RESTITUITI DA > 30GG ({len(prestiti_scaduti)})**")
            for i, row in prestiti_scaduti.iterrows():
                d_pres = row['Data_Prestito'].strftime('%d/%m')
                st.write(f"🔹 **{row.get('Paziente','?')}** ha ancora: **{row.get('Oggetto','?')}** (dal {d_pres})")
            alert_shown = True

        if not alert_shown:
            st.success("✅ Nessun alert attivo.")

        st.write("---")

        # --- GRAFICO (FIXED) ---
        st.subheader("📍 Carico di Lavoro (Attivi)")
        
        # Filtriamo solo gli attivi
        df_attivi = df[ (df['Disdetto'] == False) | (df['Disdetto'] == 0) ]
        
        # Raccogliamo le aree
        all_areas = []
        if 'Area' in df_attivi.columns:
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
                x=alt.X('Pazienti', title="Pazienti"), 
                y=alt.Y('Area', sort='-x'),
                color=alt.Color('Area', scale=alt.Scale(domain=domain, range=range_), legend=None)
            ).properties(height=350)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("ℹ️ Il grafico apparirà quando avrai inserito le 'Aree' per i pazienti attivi.")

    else:
        st.info("Nessun dato pazienti trovato.")

# =========================================================
# SEZIONE 2: GESTIONE PAZIENTI
# =========================================================
elif menu == "👥 Gestione Pazienti":
    st.title("📂 Anagrafica Pazienti")
    lista_aree = ["Mano-Polso", "Colonna", "ATM", "Muscolo-Scheletrico", "Gruppi", "Ortopedico"]
    
    with st.expander("➕ Nuovo Inserimento"):
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
        for c in ['Disdetto', 'Visita_Esterna', 'Dimissione']:
            if c not in df_original.columns: df_original[c] = False
            df_original[c] = df_original[c].fillna(False).infer_objects(copy=False)
        for c in ['Data_Disdetta', 'Data_Visita']:
            if c not in df_original.columns: df_original[c] = None
            df_original[c] = pd.to_datetime(df_original[c], errors='coerce')
        if 'Area' in df_original.columns:
             df_original['Area'] = df_original['Area'].apply(lambda x: x[0] if isinstance(x, list) and len(x)>0 else (str(x) if x else "")).str.strip() 
        df_original['Area'] = df_original['Area'].astype("category")

        search = st.text_input("🔍 Cerca...", placeholder="Cognome...")
        df_filt = df_original[df_original['Cognome'].astype(str).str.contains(search, case=False, na=False)] if search else df_original

        cols_show = ['Nome', 'Cognome', 'Area', 'Disdetto', 'Data_Disdetta', 'Visita_Esterna', 'Data_Visita', 'Dimissione', 'id']
        valid_cols = [c for c in cols_show if c in df_filt.columns]

        edited = st.data_editor(
            df_filt[valid_cols],
            column_config={
                "Disdetto": st.column_config.CheckboxColumn("Disdetto", width="small"),
                "Data_Disdetta": st.column_config.DateColumn("Data Disd.", format="DD/MM/YYYY"),
                "Visita_Esterna": st.column_config.CheckboxColumn("Visita Ext.", width="small"),
                "Data_Visita": st.column_config.DateColumn("Data Visita", format="DD/MM/YYYY"),
                "Dimissione": st.column_config.CheckboxColumn("🗑️"),
                "Area": st.column_config.SelectboxColumn("Area", options=lista_aree),
                "id": None
            },
            disabled=["Nome", "Cognome"], hide_index=True, use_container_width=True, key="editor_main"
        )

        if st.button("💾 Salva Modifiche"):
            count_upd = 0
            count_del = 0
            for i, row in edited.iterrows():
                rec_id = row['id']
                if row.get('Dimissione') == True:
                    delete_generic("Pazienti", rec_id)
                    count_del += 1
                    continue

                orig = df_original[df_original['id'] == rec_id].iloc[0]
                changes = {}
                
                if row['Disdetto'] != (orig['Disdetto'] in [True, 1]): changes['Disdetto'] = row['Disdetto']
                d_dis = row['Data_Disdetta']
                if row['Disdetto'] and (pd.isna(d_dis) or str(d_dis) == "NaT"): 
                    d_dis = pd.Timestamp.now().normalize()
                    changes['Data_Disdetta'] = d_dis
                elif str(d_dis) != str(orig['Data_Disdetta']):
                    changes['Data_Disdetta'] = d_dis

                if row['Visita_Esterna'] != (orig['Visita_Esterna'] in [True, 1]): changes['Visita_Esterna'] = row['Visita_Esterna']
                if str(row['Data_Visita']) != str(orig['Data_Visita']): changes['Data_Visita'] = row['Data_Visita']
                if row['Area'] != orig['Area']: changes['Area'] = row['Area']

                if changes:
                    update_generic("Pazienti", rec_id, changes)
                    count_upd += 1

            if count_upd > 0 or count_del > 0:
                get_data.clear()
                st.success("Aggiornato!")
                st.rerun()

# =========================================================
# SEZIONE 3: PREVENTIVI
# =========================================================
elif menu == "💰 Calcolo Preventivo":
    st.title("Generatore Preventivi")
    df_srv = get_data("Servizi") 
    listino = {str(r['Servizio']): float(r.get('Prezzo', 0) or 0) for i, r in df_srv.iterrows() if r.get('Servizio')} if not df_srv.empty else {}
    
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

# =========================================================
# SEZIONE 4: INVENTARIO
# =========================================================
elif menu == "📦 Inventario Materiali":
    st.title("📦 Magazzino e Inventario")
    c1, c2 = st.columns([2, 1])
    with c1: st.info("Gestisci qui le quantità dei materiali.")
    with c2:
        with st.expander("➕ Aggiungi"):
            with st.form("add_prod"):
                new_prod = st.text_input("Nome")
                new_qty = st.number_input("Q.tà", 0, 1000, 1)
                if st.form_submit_button("Salva"):
                    save_prodotto(new_prod, new_qty)
                    st.success("Fatto!")
                    st.rerun()

    df_inv = get_data("Inventario")
    if not df_inv.empty:
        if 'Prodotto' in df_inv.columns: df_inv = df_inv.sort_values('Prodotto')
        edited_inv = st.data_editor(
            df_inv[['Prodotto', 'Quantita', 'id']],
            column_config={
                "Prodotto": st.column_config.TextColumn("Prodotto", disabled=True),
                "Quantita": st.column_config.NumberColumn("Quantità", min_value=0, step=1),
                "id": None
            },
            hide_index=True, use_container_width=True
        )
        if st.button("💾 Aggiorna Quantità"):
            cnt = 0
            for i, row in edited_inv.iterrows():
                rec_id = row['id']
                orig_qty = df_inv[df_inv['id']==rec_id].iloc[0]['Quantita']
                if row['Quantita'] != orig_qty:
                    update_generic("Inventario", rec_id, {"Quantita": row['Quantita']})
                    cnt += 1
            if cnt > 0:
                get_data.clear()
                st.success("Aggiornato!")
                st.rerun()
    else: st.info("Inventario vuoto.")

# =========================================================
# SEZIONE 5: PRESTITI
# =========================================================
elif menu == "🤝 Materiali Prestati":
    st.title("🤝 Registro Prestiti")
    st.subheader("Nuovo Prestito")
    df_paz = get_data("Pazienti")
    df_inv = get_data("Inventario")
    nomi_pazienti = sorted([f"{r['Cognome']} {r['Nome']}" for i, r in df_paz.iterrows() if r.get('Cognome')]) if not df_paz.empty else []
    nomi_prodotti = sorted([r['Prodotto'] for i, r in df_inv.iterrows() if r.get('Prodotto')]) if not df_inv.empty else []

    with st.form("form_prestito"):
        c1, c2, c3 = st.columns(3)
        paz_scelto = c1.selectbox("Paziente", nomi_pazienti if nomi_pazienti else ["Nessun Paziente"])
        prod_scelto = c2.selectbox("Oggetto", nomi_prodotti if nomi_prodotti else ["Nessun Prodotto"])
        data_prestito = c3.date_input("Data Prestito", date.today())
        if st.form_submit_button("Registra"):
            if paz_scelto and prod_scelto:
                save_prestito(paz_scelto, prod_scelto, data_prestito)
                st.success("Segnato!")
                st.rerun()
            else: st.error("Mancano dati.")

    st.divider()
    st.subheader("In Prestito (Non Restituiti)")
    df_pres = get_data("Prestiti")
    if not df_pres.empty:
        if 'Restituito' not in df_pres.columns: df_pres['Restituito'] = False
        df_pres['Restituito'] = df_pres['Restituito'].fillna(False)
        if 'Data_Prestito' not in df_pres.columns: df_pres['Data_Prestito'] = None
        df_pres['Data_Prestito'] = pd.to_datetime(df_pres['Data_Prestito'], errors='coerce')
        
        active_loans = df_pres[df_pres['Restituito'] != True].copy()
        if not active_loans.empty:
            edited_loans = st.data_editor(
                active_loans[['Paziente', 'Oggetto', 'Data_Prestito', 'Restituito', 'id']],
                column_config={
                    "Paziente": st.column_config.TextColumn("Paziente", disabled=True),
                    "Oggetto": st.column_config.TextColumn("Oggetto", disabled=True),
                    "Data_Prestito": st.column_config.DateColumn("Data", format="DD/MM/YYYY", disabled=True), 
                    "Restituito": st.column_config.CheckboxColumn("✅ Restituito?"),
                    "id": None
                },
                hide_index=True, use_container_width=True
            )
            if st.button("💾 Conferma Restituzioni"):
                cnt = 0
                for i, row in edited_loans.iterrows():
                    if row['Restituito'] == True: 
                        update_generic("Prestiti", row['id'], {"Restituito": True})
                        cnt += 1
                if cnt > 0:
                    get_data.clear()
                    st.success("Restituiti!")
                    st.rerun()
        else: st.info("Nessun materiale fuori.")
    else: st.info("Nessun storico.")

# =========================================================
# SEZIONE 6: SCADENZE
# =========================================================
elif menu == "📝 Scadenze Ufficio":
    st.title("Checklist Pagamenti")
    df_scad = get_data("Scadenze")
    if not df_scad.empty and 'Data_Scadenza' in df_scad.columns:
        df_scad['Data_Scadenza'] = pd.to_datetime(df_scad['Data_Scadenza'], errors='coerce')
        st.dataframe(df_scad.sort_values("Data_Scadenza").style.format({"Data_Scadenza": lambda t: t.strftime("%d/%m/%Y") if t else ""}), use_container_width=True)
    else:
        st.info("Nessuna scadenza.")
        
