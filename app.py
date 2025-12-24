import streamlit as st
from pyairtable import Api
import pandas as pd
import altair as alt
from datetime import date, datetime, timedelta
from fpdf import FPDF
import io
import os

# =========================================================
# 0. CONFIGURAZIONE & STILE (NEUTRAL BUTTONS)
# =========================================================
st.set_page_config(page_title="Gestionale Fisio Pro", page_icon="🏥", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }

    /* SFONDO */
    .stApp {
        background: radial-gradient(circle at top left, #1a202c, #0d1117);
        color: #e2e8f0;
    }

    /* SIDEBAR */
    section[data-testid="stSidebar"] {
        background-color: rgba(13, 17, 23, 0.95);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }

    /* --- KPI CARDS --- */
    .glass-kpi {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 15px;
        text-align: center;
        height: 130px;
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        margin-bottom: 8px;
    }
    .kpi-value { font-size: 30px; font-weight: 800; color: white; line-height: 1.1; }
    .kpi-label { font-size: 11px; text-transform: uppercase; color: #a0aec0; margin-top: 5px; }

    /* --- PULSANTI MODERNI (Dashboard Top) --- */
    div[data-testid="column"] .stButton > button {
        background: linear-gradient(135deg, #4299e1 0%, #3182ce 100%) !important;
        border: none !important;
        color: white !important;
        border-radius: 8px !important;
        font-size: 12px !important;
        font-weight: 600 !important;
        padding: 4px 0 !important;
        box-shadow: 0 4px 6px rgba(66, 153, 225, 0.25) !important;
        transition: transform 0.2s;
        margin-top: 0px !important;
    }
    div[data-testid="column"] .stButton > button:hover {
        transform: translateY(-2px);
    }

    /* --- STILE RIGHE COMPATTE (AVVISI) --- */
    .alert-row-name {
        background-color: rgba(255, 255, 255, 0.03);
        border-radius: 8px;
        padding: 0 15px;
        height: 42px;    
        display: flex;
        align-items: center;
        border: 1px solid rgba(255, 255, 255, 0.05);
        font-weight: 600;
        color: #fff;
        font-size: 14px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    /* Bordi colorati laterali */
    .border-orange { border-left: 4px solid #ed8936 !important; }
    .border-red { border-left: 4px solid #e53e3e !important; }
    .border-blue { border-left: 4px solid #0bc5ea !important; }

    /* --- PULSANTI "SLIM" ALLINEATI --- */
    div[data-testid="stHorizontalBlock"] button {
        padding: 2px 10px !important;
        font-size: 11px !important;
        min-height: 0px !important;
        height: 32px !important;
        line-height: 1 !important;
        border-radius: 6px !important;
        margin-top: 6px !important;
    }
    
    /* Pulsante Primario (Es. Rientrato - Blu) */
    button[kind="primary"] {
        background: linear-gradient(135deg, #3182ce, #2b6cb0) !important;
        border: none !important;
        color: white !important;
    }

    /* Pulsante Secondario (Rimandare - Neutro/Grigio) */
    button[kind="secondary"] {
        background: rgba(255, 255, 255, 0.1) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        color: #e2e8f0 !important;
        transition: all 0.2s ease !important;
    }
    button[kind="secondary"]:hover {
        background: rgba(255, 255, 255, 0.2) !important;
        border-color: #a0aec0 !important;
    }

    /* --- ALTRI --- */
    div[data-testid="stDataFrame"] { background: transparent; border: 1px solid rgba(255,255,255,0.1); border-radius: 10px; }
    input, select, textarea { background-color: rgba(13, 17, 23, 0.8) !important; border: 1px solid rgba(255, 255, 255, 0.15) !important; color: white !important; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# --- 1. CONNESSIONE ---
try:
    API_KEY = st.secrets["AIRTABLE_TOKEN"]
    BASE_ID = st.secrets["AIRTABLE_BASE_ID"]
except:
    API_KEY = "key"
    BASE_ID = "id"

api = Api(API_KEY)

# --- 2. FUNZIONI ---
@st.cache_data(ttl=60)
def get_data(table_name):
    try:
        table = api.table(BASE_ID, table_name)
        records = table.all()
        if not records: return pd.DataFrame()
        data = [{'id': r['id'], **r['fields']} for r in records]
        return pd.DataFrame(data)
    except: return pd.DataFrame()

def save_paziente(n, c, a, d):
    try: api.table(BASE_ID, "Pazienti").create({"Nome": n, "Cognome": c, "Area": a, "Disdetto": d}, typecast=True); get_data.clear(); return True
    except: return False

def update_generic(tbl, rid, data):
    try:
        cl = {k: (v.strftime('%Y-%m-%d') if hasattr(v, 'strftime') else v) for k,v in data.items()}
        api.table(BASE_ID, tbl).update(rid, cl, typecast=True); get_data.clear(); return True
    except: return False

def delete_generic(tbl, rid):
    try: api.table(BASE_ID, tbl).delete(rid); get_data.clear(); return True
    except: return False

def save_preventivo_temp(paziente, dettagli_str, totale, note):
    try: api.table(BASE_ID, "Preventivi_Salvati").create({"Paziente": paziente, "Dettagli": dettagli_str, "Totale": totale, "Note": note, "Data_Creazione": str(date.today())}, typecast=True); get_data.clear(); return True
    except: return False

def save_prodotto(prodotto, quantita):
    try: api.table(BASE_ID, "Inventario").create({"Prodotto": prodotto, "Quantita": quantita}, typecast=True); get_data.clear(); return True
    except: return False

def save_prestito(paziente, oggetto, data_prestito):
    try: api.table(BASE_ID, "Prestiti").create({"Paziente": paziente, "Oggetto": oggetto, "Data_Prestito": str(data_prestito), "Restituito": False}, typecast=True); get_data.clear(); return True
    except: return False

def create_pdf(paz, righe, tot, note=""):
    euro = chr(128)
    class PDF(FPDF):
        def header(self):
            if os.path.exists("logo.png"):
                try: self.image('logo.png', 75, 10, 60)
                except: pass
            self.set_y(35); self.set_font('Arial', 'B', 14); self.set_text_color(50)
            self.cell(0, 10, 'PREVENTIVO', 0, 1, 'C'); self.ln(10)
    pdf = PDF(); pdf.add_page(); pdf.set_text_color(0); pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, f'Paziente: {paz}', 0, 1); pdf.ln(5)
    if note: pdf.set_font('Arial', 'I', 11); pdf.multi_cell(0, 6, note.replace("€", euro).encode('latin-1','replace').decode('latin-1')); pdf.ln(5)
    pdf.set_font('Arial', 'B', 11); pdf.set_fill_color(240)
    pdf.cell(110, 10, 'Trattamento', 1, 0, 'L', 1); pdf.cell(30, 10, 'Q.ta', 1, 0, 'C', 1); pdf.cell(50, 10, 'Importo', 1, 1, 'R', 1)
    pdf.set_font('Arial', '', 11)
    for r in righe: pdf.cell(110, 10, f" {str(r['nome'])[:55]}", 1); pdf.cell(30, 10, str(r['qty']), 1, 0, 'C'); pdf.cell(50, 10, f"{r['tot']} {euro}", 1, 1, 'R')
    pdf.ln(5); pdf.set_font('Arial', 'B', 14); pdf.cell(140, 12, 'TOTALE:', 0, 0, 'R'); pdf.cell(50, 12, f'{tot} {euro}', 1, 1, 'R')
    return pdf.output(dest='S').encode('latin-1')

# --- 3. INTERFACCIA ---
with st.sidebar:
    try: st.image("logo.png", use_container_width=True)
    except: st.title("Focus Rehab")
    menu = st.radio("Menu", ["⚡ Dashboard", "👥 Pazienti", "💳 Preventivi", "📦 Magazzino", "🔄 Prestiti", "📅 Scadenze"], label_visibility="collapsed")
    st.divider(); st.caption("App v50 - Final Logic")

# =========================================================
# DASHBOARD
# =========================================================
if menu == "⚡ Dashboard":
    st.title("⚡ Dashboard")
    st.write("")

    if 'kpi_filter' not in st.session_state: st.session_state.kpi_filter = "None"

    df = get_data("Pazienti")
    
    if not df.empty:
        # Preprocessing
        for col in ['Disdetto', 'Visita_Esterna']:
            if col not in df.columns: df[col] = False
            df[col] = df[col].fillna(False)
        for col in ['Data_Disdetta', 'Data_Visita']:
            if col not in df.columns: df[col] = None
            df[col] = pd.to_datetime(df[col], errors='coerce')
        if 'Area' not in df.columns: df['Area'] = None

        totali = len(df)
        df_disdetti = df[ (df['Disdetto'] == True) | (df['Disdetto'] == 1) ]
        cnt_attivi = totali - len(df_disdetti)
        
        oggi = pd.Timestamp.now().normalize()
        limite_recall = oggi - pd.Timedelta(days=10)
        da_richiamare = df_disdetti[ (df_disdetti['Data_Disdetta'].notna()) & (df_disdetti['Data_Disdetta'] <= limite_recall) ]
        
        df_visite = df[ (df['Visita_Esterna'] == True) | (df['Visita_Esterna'] == 1) ]
        domani = oggi + pd.Timedelta(days=1)
        visite_imminenti = df_visite[ (df_visite['Data_Visita'].notna()) & (df_visite['Data_Visita'] >= oggi) & (df_visite['Data_Visita'] <= domani) ]
        
        sette_giorni_fa = oggi - pd.Timedelta(days=7)
        visite_passate = df_visite[ (df_visite['Data_Visita'].notna()) & (df_visite['Data_Visita'] <= sette_giorni_fa) ]

        # --- 1. KPI CARDS ---
        col1, col2, col3, col4 = st.columns(4)
        def draw_kpi(col, icon, num, label, color, filter_key):
            with col:
                st.markdown(f"""
                <div class="glass-kpi" style="border-bottom: 4px solid {color};">
                    <div class="kpi-icon" style="color:{color}">{icon}</div>
                    <div class="kpi-value">{num}</div>
                    <div class="kpi-label">{label}</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("Vedi Lista", key=f"btn_{filter_key}"):
                    st.session_state.kpi_filter = filter_key

        draw_kpi(col1, "👥", cnt_attivi, "Attivi", "#2ecc71", "Attivi")
        draw_kpi(col2, "📉", len(df_disdetti), "Disdetti", "#e53e3e", "Disdetti")
        draw_kpi(col3, "💡", len(da_richiamare), "Recall", "#ed8936", "Recall")
        draw_kpi(col4, "🩺", len(visite_imminenti), "Visite", "#0bc5ea", "Visite")

        st.write("")

        # --- 2. LISTA DETTAGLIO ---
        if st.session_state.kpi_filter != "None":
            st.divider()
            c_head, c_close = st.columns([9, 1])
            c_head.subheader(f"📋 Lista: {st.session_state.kpi_filter}")
            if c_close.button("❌"): st.session_state.kpi_filter = "None"; st.rerun()
            
            df_show = pd.DataFrame()
            if st.session_state.kpi_filter == "Attivi": df_show = df[ (df['Disdetto'] == False) | (df['Disdetto'] == 0) ]
            elif st.session_state.kpi_filter == "Disdetti": df_show = df_disdetti
            elif st.session_state.kpi_filter == "Recall": df_show = da_richiamare
            elif st.session_state.kpi_filter == "Visite": df_show = df_visite

            if not df_show.empty: st.dataframe(df_show[['Nome', 'Cognome', 'Area', 'Data_Disdetta', 'Data_Visita']], use_container_width=True, height=250)
            else: st.info("Nessun dato.")
            st.divider()

        st.write("")

        # --- 3. AVVISI ---
        st.subheader("🔔 Avvisi e Scadenze")
        
        # RECALL (ARANCIO)
        if not da_richiamare.empty:
            st.caption(f"📞 Recall Necessari: {len(da_richiamare)}")
            for i, row in da_richiamare.iterrows():
                c_info, c_btn1, c_btn2 = st.columns([3, 1, 1], gap="small")
                with c_info:
                    st.markdown(f"""<div class="alert-row-name border-orange">{row['Nome']} {row['Cognome']}</div>""", unsafe_allow_html=True)
                with c_btn1:
                    # FIX LOGICA: Rimuove Disdetto E svuota Data_Disdetta
                    if st.button("✅ Rientrato", key=f"rk_{row['id']}", use_container_width=True, type="primary"):
                        update_generic("Pazienti", row['id'], {"Disdetto": False, "Data_Disdetta": None}); st.rerun()
                with c_btn2:
                    # Pulsante Rimandare (Stile Neutro)
                    if st.button("📅 Rimandare", key=f"pk_{row['id']}", use_container_width=True, type="secondary"):
                        new_date = pd.Timestamp.now() + timedelta(days=7)
                        update_generic("Pazienti", row['id'], {"Data_Disdetta": new_date}); st.rerun()

        # VISITE SCADUTE (ROSSO)
        if not visite_passate.empty:
            st.caption(f"⚠️ Visite Scadute: {len(visite_passate)}")
            for i, row in visite_passate.iterrows():
                c_info, c_btn1, c_void = st.columns([3, 1, 1], gap="small")
                with c_info:
                    st.markdown(f"""<div class="alert-row-name border-red">{row['Nome']} {row['Cognome']}</div>""", unsafe_allow_html=True)
                with c_btn1:
                    if st.button("✅ Rientrato", key=f"vk_{row['id']}", use_container_width=True, type="primary"):
                        update_generic("Pazienti", row['id'], {"Visita_Esterna": False, "Data_Visita": None}); st.rerun()

        # VISITE IMMINENTI (AZZURRO)
        if not visite_imminenti.empty:
            st.caption(f"👨‍⚕️ Visite Imminenti: {len(visite_imminenti)}")
            for i, row in visite_imminenti.iterrows():
                st.markdown(f"""
                <div class="alert-row-name border-blue" style="justify-content: space-between;">
                    <span>{row['Nome']} {row['Cognome']}</span>
                    <span style="color:#0bc5ea; font-size:13px;">{row['Data_Visita'].strftime('%d/%m')}</span>
                </div>
                """, unsafe_allow_html=True)

        if da_richiamare.empty and visite_passate.empty and visite_imminenti.empty:
            st.success("Tutto tranquillo! Nessun avviso.")

        st.divider()

        # --- 4. GRAFICO ---
        st.subheader("📈 Performance Aree")
        df_attivi = df[ (df['Disdetto'] == False) | (df['Disdetto'] == 0) ]
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
            range_ = ["#4299e1", "#ed8936", "#38b2ac", "#9f7aea", "#f56565", "#a0aec0"]
            chart = alt.Chart(counts).mark_bar(cornerRadius=6, height=35).encode(
                x=alt.X('Pazienti', axis=None), 
                y=alt.Y('Area', sort='-x', title=None, axis=alt.Axis(domain=False, ticks=False, labelColor="#cbd5e0", labelFontSize=14)),
                color=alt.Color('Area', scale=alt.Scale(domain=domain, range=range_), legend=None),
                tooltip=['Area', 'Pazienti']
            ).properties(height=400).configure_view(strokeWidth=0).configure_axis(grid=False)
            st.altair_chart(chart, use_container_width=True)
        else: st.info("Dati insufficienti.")

# =========================================================
# SEZIONE 2: PAZIENTI
# =========================================================
elif menu == "👥 Pazienti":
    st.title("Anagrafica Pazienti")
    lista_aree = ["Mano-Polso", "Colonna", "ATM", "Muscolo-Scheletrico", "Gruppi", "Ortopedico"]
    
    with st.container(border=True):
        st.subheader("➕ Aggiungi Paziente")
        with st.form("form_paziente", clear_on_submit=True):
            c1, c2, c3 = st.columns([2, 2, 1])
            c1.text_input("Nome", key="new_name", placeholder="Es. Mario")
            c2.text_input("Cognome", key="new_surname", placeholder="Es. Rossi")
            c3.multiselect("Area", lista_aree, key="new_area")
            if st.form_submit_button("Salva Paziente", use_container_width=True, type="primary"):
                if st.session_state.new_name and st.session_state.new_surname:
                    area_s = ", ".join(st.session_state.new_area)
                    save_paziente(st.session_state.new_name, st.session_state.new_surname, area_s, False)
                    st.success("Paziente salvato con successo!"); st.rerun()
    
    st.write("")
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

        col_search, _ = st.columns([1, 2])
        with col_search: search = st.text_input("🔍 Cerca Paziente", placeholder="Digita il cognome...")
        df_filt = df_original[df_original['Cognome'].astype(str).str.contains(search, case=False, na=False)] if search else df_original

        cols_show = ['Nome', 'Cognome', 'Area', 'Disdetto', 'Data_Disdetta', 'Visita_Esterna', 'Data_Visita', 'Dimissione', 'id']
        valid_cols = [c for c in cols_show if c in df_filt.columns]

        edited = st.data_editor(
            df_filt[valid_cols],
            column_config={
                "Disdetto": st.column_config.CheckboxColumn("Disd.", width="small", help="Segna come disdetto"),
                "Data_Disdetta": st.column_config.DateColumn("Data Disd.", format="DD/MM/YYYY"),
                "Visita_Esterna": st.column_config.CheckboxColumn("Visita Ext.", width="small", help="Inviato a visita medica"),
                "Data_Visita": st.column_config.DateColumn("Data Visita", format="DD/MM/YYYY"),
                "Dimissione": st.column_config.CheckboxColumn("🗑️", width="small", help="Elimina definitivamente"),
                "Area": st.column_config.SelectboxColumn("Area Principale", options=lista_aree),
                "id": None
            },
            disabled=["Nome", "Cognome"], hide_index=True, use_container_width=True, key="editor_main", num_rows="fixed", height=500
        )

        if st.button("💾 Salva Modifiche Tabella", type="primary", use_container_width=True):
            count_upd = 0; count_del = 0
            for i, row in edited.iterrows():
                rec_id = row['id']
                if row.get('Dimissione') == True:
                    delete_generic("Pazienti", rec_id); count_del += 1; continue

                orig = df_original[df_original['id'] == rec_id].iloc[0]
                changes = {}
                
                if row['Disdetto'] != (orig['Disdetto'] in [True, 1]): changes['Disdetto'] = row['Disdetto']
                d_dis = row['Data_Disdetta']
                if row['Disdetto'] and (pd.isna(d_dis) or str(d_dis) == "NaT"): 
                    d_dis = pd.Timestamp.now().normalize(); changes['Data_Disdetta'] = d_dis
                elif str(d_dis) != str(orig['Data_Disdetta']): changes['Data_Disdetta'] = d_dis

                if row['Visita_Esterna'] != (orig['Visita_Esterna'] in [True, 1]): changes['Visita_Esterna'] = row['Visita_Esterna']
                if str(row['Data_Visita']) != str(orig['Data_Visita']): changes['Data_Visita'] = row['Data_Visita']
                if row['Area'] != orig['Area']: changes['Area'] = row['Area']

                if changes: update_generic("Pazienti", rec_id, changes); count_upd += 1

            if count_upd > 0 or count_del > 0:
                get_data.clear(); st.toast("Database aggiornato con successo!", icon="✅"); st.rerun()

# =========================================================
# SEZIONE 3: PREVENTIVI
# =========================================================
elif menu == "💳 Preventivi":
    st.title("Preventivi & Proposte")
    tab1, tab2 = st.tabs(["📝 Generatore", "📂 Archivio Salvati"])
    df_srv = get_data("Servizi")
    df_paz = get_data("Pazienti")
    df_std = get_data("Preventivi_Standard")

    with tab1:
        with st.expander("📋 Listino Prezzi Attuale", expanded=False):
            if not df_srv.empty and 'Area' in df_srv.columns:
                aree_uniche = df_srv['Area'].dropna().unique(); cols = st.columns(3)
                for i, area in enumerate(aree_uniche):
                    with cols[i % 3]:
                        st.markdown(f"<strong style='color:var(--neon-blue)'>📍 {area}</strong>", unsafe_allow_html=True)
                        items = df_srv[df_srv['Area'] == area]
                        for _, r in items.iterrows(): prz = f"{r['Prezzo']}€" if 'Prezzo' in r else "-"; st.caption(f"{r['Servizio']}: **{prz}**")
            else: st.warning("Configura la colonna 'Area' in Servizi.")

        with st.container(border=True):
            st.subheader("Creazione Nuovo Preventivo")
            selected_services_default = []
            default_descrizione = "" 
            
            if not df_std.empty and 'Nome' in df_std.columns:
                c_filtro, c_pack = st.columns(2)
                with c_filtro:
                    if 'Area' in df_std.columns:
                        aree_std = ["Tutte"] + sorted(list(df_std['Area'].astype(str).unique()))
                        filtro_area = st.selectbox("Filtra Area Pacchetti:", aree_std)
                        df_std_filt = df_std[df_std['Area'].astype(str) == filtro_area] if filtro_area != "Tutte" else df_std
                    else: df_std_filt = df_std
                with c_pack:
                    opt_std = ["-- Seleziona --"] + sorted(list(df_std_filt['Nome'].unique()))
                    scelta_std = st.selectbox("Carica Pacchetto Standard (Opzionale):", opt_std)
                
                if scelta_std != "-- Seleziona --":
                    row_std = df_std_filt[df_std_filt['Nome'] == scelta_std].iloc[0]
                    content = row_std.get('Contenuto', '')
                    default_descrizione = row_std.get('Descrizione', '')
                    if pd.isna(default_descrizione): default_descrizione = ""
                    
                    if content:
                        parts = [x.strip() for x in content.split(',')]
                        for p in parts:
                            if ' x' in p:
                                srv_name, srv_qty = p.split(' x')
                                selected_services_default.append(srv_name)
                                st.session_state[f"qty_preload_{srv_name}"] = int(srv_qty)
            st.divider()

            nomi_pazienti = ["Seleziona Paziente..."]
            if not df_paz.empty:
                nomi_pazienti += sorted([f"{r['Cognome']} {r['Nome']}" for i, r in df_paz.iterrows() if r.get('Cognome')])
            
            col_paz, col_serv = st.columns([1, 2])
            with col_paz: paziente_scelto = st.selectbox("Intestato a:", nomi_pazienti)
            
            listino_dict = {str(r['Servizio']): float(r.get('Prezzo', 0) or 0) for i, r in df_srv.iterrows() if r.get('Servizio')}
            valid_defaults = [s for s in selected_services_default if s in listino_dict]
            
            with col_serv:
                servizi_scelti = st.multiselect("Aggiungi Trattamenti:", sorted(list(listino_dict.keys())), default=valid_defaults)

            st.markdown("**Descrizione del Percorso / Obiettivi** (Appare nel PDF)")
            note_preventivo = st.text_area("Dettagli...", value=default_descrizione, height=100, label_visibility="collapsed")
            
            righe_preventivo = []
            totale = 0

            if servizi_scelti:
                st.divider()
                st.subheader("Dettaglio Costi")
                for s in servizi_scelti:
                    c1, c2, c3 = st.columns([3, 1, 1])
                    with c1: st.write(f"**{s}**")
                    def_qty = st.session_state.get(f"qty_preload_{s}", 1)
                    with c2: qty = st.number_input(f"Q.tà", 1, 50, def_qty, key=f"q_{s}", label_visibility="collapsed")
                    with c3: 
                        costo = listino_dict[s] * qty
                        st.markdown(f"<div style='text-align:right; font-weight:bold'>{costo} €</div>", unsafe_allow_html=True)
                    totale += costo
                    righe_preventivo.append({"nome": s, "qty": qty, "tot": costo})
                
                st.divider()
                col_tot, col_btn = st.columns([2, 1])
                with col_tot: 
                    st.markdown(f"<div style='font-size: 24px; font-weight: 800; color: var(--neon-blue);'>TOTALE: {totale} €</div>", unsafe_allow_html=True)
                with col_btn:
                    st.write("") 
                    if st.button("💾 Salva e Genera PDF", type="primary", use_container_width=True):
                        if paziente_scelto == "Seleziona Paziente...":
                            st.error("Seleziona un paziente!")
                        else:
                            dettagli_str = " | ".join([f"{r['nome']} x{r['qty']} ({r['tot']}€)" for r in righe_preventivo])
                            save_preventivo_temp(paziente_scelto, dettagli_str, totale, note_preventivo)
                            st.balloons()
                            for k in list(st.session_state.keys()):
                                if k.startswith("qty_preload_"): del st.session_state[k]
                            st.success("Preventivo salvato! Vai nella tab 'Archivio'.")

    with tab2:
        st.subheader("Archivio Preventivi")
        df_prev = get_data("Preventivi_Salvati")
        if not df_prev.empty:
            for i, row in df_prev.iterrows():
                rec_id = row['id']
                paz = row.get('Paziente', 'Sconosciuto')
                dett = str(row.get('Dettagli', '')) if not pd.isna(row.get('Dettagli')) else ""
                note_saved = str(row.get('Note', '')) if not pd.isna(row.get('Note')) else ""
                tot = row.get('Totale', 0)
                data_c = row.get('Data_Creazione', '')

                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 1, 1])
                    with c1:
                        st.markdown(f"**{paz}**"); st.caption(f"Emesso: {data_c} • Tot: **{tot} €**")
                    with c2:
                        righe_pdf = []
                        if dett:
                            items = dett.split(" | ")
                            for it in items:
                                try:
                                    parts = it.split(" x")
                                    nome = parts[0]; rest = parts[1].split(" ("); qty = rest[0]; prz = rest[1].replace("€)", "")
                                    righe_pdf.append({"nome": nome, "qty": qty, "tot": prz})
                                except: righe_pdf.append({"nome": it, "qty": "-", "tot": "-"})
                        pdf_bytes = create_pdf(paz, righe_pdf, tot, note_saved)
                        st.download_button("📄 Scarica PDF", data=pdf_bytes, file_name=f"Prev_{paz}.pdf", mime="application/pdf", key=f"pdf_{rec_id}", use_container_width=True, type="primary")
                    with c3:
                        if st.button("✅ Archivia/Elimina", key=f"conf_{rec_id}", use_container_width=True):
                            delete_generic("Preventivi_Salvati", rec_id); st.rerun()
        else: st.info("Nessun preventivo salvato.")

# =========================================================
# SEZIONE 4: MAGAZZINO
# =========================================================
elif menu == "📦 Magazzino":
    st.title("Magazzino & Materiali")
    col_add, col_tab = st.columns([1, 2], gap="large")
    with col_add:
        with st.container(border=True):
            st.subheader("Nuovo Prodotto")
            with st.form("add_prod"):
                new_prod = st.text_input("Nome Prodotto"); new_qty = st.number_input("Quantità Iniziale", 0, 1000, 1)
                if st.form_submit_button("Aggiungi al Magazzino", use_container_width=True, type="primary"): save_prodotto(new_prod, new_qty); st.rerun()
    with col_tab:
        df_inv = get_data("Inventario")
        if not df_inv.empty:
            st.subheader("Giacenze Attuali")
            if 'Prodotto' in df_inv.columns: df_inv = df_inv.sort_values('Prodotto')
            edited_inv = st.data_editor(df_inv[['Prodotto', 'Quantita', 'id']], column_config={"Prodotto": st.column_config.TextColumn("Prodotto", disabled=True), "Quantita": st.column_config.NumberColumn("Q.tà Disponibile", min_value=0, step=1), "id": None}, hide_index=True, use_container_width=True, height=400)
            if st.button("🔄 Aggiorna Giacenze", type="primary", use_container_width=True):
                cnt = 0
                for i, row in edited_inv.iterrows():
                    rec_id = row['id']; orig_qty = df_inv[df_inv['id']==rec_id].iloc[0]['Quantita']
                    if row['Quantita'] != orig_qty: update_generic("Inventario", rec_id, {"Quantita": row['Quantita']}); cnt += 1
                if cnt > 0: get_data.clear(); st.success("Stock aggiornato!"); st.rerun()
        else: st.info("Magazzino vuoto.")

# =========================================================
# SEZIONE 5: PRESTITI
# =========================================================
elif menu == "🔄 Prestiti":
    st.title("Registro Prestiti")
    df_paz = get_data("Pazienti"); df_inv = get_data("Inventario")
    with st.expander("➕ Registra Nuovo Prestito", expanded=True):
        nomi_pazienti = sorted([f"{r['Cognome']} {r['Nome']}" for i, r in df_paz.iterrows() if r.get('Cognome')]) if not df_paz.empty else []
        nomi_prodotti = sorted([r['Prodotto'] for i, r in df_inv.iterrows() if r.get('Prodotto')]) if not df_inv.empty else []
        with st.form("form_prestito"):
            c1, c2, c3 = st.columns(3); paz_scelto = c1.selectbox("Chi?", nomi_pazienti); prod_scelto = c2.selectbox("Cosa?", nomi_prodotti); data_prestito = c3.date_input("Quando?", date.today())
            if st.form_submit_button("Registra Prestito", use_container_width=True, type="primary"): save_prestito(paz_scelto, prod_scelto, data_prestito); st.success("Registrato!"); st.rerun()
    
    st.write(""); st.subheader("Materiali Attualmente Fuori")
    df_pres = get_data("Prestiti")
    if not df_pres.empty:
        if 'Restituito' not in df_pres.columns: df_pres['Restituito'] = False
        df_pres['Restituito'] = df_pres['Restituito'].fillna(False)
        if 'Data_Prestito' not in df_pres.columns: df_pres['Data_Prestito'] = None
        df_pres['Data_Prestito'] = pd.to_datetime(df_pres['Data_Prestito'], errors='coerce')
        active_loans = df_pres[df_pres['Restituito'] != True].copy()
        if not active_loans.empty:
            edited_loans = st.data_editor(active_loans[['Paziente', 'Oggetto', 'Data_Prestito', 'Restituito', 'id']], column_config={"Paziente": st.column_config.TextColumn("Paziente", disabled=True), "Oggetto": st.column_config.TextColumn("Oggetto", disabled=True), "Data_Prestito": st.column_config.DateColumn("Data", format="DD/MM/YYYY", disabled=True), "Restituito": st.column_config.CheckboxColumn("Rientrato?", help="Spunta per confermare il rientro"), "id": None}, hide_index=True, use_container_width=True)
            if st.button("💾 Conferma Restituzioni Selezionate", type="primary", use_container_width=True):
                cnt = 0
                for i, row in edited_loans.iterrows():
                    if row['Restituito'] == True: update_generic("Prestiti", row['id'], {"Restituito": True}); cnt += 1
                if cnt > 0: get_data.clear(); st.success("Aggiornato!"); st.rerun()
        else: st.success("Tutti i materiali sono in sede!")

# =========================================================
# SEZIONE 6: SCADENZE
# =========================================================
elif menu == "📅 Scadenze":
    st.title("Checklist Scadenze")
    df_scad = get_data("Scadenze")
    if not df_scad.empty and 'Data_Scadenza' in df_scad.columns:
        df_scad['Data_Scadenza'] = pd.to_datetime(df_scad['Data_Scadenza'], errors='coerce'); df_scad = df_scad.sort_values("Data_Scadenza")
        st.dataframe(df_scad, column_config={"Data_Scadenza": st.column_config.DateColumn("Scadenza", format="DD/MM/YYYY"), "Importo": st.column_config.NumberColumn("Importo", format="%d €"), "Descrizione": st.column_config.TextColumn("Dettagli")}, use_container_width=True, height=500)
    else: st.info("Nessuna scadenza prossima.")
        
