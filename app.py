import streamlit as st
from pyairtable import Api
import pandas as pd
import altair as alt
from datetime import date, datetime, timedelta
from fpdf import FPDF
import io
import os
import time

# ==============================================================================
# 1. CONFIGURAZIONE PAGINA
# ==============================================================================
st.set_page_config(
    page_title="Gestionale Fisio Pro",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# 2. CSS AVANZATO (GHOST UI TRASPARENTE + FIX ERRORI)
# ==============================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    :root {
        --glass-bg: rgba(255, 255, 255, 0.03);
        --glass-border: 1px solid rgba(255, 255, 255, 0.08);
        --neon-blue: #4299e1;
        --text-primary: #e2e8f0;
    }

    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }

    /* SFONDO GALAXY SCURO */
    .stApp {
        background: radial-gradient(circle at top left, #1a202c, #0d1117);
        color: var(--text-primary);
    }

    /* SIDEBAR */
    section[data-testid="stSidebar"] {
        background-color: rgba(13, 17, 23, 0.95);
        border-right: var(--glass-border);
        backdrop-filter: blur(12px);
    }
    
    /* TITOLI */
    h1 {
        background: linear-gradient(90deg, #FFF, #cbd5e0);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
        letter-spacing: -0.5px;
        margin-bottom: 20px;
    }
    h2, h3, h4 { color: #FFF !important; font-weight: 600; }

    /* ============================================================
       1. KPI CARDS (HTML PURO)
       ============================================================ */
    .glass-kpi {
        background: var(--glass-bg);
        border: var(--glass-border);
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 140px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        margin-bottom: 10px;
        transition: transform 0.3s ease;
        position: relative;
    }
    .glass-kpi:hover {
        transform: translateY(-2px);
        background: rgba(255,255,255,0.05);
    }
    .kpi-icon { font-size: 28px; margin-bottom: 8px; opacity: 0.9; }
    .kpi-value { font-size: 34px; font-weight: 800; color: white; line-height: 1.1; }
    .kpi-label { font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px; color: #a0aec0; margin-top: 5px; }

    /* ============================================================
       2. LINK TESTUALI TRASPARENTI (Sotto le card)
       Qui forziamo la trasparenza totale
       ============================================================ */
    div[data-testid="column"] .stButton > button {
        background-color: transparent !important;
        background: transparent !important;
        border: none !important;
        color: #718096 !important; /* Grigio scuro per default */
        font-size: 12px !important;
        font-weight: 500 !important;
        padding: 0px !important;
        width: 100% !important;
        text-align: center !important;
        margin-top: -5px !important;
        text-decoration: none !important;
        box-shadow: none !important;
    }

    /* Effetto Hover: Diventa blu e sottolineato */
    div[data-testid="column"] .stButton > button:hover {
        color: #4299e1 !important;
        text-decoration: underline !important;
        background-color: transparent !important;
        transform: none !important;
        border: none !important;
        box-shadow: none !important;
    }
    
    /* Rimozione effetto focus/active */
    div[data-testid="column"] .stButton > button:focus,
    div[data-testid="column"] .stButton > button:active {
        box-shadow: none !important;
        color: #4299e1 !important;
        background-color: transparent !important;
        border: none !important;
    }

    /* ============================================================
       3. PULSANTI AZIONE STANDARD (Salva, Fatto, Rientrato)
       ============================================================ */
    /* Questi rimangono belli e visibili */
    div[data-testid="stVerticalBlock"] .stButton > button {
        background: linear-gradient(135deg, #3182ce, #2b6cb0) !important;
        border: none !important;
        color: white !important;
        padding: 0.6rem 1.2rem !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2) !important;
        transition: all 0.2s;
    }
    div[data-testid="stVerticalBlock"] .stButton > button:hover {
        box-shadow: 0 6px 12px rgba(66, 153, 225, 0.4) !important;
        transform: scale(1.02) !important;
    }

    /* ============================================================
       ALTRI ELEMENTI
       ============================================================ */
    
    /* Tabelle Trasparenti */
    div[data-testid="stDataFrame"] {
        background-color: transparent !important;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
    }
    div[data-testid="stDataFrame"] div[data-testid="stTable"] {
        background-color: transparent !important;
    }

    /* Alert Box */
    .alert-box {
        padding: 15px; 
        border-radius: 12px; 
        margin-bottom: 12px;
        border-left: 4px solid; 
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.05);
    }
    
    /* Input Fields */
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
        border: 1px solid rgba(255,255,255,0.1);
    }
    
    /* Navigazione Radio */
    div.row-widget.stRadio > div { background-color: transparent; }
    div.row-widget.stRadio > div[role="radiogroup"] > label {
        background-color: transparent;
        padding: 10px 15px;
        margin-bottom: 5px;
        border-radius: 10px;
        color: #94a3b8;
        border: 1px solid transparent;
        transition: all 0.2s;
    }
    div.row-widget.stRadio > div[role="radiogroup"] > label:hover {
        color: #fff;
        background: rgba(255,255,255,0.03);
    }
    div.row-widget.stRadio > div[role="radiogroup"] > label[data-checked="true"] {
        background: rgba(66, 153, 225, 0.15);
        border: 1px solid var(--neon-blue);
        color: #fff;
        font-weight: 600;
    }
    div.row-widget.stRadio div[role="radiogroup"] > label > div:first-child { display: none; }

</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 3. GESTIONE CONNESSIONE E API
# ==============================================================================
try:
    API_KEY = st.secrets["AIRTABLE_TOKEN"]
    BASE_ID = st.secrets["AIRTABLE_BASE_ID"]
except Exception:
    # Gestione robusta per evitare crash se mancano le chiavi
    API_KEY = "dummy_key"
    BASE_ID = "dummy_base"

api = Api(API_KEY)

# ==============================================================================
# 4. FUNZIONI COMPLETE (CRUD & PDF)
# ==============================================================================

@st.cache_data(ttl=30)
def get_data(tbl):
    """Scarica i dati dalla tabella specificata con gestione errori."""
    try:
        table = api.table(BASE_ID, tbl)
        records = table.all()
        if not records: return pd.DataFrame()
        data = [{'id': r['id'], **r['fields']} for r in records]
        return pd.DataFrame(data)
    except Exception as e:
        return pd.DataFrame()

def save_paziente(nome, cognome, area, disdetto):
    """Salva un nuovo paziente."""
    try:
        api.table(BASE_ID, "Pazienti").create({
            "Nome": nome, 
            "Cognome": cognome, 
            "Area": area, 
            "Disdetto": disdetto,
            "Data_Inserimento": str(date.today())
        }, typecast=True)
        get_data.clear()
        return True
    except Exception as e:
        st.error(f"Errore salvataggio: {e}")
        return False

def update_generic(tbl, rid, data):
    """Aggiorna un record generico con gestione date sicura."""
    try:
        clean = {}
        for k, v in data.items():
            if "Data" in k:
                if pd.isna(v) or str(v) == "NaT" or v == "":
                    clean[k] = None
                else:
                    clean[k] = v.strftime('%Y-%m-%d') if hasattr(v, 'strftime') else str(v)
            else:
                clean[k] = v
        
        api.table(BASE_ID, tbl).update(rid, clean, typecast=True)
        get_data.clear()
        return True
    except Exception as e:
        st.error(f"Errore aggiornamento: {e}")
        return False

def create_generic(tbl, data):
    """Crea un record generico."""
    try:
        api.table(BASE_ID, tbl).create(data, typecast=True)
        get_data.clear()
        return True
    except Exception as e:
        st.error(f"Errore creazione: {e}")
        return False

def delete_generic(tbl, rid):
    """Elimina un record."""
    try:
        api.table(BASE_ID, tbl).delete(rid)
        get_data.clear()
        return True
    except Exception as e:
        st.error(f"Errore eliminazione: {e}")
        return False

# --- FUNZIONI SPECIFICHE ---
def save_preventivo_temp(paziente, dettagli_str, totale, note):
    return create_generic("Preventivi_Salvati", {
        "Paziente": paziente, "Dettagli": dettagli_str, "Totale": totale, 
        "Note": note, "Data_Creazione": str(date.today())
    })

def save_prodotto(prodotto, quantita):
    return create_generic("Inventario", {"Prodotto": prodotto, "Quantita": quantita})

def save_prestito(paziente, oggetto, data_prestito):
    return create_generic("Prestiti", {
        "Paziente": paziente, "Oggetto": oggetto, 
        "Data_Prestito": str(data_prestito), "Restituito": False
    })

# --- GENERAZIONE PDF AVANZATA ---
def create_pdf(paz, righe, tot, note=""):
    euro = chr(128)
    
    class PDF(FPDF):
        def header(self):
            if os.path.exists("logo.png"):
                try: self.image('logo.png', 75, 10, 60)
                except: pass
            self.set_y(35); self.set_font('Arial', 'B', 14); self.set_text_color(50)
            self.cell(0, 10, 'PREVENTIVO PERCORSO RIABILITATIVO', 0, 1, 'C')
            self.line(20, self.get_y(), 190, self.get_y()); self.ln(10)
            
        def footer(self):
            self.set_y(-15); self.set_font('Arial', 'I', 8); self.set_text_color(128)
            self.cell(0, 10, f'Pagina {self.page_no()} - Studio Focus', 0, 0, 'C')

    pdf = PDF()
    pdf.add_page(); pdf.set_text_color(0)
    
    # Info Paziente
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, f'Paziente: {paz}', 0, 1)
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 8, f'Data: {date.today().strftime("%d/%m/%Y")}', 0, 1); pdf.ln(5)
    
    # Note
    if note:
        pdf.set_font('Arial', 'I', 11); pdf.set_text_color(80)
        clean_note = note.replace("€", euro).encode('latin-1','replace').decode('latin-1')
        pdf.multi_cell(0, 6, clean_note); pdf.ln(8)
        
    # Tabella
    pdf.set_font('Arial', 'B', 11); pdf.set_fill_color(240); pdf.set_text_color(0)
    pdf.cell(110, 10, ' Trattamento', 1, 0, 'L', 1)
    pdf.cell(30, 10, 'Q.ta', 1, 0, 'C', 1)
    pdf.cell(50, 10, 'Importo ', 1, 1, 'R', 1)
    
    pdf.set_font('Arial', '', 11)
    for r in righe:
        nome = str(r['nome'])[:55]
        qty = str(r['qty'])
        tot_r = f"{r['tot']} {euro}"
        pdf.cell(110, 10, f" {nome}", 1)
        pdf.cell(30, 10, qty, 1, 0, 'C')
        pdf.cell(50, 10, tot_r, 1, 1, 'R')
        
    pdf.ln(5); pdf.set_font('Arial', 'B', 14)
    pdf.cell(140, 12, 'TOTALE:', 0, 0, 'R')
    pdf.cell(50, 12, f'{tot} {euro}', 1, 1, 'R')
    
    return pdf.output(dest='S').encode('latin-1')

# ==============================================================================
# 5. LAYOUT E SIDEBAR
# ==============================================================================
with st.sidebar:
    try: st.image("logo.png", use_container_width=True)
    except: st.title("Focus Rehab")
    
    st.write("")
    menu = st.radio(
        "NAVIGAZIONE", 
        ["⚡ Dashboard", "👥 Pazienti", "💳 Preventivi", "📦 Magazzino", "🔄 Prestiti", "📅 Scadenze"],
        label_visibility="collapsed"
    )
    st.divider(); st.caption("System v3.8 - Stable")

# ==============================================================================
# SEZIONE 1: DASHBOARD
# ==============================================================================
if menu == "⚡ Dashboard":
    st.title("⚡ Dashboard")
    st.write("")
    
    if 'dash_filter' not in st.session_state: st.session_state.dash_filter = None
    
    df = get_data("Pazienti")
    if not df.empty:
        # Preprocessing Robusto
        for c in ['Disdetto','Visita_Esterna']: 
            if c not in df.columns: df[c] = False
            df[c] = df[c].fillna(False)
        for c in ['Data_Disdetta','Data_Visita']: 
            if c not in df.columns: df[c] = None
            df[c] = pd.to_datetime(df[c], errors='coerce')
        if 'Area' not in df.columns: df['Area'] = "Non specificato"

        # Logica KPI
        tot = len(df)
        disdetti = df[(df['Disdetto']==True)]
        attivi = tot - len(disdetti)
        
        # Logica Date (CORRETTA - SENZA WALRUS OPERATOR :=)
        oggi = pd.Timestamp.now().normalize()
        limit_recall = today = pd.Timestamp.now().normalize() - pd.Timedelta(days=10)
        
        recall = disdetti[(disdetti['Data_Disdetta'].notna()) & (disdetti['Data_Disdetta'] <= limit_recall)]
        
        visite = df[(df['Visita_Esterna']==True)]
        # Qui c'era l'errore, ora è corretto:
        vis_imm = visite[(visite['Data_Visita'] >= today)]
        vis_scad = visite[(visite['Data_Visita'] < today)]

        # --- 1. KPI CARDS (HTML) + LINK TRASPARENTI ---
        c1, c2, c3, c4 = st.columns(4)
        
        def draw_kpi(col, icon, num, label, color, key):
            with col:
                st.markdown(f"""
                <div class="glass-kpi" style="border-bottom: 4px solid {color};">
                    <div class="kpi-icon" style="color:{color}">{icon}</div>
                    <div class="kpi-value">{num}</div>
                    <div class="kpi-label">{label}</div>
                </div>
                """, unsafe_allow_html=True)
                # Link testuale sottile (diventerà trasparente grazie al CSS)
                if st.button("› vedi dettagli", key=f"btn_{key}"):
                    st.session_state.dash_filter = key

        draw_kpi(c1, "👥", attivi, "ATTIVI", "#4299e1", "Attivi")
        draw_kpi(c2, "📉", len(disdetti), "DISDETTI", "#e53e3e", "Disdetti")
        draw_kpi(c3, "💡", len(recall), "RECALL", "#ed8936", "Recall")
        draw_kpi(c4, "🩺", len(vis_imm), "VISITE", "#38b2ac", "Visite")

        st.write("")

        # --- 2. LISTA COMPARSA ---
        if st.session_state.dash_filter:
            with st.container(border=True):
                cl, cr = st.columns([9,1])
                cl.subheader(f"📋 Dettaglio: {st.session_state.dash_filter}")
                if cr.button("❌ Chiudi"): st.session_state.dash_filter = None; st.rerun()
                
                d_show = pd.DataFrame()
                if st.session_state.dash_filter == "Attivi":
                    d_show = df[(df['Disdetto']==False)]
                elif st.session_state.dash_filter == "Disdetti":
                    d_show = disdetti
                elif st.session_state.dash_filter == "Recall":
                    d_show = recall
                elif st.session_state.dash_filter == "Visite":
                    d_show = visite
                
                if not d_show.empty: 
                    st.dataframe(d_show[['Nome','Cognome','Area','Data_Disdetta','Data_Visita']], use_container_width=True, height=250)
                else: st.info("Nessun dato.")
            st.divider()

        # --- 3. AVVISI & GRAFICI ---
        col_L, col_R = st.columns([1, 1.5], gap="large")
        
        with col_L:
            st.subheader("🔔 Avvisi")
            
            if not vis_scad.empty:
                st.markdown(f"<div class='alert-box' style='border-color:#e53e3e; color:#e53e3e'><strong>⚠️ Visite Scadute ({len(vis_scad)})</strong></div>", unsafe_allow_html=True)
                for i, r in vis_scad.iterrows():
                    with st.container(border=True):
                        cn, cb = st.columns([2, 1])
                        cn.write(f"**{r['Nome']} {r['Cognome']}**")
                        if cb.button("Rientrato", key=f"v_{r['id']}"):
                            update_generic("Pazienti", r['id'], {"Visita_Esterna": False, "Data_Visita": None}); st.rerun()

            if len(recall) > 0:
                st.markdown(f"<div class='alert-box' style='border-color:#ed8936; color:#ed8936'><strong>📞 Recall Necessari ({len(recall)})</strong></div>", unsafe_allow_html=True)
                for i, r in recall.iterrows():
                    with st.container(border=True):
                        cn, cb = st.columns([2, 1])
                        cn.write(f"**{r['Nome']} {r['Cognome']}**")
                        if cb.button("Fatto", key=f"r_{r['id']}"):
                            update_generic("Pazienti", r['id'], {"Disdetto": False}); st.rerun()

            if not vis_imm.empty:
                st.markdown(f"<div class='alert-box' style='border-color:#38b2ac; color:#38b2ac'><strong>👨‍⚕️ Visite Imminenti ({len(vis_imm)})</strong></div>", unsafe_allow_html=True)
                for i, r in vis_imm.iterrows(): st.caption(f"• {r['Nome']} {r['Cognome']} ({r['Data_Visita'].strftime('%d/%m')})")

            if vis_scad.empty and len(recall) == 0 and vis_imm.empty: 
                st.success("✅ Tutto regolare.")

        with col_R:
            st.subheader("📈 Aree")
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
            else:
                st.info("Nessun dato area disponibile.")

# ==============================================================================
# SEZIONE 2: PAZIENTI
# ==============================================================================
elif menu == "👥 Pazienti":
    st.title("Anagrafica Pazienti")
    
    with st.expander("➕ Nuovo Paziente"):
        with st.form("new_p"):
            c1,c2,c3 = st.columns(3)
            n=c1.text_input("Nome"); s=c2.text_input("Cognome")
            a=c3.multiselect("Area", ["Mano-Polso", "Colonna", "ATM", "Muscolo-Scheletrico", "Gruppi", "Ortopedico"])
            if st.form_submit_button("Salva"): 
                save_paziente(n, s, ",".join(a), False); st.success("Salvato!"); st.rerun()
    
    df = get_data("Pazienti")
    if not df.empty:
        df['Disdetto'] = df['Disdetto'].fillna(False); df['Visita_Esterna'] = df['Visita_Esterna'].fillna(False)
        df['Data_Disdetta'] = pd.to_datetime(df['Data_Disdetta'], errors='coerce')
        df['Data_Visita'] = pd.to_datetime(df['Data_Visita'], errors='coerce')
        
        search = st.text_input("🔍 Cerca...", placeholder="Cognome...")
        df_filt = df[df['Cognome'].astype(str).str.contains(search, case=False, na=False)] if search else df
        
        ed = st.data_editor(
            df_filt[['Nome','Cognome','Area','Disdetto','Data_Disdetta','Visita_Esterna','Data_Visita','id']],
            key="paz_editor", hide_index=True, use_container_width=True,
            column_config={
                "Disdetto": st.column_config.CheckboxColumn("Disd.", width="small"),
                "Visita_Esterna": st.column_config.CheckboxColumn("Visita", width="small"),
                "Data_Disdetta": st.column_config.DateColumn("Data Disd."),
                "Data_Visita": st.column_config.DateColumn("Data Visita"),
                "Area": st.column_config.SelectboxColumn("Area", options=["Mano-Polso", "Colonna", "ATM", "Muscolo-Scheletrico", "Gruppi", "Ortopedico"]),
                "id": None
            }
        )
        
        if st.button("💾 Salva Modifiche", type="primary"):
            for i, r in ed.iterrows():
                orig = df[df['id']==r['id']].iloc[0]
                chg = {}
                if r['Disdetto'] != orig['Disdetto']: 
                    chg['Disdetto'] = r['Disdetto']
                    if r['Disdetto'] and pd.isna(r['Data_Disdetta']): chg['Data_Disdetta'] = pd.Timestamp.now()
                if str(r['Data_Disdetta']) != str(orig['Data_Disdetta']): chg['Data_Disdetta'] = r['Data_Disdetta']
                if str(r['Data_Visita']) != str(orig['Data_Visita']): chg['Data_Visita'] = r['Data_Visita']
                if r['Visita_Esterna'] != orig['Visita_Esterna']: chg['Visita_Esterna'] = r['Visita_Esterna']
                if r['Area'] != orig['Area']: chg['Area'] = r['Area']
                
                if chg: update_generic("Pazienti", r['id'], chg)
            st.success("Aggiornato!"); st.rerun()

# ==============================================================================
# SEZIONE 3: PREVENTIVI
# ==============================================================================
elif menu == "💳 Preventivi":
    st.title("Preventivi")
    t1, t2 = st.tabs(["📝 Crea", "📂 Archivio"])
    paz = get_data("Pazienti"); srv = get_data("Servizi")
    
    with t1:
        c1,c2 = st.columns(2)
        p_sel = c1.selectbox("Paziente", sorted([f"{r['Cognome']} {r['Nome']}" for i,r in paz.iterrows()])) if not paz.empty else None
        
        listino = {}
        if not srv.empty:
            listino = {str(r['Servizio']): float(r.get('Prezzo', 0) or 0) for i,r in srv.iterrows()}
            
        s_sel = c2.multiselect("Servizi", sorted(list(listino.keys())))
        note = st.text_area("Note")
        
        if s_sel:
            st.divider(); tot = 0; righe = []
            for s in s_sel:
                c_a, c_b, c_c = st.columns([3,1,1])
                c_a.write(f"**{s}**")
                q = c_b.number_input("Q.tà", 1, 50, 1, key=f"q_{s}")
                cost = listino[s] * q; c_c.write(f"**{cost} €**"); tot += cost
                righe.append({"nome":s, "qty":q, "tot":cost})
            
            st.divider(); st.metric("TOTALE", f"{tot} €")
            if st.button("💾 Salva PDF", type="primary"):
                det = " | ".join([f"{r['nome']} x{r['qty']}" for r in righe])
                save_preventivo_temp(p_sel, det, tot, note); st.success("Salvato!")

    with t2:
        prv = get_data("Preventivi_Salvati")
        if not prv.empty:
            for i,r in prv.iterrows():
                with st.container(border=True):
                    c1,c2,c3 = st.columns([3,1,1])
                    c1.write(f"**{r['Paziente']}**"); c1.caption(f"{r['Data_Creazione']} - {r['Totale']}€")
                    
                    righe_pdf = []
                    if not pd.isna(r['Dettagli']):
                        for item in r['Dettagli'].split(" | "):
                            parts = item.split(" x")
                            if len(parts) >= 2: righe_pdf.append({"nome":parts[0], "qty":parts[1], "tot":"-"})
                    
                    pdf = create_pdf(r['Paziente'], righe_pdf, r['Totale'], str(r.get('Note','')))
                    c2.download_button("📄 PDF", pdf, f"P_{r['id']}.pdf", use_container_width=True)
                    if c3.button("🗑️", key=f"del_{r['id']}"): delete_generic("Preventivi_Salvati", r['id']); st.rerun()

# ==============================================================================
# SEZIONE 4: MAGAZZINO
# ==============================================================================
elif menu == "📦 Magazzino":
    st.title("Magazzino")
    c1,c2 = st.columns(2)
    with c1: 
        with st.form("np"):
            n=st.text_input("Prod"); q=st.number_input("Qta",1); 
            if st.form_submit_button("Add"): save_prodotto(n, q); st.rerun()
    with c2:
        df = get_data("Inventario")
        if not df.empty:
            ed = st.data_editor(df[['Prodotto','Quantita','id']], hide_index=True)
            if st.button("Aggiorna"):
                for i,r in ed.iterrows(): update_generic("Inventario", r['id'], {"Quantita": r['Quantita']})
                st.rerun()

# ==============================================================================
# SEZIONE 5: PRESTITI
# ==============================================================================
elif menu == "🔄 Prestiti":
    st.title("Prestiti")
    with st.expander("➕ Nuovo"):
        p = st.selectbox("Chi", get_data("Pazienti")['Cognome'].tolist() if not get_data("Pazienti").empty else [])
        o = st.text_input("Cosa")
        if st.button("Presta"): save_prestito(p, o, date.today()); st.rerun()
    df = get_data("Prestiti")
    if not df.empty:
        df['Restituito'] = df['Restituito'].fillna(False)
        ed = st.data_editor(df[['Paziente','Oggetto','Restituito','id']], hide_index=True)
        if st.button("Salva Resi"):
            for i,r in ed.iterrows(): 
                if r['Restituito']: update_generic("Prestiti", r['id'], {"Restituito": True})
            st.rerun()

# ==============================================================================
# SEZIONE 6: SCADENZE
# ==============================================================================
elif menu == "📅 Scadenze":
    st.title("Scadenze")
    df = get_data("Scadenze")
    if not df.empty: 
        df['Data_Scadenza'] = pd.to_datetime(df['Data_Scadenza'])
        df = df.sort_values('Data_Scadenza')
        st.dataframe(df, use_container_width=True)
        
