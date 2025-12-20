import streamlit as st
from pyairtable import Api
import pandas as pd
import altair as alt
from datetime import date, timedelta
from fpdf import FPDF
import io
import os

# =========================================================
# 0. CONFIGURAZIONE & CSS (Versione 22 - Complete Restore)
# =========================================================
st.set_page_config(page_title="Gestionale Fisio Pro", page_icon="🏥", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }

    /* SFONDO SCURO PULITO */
    .stApp {
        background-color: #0e1117;
        color: #e2e8f0;
    }

    /* SIDEBAR */
    section[data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }

    /* ============================================================
       1. KPI CARDS (I 4 PULSANTONI IN ALTO)
       ============================================================ */
    div[data-testid="column"] button {
        background-color: #1f2937 !important;
        border: 1px solid #374151 !important;
        border-radius: 12px !important;
        padding: 20px 10px !important;
        height: 130px !important;
        width: 100% !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
        transition: all 0.2s !important;
    }

    div[data-testid="column"] button:hover {
        transform: translateY(-3px) !important;
        border-color: #60a5fa !important;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3) !important;
    }

    /* Testo Grande dentro le Card */
    div[data-testid="column"] button p {
        font-size: 26px !important;
        font-weight: 700 !important;
        color: #f3f4f6 !important;
        margin-bottom: 5px !important;
        line-height: 1.2 !important;
    }

    /* ============================================================
       2. PULSANTI AZIONE (PICCOLI NEGLI ALERT)
       ============================================================ */
    div[data-testid="stVerticalBlock"] div[data-testid="column"] button {
        height: auto !important;
        background-color: #2563eb !important;
        border: none !important;
        padding: 0.4rem 1rem !important;
        font-size: 14px !important;
    }
    
    div[data-testid="stVerticalBlock"] div[data-testid="column"] button p {
        font-size: 14px !important;
        font-weight: 600 !important;
        color: white !important;
    }

    /* ============================================================
       ALTRI ELEMENTI
       ============================================================ */
    
    /* Tabelle Trasparenti */
    div[data-testid="stDataFrame"] {
        background-color: transparent !important;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
    }
    div[data-testid="stDataFrame"] div[data-testid="stTable"] {
        background-color: transparent !important;
    }

    /* Navigazione */
    div.row-widget.stRadio > div[role="radiogroup"] > label {
        background-color: transparent;
        border: 1px solid transparent;
        padding: 10px;
        border-radius: 8px;
        color: #9ca3af;
        transition: all 0.2s;
    }
    div.row-widget.stRadio > div[role="radiogroup"] > label:hover {
        background-color: rgba(255,255,255,0.05);
        color: white;
    }
    div.row-widget.stRadio > div[role="radiogroup"] > label[data-checked="true"] {
        background-color: rgba(37, 99, 235, 0.2);
        border: 1px solid #2563eb;
        color: white;
        font-weight: 600;
    }

    /* Alert Boxes */
    .alert-container {
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 15px;
        border-left: 5px solid;
        background-color: rgba(255,255,255,0.03);
    }
    .alert-title { font-weight: bold; font-size: 16px; margin-bottom: 10px; display: block; }
    
    /* Input */
    input, select, textarea {
        background-color: rgba(13, 17, 23, 0.8) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        color: white !important;
        border-radius: 8px;
    }
    .streamlit-expanderHeader {
        background-color: rgba(255,255,255,0.02);
        border-radius: 8px;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# --- CONFIGURAZIONE CONNESSIONE ---
try:
    API_KEY = st.secrets["AIRTABLE_TOKEN"]
    BASE_ID = st.secrets["AIRTABLE_BASE_ID"]
except FileNotFoundError:
    API_KEY = "tua_chiave"
    BASE_ID = "tuo_base_id"

api = Api(API_KEY)

# --- FUNZIONI ---
@st.cache_data(ttl=60)
def get_data(table_name):
    try:
        table = api.table(BASE_ID, table_name)
        records = table.all()
        if not records: return pd.DataFrame()
        data = [{'id': r['id'], **r['fields']} for r in records]
        return pd.DataFrame(data)
    except Exception: return pd.DataFrame()

def save_paziente(nome, cognome, area, disdetto):
    table = api.table(BASE_ID, "Pazienti")
    table.create({"Nome": nome, "Cognome": cognome, "Area": area, "Disdetto": disdetto}, typecast=True)
    get_data.clear()

def update_generic(table_name, record_id, changes):
    table = api.table(BASE_ID, table_name)
    clean = {}
    for k, v in changes.items():
        if "Data" in k: 
            if pd.isna(v) or str(v)=="NaT": clean[k] = None
            else: clean[k] = v.strftime('%Y-%m-%d')
        else: clean[k] = v
    table.update(record_id, clean, typecast=True)
    get_data.clear()

def delete_generic(table_name, record_id):
    api.table(BASE_ID, table_name).delete(record_id)
    get_data.clear()

def save_prestito(paziente, oggetto, data_prestito):
    d_str = data_prestito.strftime('%Y-%m-%d')
    api.table(BASE_ID, "Prestiti").create({"Paziente": paziente, "Oggetto": oggetto, "Data_Prestito": d_str, "Restituito": False}, typecast=True)
    get_data.clear()

def save_prodotto(prodotto, quantita):
    api.table(BASE_ID, "Inventario").create({"Prodotto": prodotto, "Quantita": quantita}, typecast=True)
    get_data.clear()

def save_preventivo_temp(paziente, dettagli_str, totale, note):
    table = api.table(BASE_ID, "Preventivi_Salvati")
    record = {
        "Paziente": paziente, "Dettagli": dettagli_str, "Totale": totale, 
        "Note": note, "Data_Creazione": str(date.today())
    }
    get_data.clear()
    table.create(record, typecast=True)

def create_pdf(paziente, righe, tot, note=""):
    euro = chr(128)
    class PDF(FPDF):
        def header(self):
            if os.path.exists("logo.png"):
                try: self.image('logo.png', 75, 10, 60)
                except: pass
            self.set_y(35); self.set_font('Arial', 'B', 12); self.set_text_color(80)
            self.cell(0, 10, 'PREVENTIVO PERCORSO RIABILITATIVO', 0, 1, 'C')
            self.line(20, self.get_y(), 190, self.get_y()); self.ln(8)
    
    pdf = PDF(); pdf.add_page(); pdf.set_text_color(0); pdf.set_font('Arial', 'B', 12)
    pdf.cell(95, 8, f'Paziente: {paziente}', 0, 0, 'L')
    pdf.set_font('Arial', '', 12)
    pdf.cell(95, 8, f'Data: {date.today().strftime("%d/%m/%Y")}', 0, 1, 'R'); pdf.ln(8)
    
    if note:
        pdf.set_font('Arial', 'I', 11); pdf.multi_cell(0, 6, note.replace("€", euro).encode('latin-1','replace').decode('latin-1')); pdf.ln(10)
    
    pdf.set_font('Arial', 'B', 11); pdf.set_fill_color(50, 50, 50); pdf.set_text_color(255)
    pdf.cell(110, 10, ' Trattamento', 0, 0, 'L', 1); pdf.cell(30, 10, 'Q.ta', 0, 0, 'C', 1); pdf.cell(50, 10, 'Importo ', 0, 1, 'R', 1)
    
    pdf.set_text_color(0); pdf.set_font('Arial', '', 11)
    for r in righe:
        pdf.cell(110, 10, str(r['nome'])[:55], 'B'); pdf.cell(30, 10, str(r['qty']), 'B', 0, 'C'); pdf.cell(50, 10, f"{r['tot']} {euro} ", 'B', 1, 'R')
    pdf.ln(5); pdf.set_font('Arial', 'B', 14)
    pdf.cell(140, 12, 'TOTALE:', 0, 0, 'R'); pdf.cell(50, 12, f'{totale} {euro}', 1, 1, 'R')
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFACCIA ---
with st.sidebar:
    try: st.image("logo.png", use_container_width=True)
    except: st.title("Focus Rehab")
    menu = st.radio("Menu", ["⚡ Dashboard", "👥 Pazienti", "💳 Preventivi", "📦 Magazzino", "🔄 Prestiti", "📅 Scadenze"], label_visibility="collapsed")
    st.divider(); st.caption("Version 22 - Complete")

# =========================================================
# SEZIONE 1: DASHBOARD
# =========================================================
if menu == "⚡ Dashboard":
    st.title("⚡ Dashboard")
    if 'dash_filter' not in st.session_state: st.session_state.dash_filter = None
    
    df = get_data("Pazienti")
    if not df.empty:
        for c in ['Disdetto','Visita_Esterna']: df[c] = df[c].fillna(False)
        for c in ['Data_Disdetta','Data_Visita']: df[c] = pd.to_datetime(df[c], errors='coerce')
        if 'Area' not in df.columns: df['Area'] = None

        tot = len(df); dis = df[(df['Disdetto']==True)]; att = tot - len(dis)
        oggi = pd.Timestamp.now().normalize()
        rec = dis[(dis['Data_Disdetta'].notna()) & (dis['Data_Disdetta'] <= (oggi - pd.Timedelta(days=10)))]
        vis = df[(df['Visita_Esterna']==True)]
        vis_imm = vis[(vis['Data_Visita'] >= today := pd.Timestamp.now().normalize())]
        vis_scad = vis[(vis['Data_Visita'] < today)]

        # 1. KPI CARDS
        c1, c2, c3, c4 = st.columns(4)
        def kpi(i, n, t): return f"{i} {n}\n\n{t}"
        
        with c1: 
            if st.button(kpi("👥", att, "ATTIVI"), key="k1"): st.session_state.dash_filter = "Attivi"
        with c2: 
            if st.button(kpi("📉", len(dis), "DISDETTI"), key="k2"): st.session_state.dash_filter = "Disdetti"
        with c3: 
            if st.button(kpi("📞", len(rec), "RECALL"), key="k3"): st.session_state.dash_filter = "Recall"
        with c4: 
            if st.button(kpi("🩺", len(vis_imm), "VISITE"), key="k4"): st.session_state.dash_filter = "Visite"

        st.write("")

        # 2. LISTA COMPARSA
        if st.session_state.dash_filter:
            with st.container(border=True):
                cl, cr = st.columns([9,1])
                cl.subheader(f"📋 {st.session_state.dash_filter}")
                if cr.button("❌"): st.session_state.dash_filter = None; st.rerun()
                
                d_s = df[(df['Disdetto']==False)] if st.session_state.dash_filter == "Attivi" else (dis if st.session_state.dash_filter == "Disdetti" else (rec if st.session_state.dash_filter == "Recall" else vis_imm))
                if not d_s.empty: st.dataframe(d_s[['Nome','Cognome','Area','Data_Disdetta','Data_Visita']], use_container_width=True, height=250)
                else: st.info("Nessun dato.")
            st.divider()

        # 3. AVVISI & GRAFICO
        col_L, col_R = st.columns([1, 1.5], gap="large")
        
        with col_L:
            st.subheader("🔔 Avvisi Operativi")
            
            # Visite Scadute
            if not vis_scad.empty:
                st.markdown(f"""<div class="alert-container" style="border-color:#ef4444"><span class="alert-title" style="color:#ef4444">⚠️ Visite Scadute ({len(vis_scad)})</span></div>""", unsafe_allow_html=True)
                for i, r in vis_scad.iterrows():
                    with st.container(border=True):
                        cn, cb = st.columns([2, 1])
                        cn.write(f"**{r['Nome']} {r['Cognome']}**")
                        if cb.button("Rientrato", key=f"v_{r['id']}"):
                            update_generic("Pazienti", r['id'], {"Visita_Esterna": False, "Data_Visita": None}); st.rerun()

            # Recall
            if len(rec) > 0:
                st.markdown(f"""<div class="alert-container" style="border-color:#f97316"><span class="alert-title" style="color:#f97316">📞 Recall Necessari ({len(rec)})</span></div>""", unsafe_allow_html=True)
                for i, r in rec.iterrows():
                    with st.container(border=True):
                        cn, cb = st.columns([2, 1])
                        cn.write(f"**{r['Nome']} {r['Cognome']}**")
                        if cb.button("Fatto", key=f"r_{r['id']}"):
                            update_generic("Pazienti", r['id'], {"Disdetto": False}); st.rerun()

            # Visite Imminenti
            if not vis_imm.empty:
                st.markdown(f"""<div class="alert-container" style="border-color:#3b82f6"><span class="alert-title" style="color:#3b82f6">👨‍⚕️ Visite Imminenti</span></div>""", unsafe_allow_html=True)
                for i, r in vis_imm.iterrows(): st.caption(f"• {r['Nome']} {r['Cognome']} ({r['Data_Visita'].strftime('%d/%m')})")

            if vis_scad.empty and len(rec) == 0 and vis_imm.empty: st.success("✅ Tutto regolare.")

        with col_R:
            st.subheader("📈 Performance Aree")
            active = df[(df['Disdetto']==False)]
            areas = []
            if 'Area' in active.columns:
                for a in active['Area'].dropna():
                    if isinstance(a, list): areas.extend(a)
                    else: areas.extend([x.strip() for x in str(a).split(',')])
            if areas:
                cnt = pd.Series(areas).value_counts().reset_index(); cnt.columns = ['Area', 'Pazienti']
                dom = ["Mano-Polso", "Colonna", "ATM", "Muscolo-Scheletrico", "Gruppi", "Ortopedico"]
                rng = ["#33A1C9", "#F1C40F", "#2ECC71", "#9B59B6", "#E74C3C", "#7F8C8D"]
                ch = alt.Chart(cnt).mark_bar(cornerRadius=5).encode(
                    x=alt.X('Pazienti', axis=None), y=alt.Y('Area', sort='-x', title=None),
                    color=alt.Color('Area', scale=alt.Scale(domain=dom, range=rng), legend=None), tooltip=['Area', 'Pazienti']
                ).properties(height=350).configure_view(strokeWidth=0).configure_axis(grid=False)
                st.altair_chart(ch, use_container_width=True)

# =========================================================
# SEZIONE 2: PAZIENTI
# =========================================================
elif menu == "👥 Pazienti":
    st.title("Anagrafica Pazienti")
    with st.expander("➕ Aggiungi Paziente"):
        c1,c2,c3 = st.columns(3); n=c1.text_input("Nome"); s=c2.text_input("Cognome"); a=c3.multiselect("Area", ["Mano-Polso", "Colonna", "ATM", "Muscolo-Scheletrico", "Gruppi", "Ortopedico"])
        if st.button("Salva", use_container_width=True): save_paziente(n, s, ",".join(a), False); st.success("Salvato!"); st.rerun()
    
    df = get_data("Pazienti")
    if not df.empty:
        df['Disdetto'] = df['Disdetto'].fillna(False)
        ed = st.data_editor(df[['Nome','Cognome','Area','Disdetto','Data_Disdetta','Visita_Esterna','Data_Visita','id']], key="p_ed", hide_index=True, use_container_width=True,
            column_config={"Disdetto": st.column_config.CheckboxColumn("Disd.", width="small"), "Visita_Esterna": st.column_config.CheckboxColumn("Visita", width="small")})
        if st.button("💾 Salva Modifiche", use_container_width=True):
            for i, r in ed.iterrows():
                orig = df[df['id']==r['id']].iloc[0]
                chg = {}
                if r['Disdetto'] != orig['Disdetto']: chg['Disdetto'] = r['Disdetto']; chg['Data_Disdetta'] = pd.Timestamp.now() if r['Disdetto'] else None
                if str(r['Data_Visita']) != str(orig['Data_Visita']): chg['Data_Visita'] = r['Data_Visita']
                if r['Visita_Esterna'] != orig['Visita_Esterna']: chg['Visita_Esterna'] = r['Visita_Esterna']
                if chg: update_generic("Pazienti", r['id'], chg)
            st.success("Aggiornato!"); st.rerun()

# =========================================================
# SEZIONE 3: PREVENTIVI
# =========================================================
elif menu == "💳 Preventivi":
    st.title("Preventivi")
    t1, t2 = st.tabs(["📝 Generatore", "📂 Archivio"])
    df_s = get_data("Servizi"); df_p = get_data("Pazienti")
    
    with t1:
        c_p, c_s = st.columns([1, 2])
        paz_s = c_p.selectbox("Paziente", sorted([f"{r['Cognome']} {r['Nome']}" for i,r in df_p.iterrows()])) if not df_p.empty else None
        listino = {str(r['Servizio']): float(r.get('Prezzo', 0) or 0) for i,r in df_s.iterrows()}
        serv_s = c_s.multiselect("Servizi", sorted(list(listino.keys())))
        note = st.text_area("Note")
        if serv_s:
            st.divider(); tot = 0; righe = []
            for s in serv_s:
                c1, c2, c3 = st.columns([3,1,1]); c1.write(f"**{s}**")
                q = c2.number_input("Q.tà", 1, 50, 1, key=f"q_{s}"); cost = listino[s] * q
                c3.write(f"**{cost} €**"); tot += cost; righe.append({"nome":s, "qty":q, "tot":cost})
            st.divider(); st.metric("TOTALE", f"{tot} €")
            if st.button("💾 Salva PDF", use_container_width=True):
                det = " | ".join([f"{r['nome']} x{r['qty']}" for r in righe])
                save_preventivo_temp(paz_s, det, tot, note); st.success("Salvato!")

    with t2:
        df_pr = get_data("Preventivi_Salvati")
        if not df_pr.empty:
            for i, r in df_pr.iterrows():
                with st.container(border=True):
                    c1, c2, c3 = st.columns([3,1,1]); c1.write(f"**{r['Paziente']}**"); c1.caption(f"{r['Data_Creazione']} - {r['Totale']}€")
                    righe_pdf = []
                    if not pd.isna(r['Dettagli']):
                        for item in r['Dettagli'].split(" | "):
                            parts = item.split(" x")
                            if len(parts)==2: righe_pdf.append({"nome":parts[0], "qty":parts[1], "tot":"-"})
                    c2.download_button("📄 PDF", create_pdf(r['Paziente'], righe_pdf, r['Totale'], str(r.get('Note',''))), f"P_{r['id']}.pdf", use_container_width=True)
                    if c3.button("🗑️", key=f"d_{r['id']}", use_container_width=True): delete_generic("Preventivi_Salvati", r['id']); st.rerun()

# =========================================================
# SEZIONE 4: MAGAZZINO
# =========================================================
elif menu == "📦 Magazzino":
    st.title("Magazzino")
    c1,c2 = st.columns(2)
    with c1: 
        with st.form("np"):
            n=st.text_input("Prod"); q=st.number_input("Qta",1); 
            if st.form_submit_button("Add"): save_prodotto(n,q); st.rerun()
    with c2:
        df = get_data("Inventario")
        if not df.empty:
            ed = st.data_editor(df[['Prodotto','Quantita','id']], hide_index=True, use_container_width=True)
            if st.button("Aggiorna"):
                for i,r in ed.iterrows(): update_generic("Inventario", r['id'], {"Quantita": r['Quantita']})
                st.rerun()

# =========================================================
# SEZIONE 5: PRESTITI
# =========================================================
elif menu == "🔄 Prestiti":
    st.title("Prestiti")
    with st.expander("Nuovo"):
        p = st.selectbox("Chi", get_data("Pazienti")['Cognome'].tolist()); o = st.text_input("Cosa")
        if st.button("Presta"): save_prestito(p, o, date.today()); st.rerun()
    df = get_data("Prestiti")
    if not df.empty:
        df['Restituito'] = df['Restituito'].fillna(False)
        ed = st.data_editor(df[['Paziente','Oggetto','Restituito','id']], hide_index=True, use_container_width=True)
        if st.button("Salva Resi"):
            for i,r in ed.iterrows(): 
                if r['Restituito']: update_generic("Prestiti", r['id'], {"Restituito": True})
            st.rerun()

# =========================================================
# SEZIONE 6: SCADENZE
# =========================================================
elif menu == "📅 Scadenze":
    st.title("Scadenze")
    df = get_data("Scadenze")
    if not df.empty: st.dataframe(df, use_container_width=True)
