import streamlit as st
from openai import OpenAI
import json, os, pandas as pd, base64, io
from datetime import datetime, timedelta

# ==========================================
# 1. API AYARLARI
# ==========================================
# Bulut ortamında anahtarları güvenli kasadan çekiyoruz
openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

openrouter_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=st.secrets["OPENROUTER_API_KEY"],
)

st.set_page_config(page_title="VC Planner Pro v20.1", layout="wide", page_icon="🏥")

# --- VERİ YÖNETİMİ ---
FILE_PATH = "staff_data_v20.json"
def save_data(data):
    with open(FILE_PATH, "w") as f: json.dump(data, f)
def load_data():
    if os.path.exists(FILE_PATH):
        try:
            with open(FILE_PATH, "r") as f: return json.load(f)
        except: return []
    return []

if 'staff_list' not in st.session_state: st.session_state.staff_list = load_data()
if 'edit_index' not in st.session_state: st.session_state.edit_index = None
if 'weekly_notes' not in st.session_state: st.session_state.weekly_notes = ""

# --- VISION ---
def encode_image(image_file):
    return base64.b64encode(image_file.read()).decode('utf-8')

# --- DIALOG BOX (HAFTALIK NOTLAR) ---
@st.dialog("📝 Veckovisa justeringar ")
def weekly_notes_dialog():
    st.write("Skriv in specifika ändringar för denna planeringsperiod:")
    notes = st.text_area("Ex: Karin är sjuk på måndag, Erik vabbar på onsdag...", value=st.session_state.weekly_notes)
    if st.button("Spara ändringar"):
        st.session_state.weekly_notes = notes
        st.rerun()

# --- HEADER ---
st.markdown("<h1 style='color: #0077b6;'>🏥 Lyckeby Vårdcentral Schema Planerare <small style='color: grey; font-size: 15px;'>v20.1 Powered by Agentic AI</small></h1>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["👥 Team & Foto", "⚙️ Planeringsperiod", "🚀 Generera Schema"])

# --- TAB 1: TEAM & FOTO ---
with tab1:
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("📸 Läs in från foto")
        uploaded_file = st.file_uploader("Ladda upp personallista", type=["jpg", "png", "jpeg"])
        if uploaded_file and st.button("Analysera Bild"):
            base64_img = encode_image(uploaded_file)
            with st.spinner("AI läser bilden..."):
                v_res = openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": [{"type": "text", "text": "Hitta läkare och grad. JSON: [{'namn': '...', 'oran': 100, 'noter': '', 'hyr': false}]"},
                                                           {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}]}]
                )
                st.session_state.staff_list.extend(json.loads(v_res.choices[0].message.content.replace('```json', '').replace('```', '')))
                save_data(st.session_state.staff_list); st.rerun()

        st.divider()
        st.subheader("➕ Hantera Personal")
        idx = st.session_state.edit_index
        with st.form("staff_form"):
            namn = st.text_input("Namn", value=st.session_state.staff_list[idx]['namn'] if idx is not None else "")
            oran = st.slider("Grad (%)", 10, 100, st.session_state.staff_list[idx]['oran'] if idx is not None else 100)
            noter = st.text_area("Fasta noter (t.ex. ledig v.28)", value=st.session_state.staff_list[idx]['noter'] if idx is not None else "")
            hyr = st.checkbox("Hyr-läkare", value=st.session_state.staff_list[idx]['hyr'] if idx is not None else False)
            if st.form_submit_button("Spara"):
                entry = {"namn": namn, "oran": oran, "noter": noter, "hyr": hyr}
                if idx is not None: st.session_state.staff_list[idx] = entry
                else: st.session_state.staff_list.append(entry)
                st.session_state.edit_index = None; save_data(st.session_state.staff_list); st.rerun()

    with c2:
        st.subheader("Aktuellt Team")
        for i, p in enumerate(st.session_state.staff_list):
            ca, cb, cc = st.columns([3, 1, 1])
            ca.write(f"**{p['namn']}** ({p['oran']}%) {'[HYR]' if p['hyr'] else ''}")
            if cb.button("Redigera", key=f"ed_{i}"): st.session_state.edit_index = i; st.rerun()
            if cc.button("Radera", key=f"de_{i}"):
                st.session_state.staff_list.pop(i); save_data(st.session_state.staff_list); st.rerun()

# --- TAB 2: PLANERİNGSPERİOD ---
with tab2:
    st.subheader("📅 Tidsram")
    col_a, col_b = st.columns(2)
    with col_a:
        raw_date = st.date_input("Välj startdatum", value=datetime.now())
        start_monday = raw_date - timedelta(days=raw_date.weekday())
        v_start = start_monday.isocalendar()[1]
    with col_b:
        duration = st.select_slider("Antal veckor", options=[1, 2, 3, 4, 5, 6])
        end_date = start_monday + timedelta(weeks=duration-1)
        v_end = end_date.isocalendar()[1]
    
    st.info(f"Planerar perioden: **v.{v_start} - v.{v_end}** ({duration} veckor)")

# --- TAB 3: GENERERA ---
with tab3:
    if st.button("📝 Lägg till veckans specifika ändringar"):
        weekly_notes_dialog()
    
    if st.session_state.weekly_notes:
        st.warning(f"**Aktiva justeringar:** {st.session_state.weekly_notes}")
        if st.button("Rensa noteringar"): st.session_state.weekly_notes = ""; st.rerun()

    if st.button("🚀 Generera Agentic Matris", type="primary"):
        with st.spinner("AI-agenterna (DeepSeek + Claude Opus) arbetar..."):
            # AGENT 1: PLANNER (DEEPSEEK)
            p_prompt = f"""Skapa matris-schema för v.{v_start}-v.{v_end}.
            PERSONAL: {st.session_state.staff_list}
            VECKANS JUSTERINGAR: {st.session_state.weekly_notes}
            HUVUDREGLER FÖR PLANERINGEN:
            1 Varje dag mellan kl. 10:00-12:00 SKA exakt en läkare tilldelas ÖLI-mottagning. Denna läkare får INTE vara 'disponibel' FM eller EM i samma dag.
            2 Varje dag SKA exakt två OLIKA läkare tilldelas som Disponibel: en på FM (kl. 08:30-12:30) och en på EM (kl. 12:30-17:00)
            3 Torsdag FM: Hyrläkare SKA vara dispo. 
            4 FM-disponibel SKA få ENDAST Telefon eller Recept EM. 
            5 EM-disponibel SKA få ENDAST Telefon eller Recept FM.
            6.Disponibel SKA ansvara för studentstöd
            7. BVC-PLANERING: Om det anges i veckans ändringar att det är BVC, ska en av de läkare som är markerade som 'BVC-läkare' tilldelas detta på onsdagar och torsdagar. 
               BVC innebär att läkaren är helt låst för barnavård och har inga akuta tider eller mottagning på vårdcentralen under den tiden.
            8. RONDTID (11:30-12:00): Varje dag kl. 11:30-12:00 SKA alla läkare tilldelas 'Rondtid'. 
               UNDANTAG: De läkare som är 'Disponibla', har 'BVC' eller har 'ÖLI-mottagning' under denna tid ska INTE ha rondtid. Alla andra MÅSTE ha detta inplanerat."""
            
            p_res = openrouter_client.chat.completions.create(
                model="deepseek/deepseek-chat",
                messages=[{"role": "user", "content": p_prompt}]
            )
            draft = p_res.choices[0].message.content

            # AGENT 2: AUDITOR (CLAUDE OPUS)
        with st.spinner("Ajan 2: Claude Opus kalite kontrolü yapıyor..."):
            # Önce denetleme talimatını hazırlıyoruz
            auditor_rules = f"""
            Du är en strikt chefsrevisor. Granska och korrigera schemat för v.{v_start}-{v_end} utifrån dessa kontrollpunkter:

            1. ÖLI-KONTROLL: Finns det exakt en ÖLI-läkare kl. 10:00-12:00 varje dag? Denna person får INTE ha något dispo-pass under hela den dagen.
            2. DISPO-DUBBLERING: Kontrollera att det är två HELT OLIKA läkare disponibla varje dag (FM 08:30-12:30 och EM 12:30-17:00).
            3. TORSDAGS-CHECK: Hyrläkaren MÅSTE vara 'Disponibel + Studentstöd' på torsdag FM.
            4. FM-DISPO BEGRÄNSNING: De som är FM-disponibla får ENDAST ha Telefon eller Recept på eftermiddagen. Inga patienter.
            5. EM-DISPO BEGRÄNSNING: De som är EM-disponibla får ENDAST ha Telefon eller Recept på förmiddagen. Inga patienter.
            6. STUDENTSTÖD: Alla disponibla pass ska vara märkta som 'Disponibel + Studentstöd'.
            7. VECKANS ÄNDRINGAR: Se till att dessa är följda: {st.session_state.weekly_notes}
            8. BVC-CHECK: Om BVC är aktiverat i veckans ändringar, kontrollera att en behörig BVC-läkare har tilldelats passet och att de inte har fått några andra patienter samtidigt.
            9. ROND-KONTROLL: Kontrollera att alla läkare har 'Rondtid' kl. 11:30-12:00 varje dag. 
               Säkerställ att de enda som saknar rondtid är de som är markerade som 'Disponibel', 'BVC' eller 'ÖLI-mottagning'. 
               Ingen annan får ha patienter eller admin under denna halvtimme.

            Om du hittar fel, korrigera dem i slutgiltiga matrisen.
            SCHEMA SOM SKA GRANSKAS: 
            {draft}
            """

            # Şimdi API'yi çağırıyoruz
            a_res = openrouter_client.chat.completions.create(
                model="anthropic/claude-3-opus",
                messages=[{"role": "user", "content": auditor_rules}]
            )
            
            # Sonucu ekrana basıyoruz
            final_schedule = a_res.choices[0].message.content
            st.markdown(final_schedule)
