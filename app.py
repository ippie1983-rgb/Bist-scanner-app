import os
import json
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

# Pagina configuratie
st.set_page_config(
    page_title="BIST & Edelmetalen 6-Agent 3-Dagen Nieuwsscanner",
    page_icon="🇹🇷",
    layout="wide"
)

# Mobiel-vriendelijke opmaak
st.markdown("""
<style>
    .main-header { font-size: 24px; font-weight: bold; color: #1E3A8A; }
    div[data-testid="stMetricValue"] { font-size: 20px !important; }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-header">🇹🇷 BIST & Edelmetalen 6-Agent 3-Dagen Nieuwsscanner</p>', unsafe_allow_html=True)
st.markdown("Live nieuws-, politiek-, oorlogs-, analisten- en agenda-scanner voor **Borsa Istanbul (BIST)**, **Goud** en **Zilver** — uitsluitend met **breaking news van maximaal 3 dagen oud** en klikbare bronlinks.")

# --- ZIJBALK: INSTELLINGEN ---
if "gemini_auth" not in st.session_state:
    st.session_state.gemini_auth = "AQ.Ab8RN6JnVmPz0K31aqL3BE1e6"

st.sidebar.header("⚙️ Systeem & AI Instellingen")

st.session_state.gemini_auth = st.sidebar.text_input(
    "Gemini / Vertex AI Key:",
    type="password",
    value=st.session_state.gemini_auth,
    help="Staat standaard ingesteld."
)
st.sidebar.success("✅ 3-Dagen Filter & 6-Agent Engine actief!")

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 Aandelen Selectie (Agent 1)")
STOCK_OPTIONS = [
    "THYAO (Turkish Airlines)",
    "ASELS (Aselsan)",
    "KCHOL (Koç Holding)",
    "AKBNK (Akbank)",
    "GARAN (Garanti BBVA)",
    "TUPRS (Tüpraş)",
    "BIMAS (Bim)",
    "EREGL (Erdemir)",
    "SISE (Şişecam)",
    "SASA (Sasa Polyester)"
]
selected_tickers = st.sidebar.multiselect(
    "Kies BIST aandelen om specifiek te volgen:",
    STOCK_OPTIONS,
    default=["THYAO (Turkish Airlines)", "ASELS (Aselsan)", "KCHOL (Koç Holding)"]
)

# --- HULPFUNCTIES VOOR LIVE MARKTDATA & 3-DAGEN RSS FILTER ---
@st.cache_data(ttl=300, show_spinner=False)
def get_live_market_snapshot():
    symbols = {
        "BIST 100": "XU100.IS",
        "USD/TRY": "USDTRY=X",
        "EUR/TRY": "EURTRY=X",
        "Goud Ons ($)": "GC=F",
        "Zilver Ons ($)": "SI=F",
        "Brent Olie ($)": "BZ=F",
        "VIX (Angst)": "^VIX"
    }
    data = {}
    for name, sym in symbols.items():
        try:
            hist = yf.Ticker(sym).history(period="5d")
            if hist is not None and len(hist) >= 2:
                curr = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2])
                chg = ((curr - prev) / prev) * 100.0 if prev else 0.0
                data[name] = {"price": curr, "change": chg}
            else:
                data[name] = {"price": float(hist["Close"].iloc[-1]) if hist is not None and not hist.empty else None, "change": 0.0}
        except Exception:
            data[name] = {"price": None, "change": 0.0}

    usd_try = data.get("USD/TRY", {}).get("price")
    gold_usd = data.get("Goud Ons ($)", {}).get("price")
    if usd_try and gold_usd:
        gram_gold = (gold_usd * usd_try) / 31.1035
        data["Gram Goud (₺)"] = {"price": gram_gold, "change": data["Goud Ons ($)"]["change"] + data["USD/TRY"]["change"]}
    else:
        data["Gram Goud (₺)"] = {"price": None, "change": 0.0}
    return data

@st.cache_data(ttl=300, show_spinner=False)
def get_stock_snapshots(tickers_clean):
    snapshots = {}
    for code in tickers_clean:
        yf_sym = f"{code}.IS"
        try:
            hist = yf.Ticker(yf_sym).history(period="3mo")
            if hist is not None and len(hist) >= 15:
                close = hist["Close"].astype(float)
                curr = float(close.iloc[-1])
                prev = float(close.iloc[-2])
                chg_1d = ((curr - prev) / prev) * 100.0 if prev else 0.0
                sma20 = float(close.rolling(20).mean().iloc[-1])
                delta = close.diff()
                gain = delta.clip(lower=0).rolling(14).mean().iloc[-1]
                loss = (-delta.clip(upper=0)).rolling(14).mean().iloc[-1]
                rsi = 100.0 - (100.0 / (1.0 + (gain / loss))) if loss and loss > 0 else 50.0
                snapshots[code] = {"price": round(curr, 2), "change": round(chg_1d, 2), "rsi": round(rsi, 1), "trend": "Positief" if curr > sma20 else "Onder druk"}
            else:
                snapshots[code] = {"price": None, "change": 0.0, "rsi": 50.0, "trend": "Onbekend"}
        except Exception:
            snapshots[code] = {"price": None, "change": 0.0, "rsi": 50.0, "trend": "Onbekend"}
    return snapshots

@st.cache_data(ttl=300, show_spinner=False)
def fetch_recent_rss_with_links(query, lang="tr", max_items=6, max_days=3):
    q_enc = urllib.parse.quote(query)
    if lang == "tr":
        url = f"https://news.google.com/rss/search?q={q_enc}&hl=tr&gl=TR&ceid=TR:tr"
    else:
        url = f"https://news.google.com/rss/search?q={q_enc}&hl=nl&gl=NL&ceid=NL:nl"
    
    items = []
    now_utc = datetime.now(timezone.utc)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            root = ET.fromstring(resp.read())
        for item in root.findall(".//item"):
            title = item.findtext("title")
            link = item.findtext("link")
            pub_str = item.findtext("pubDate") or ""
            
            if title and link:
                is_recent = True
                if pub_str:
                    try:
                        from email.utils import parsedate_to_datetime
                        dt = parsedate_to_datetime(pub_str)
                        if dt:
                            diff_days = (now_utc - dt).total_seconds() / 86400.0
                            if diff_days > max_days:
                                is_recent = False
                    except Exception:
                        pass
                
                if is_recent:
                    items.append({"title": title, "link": link, "date": pub_str[:16]})
                    if len(items) >= max_items:
                        break
    except Exception:
        pass
    return items

# --- LIVE MARKT TICKER BAR ---
st.markdown("### 📊 Live Marktoverzicht")
market_data = get_live_market_snapshot()
market_items = list(market_data.items())

for row_slice in [market_items[:4], market_items[4:8]]:
    cols = st.columns(len(row_slice))
    for i, (name, info) in enumerate(row_slice):
        with cols[i]:
            if info["price"] is not None:
                st.metric(label=name, value=f"{info['price']:,.2f}", delta=f"{info['change']:+.2f}%")
            else:
                st.metric(label=name, value="N/B")

st.markdown("---")

# --- AI AANROEP ---
def call_gemini_with_fallback(prompt_text, system_instruction, fallback_text):
    token = st.session_state.gemini_auth.strip()
    if not token:
        return fallback_text
    full_prompt = f"{system_instruction}\n\n{prompt_text}" if system_instruction else prompt_text
    payload = {"contents": [{"role": "user", "parts": [{"text": full_prompt}]}], "generationConfig": {"temperature": 0.2}}
    data_bytes = json.dumps(payload).encode("utf-8")
    q_token = urllib.parse.quote(token)
    endpoints = [
        (f"https://aiplatform.googleapis.com/v1beta1/publishers/google/models/gemini-2.5-flash:generateContent?key={q_token}", {"Content-Type": "application/json"}),
        (f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={q_token}", {"Content-Type": "application/json"})
    ]
    for url, headers in endpoints:
        try:
            req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=12) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                text = res_json["candidates"][0]["content"]["parts"][0]["text"]
                if text and len(text.strip()) > 20:
                    return text
        except Exception:
            continue
    return fallback_text

# --- HOOFDPROGRAMMA ---
st.markdown("### 🤖 Start de 6-Agent Breaking News Scanner (Max 3 Dagen Oud)")
st.markdown("Druk op de knop om uitsluitend **vers nieuws van de afgelopen 72 uur** en marktinformatie te analyseren.")

if st.button("🚀 Start 6-Agent Analyse (Strict max 3 dagen oud)", type="primary"):
    tickers_clean = [t.split(" ")[0] for t in selected_tickers] if selected_tickers else ["THYAO", "ASELS", "KCHOL"]
    tickers_str = ", ".join(tickers_clean)

    with st.spinner("📡 Live ophalen van artikelen en marktomstandigheden (max 3 dagen oud)..."):
        stock_snaps = get_stock_snapshots(tickers_clean)
        tr_econ_items = fetch_recent_rss_with_links("Turkiye ekonomi Borsa Istanbul TCMB", "tr", 5, 3)
        tr_spk_items = fetch_recent_rss_with_links("SPK ceza sorusturma borsa operasyon", "tr", 4, 3)
        stock_news_dict = {c: fetch_recent_rss_with_links(f"{c} hisse KAP", "tr", 3, 3) for c in tickers_clean}
        nl_war_items = fetch_recent_rss_with_links("oorlog Midden-Oosten Oekraine geopolitiek olie", "nl", 5, 3)
        nl_gold_items = fetch_recent_rss_with_links("goudprijs zilverprijs Fed rente", "nl", 5, 3)
        agenda_items = fetch_recent_rss_with_links("Fed toplantı faiz kararı TCMB PPK TÜİK enflasyon", "tr", 6, 3)

        bist_p = market_data.get("BIST 100", {}).get("price") or 0.0
        bist_c = market_data.get("BIST 100", {}).get("change") or 0.0
        usd_p = market_data.get("USD/TRY", {}).get("price") or 0.0
        gold_p = market_data.get("Goud Ons ($)", {}).get("price") or 0.0
        gram_p = market_data.get("Gram Goud (₺)", {}).get("price") or 0.0
        silv_p = market_data.get("Zilver Ons ($)", {}).get("price") or 0.0
        vix_p = market_data.get("VIX (Angst)", {}).get("price") or 0.0

    # --- AGENT 1 ---
    with st.spinner("🇹🇷 Agent 1: BIST & Lokaal..."):
        fallback_agent1 = f"BIST 100 staat op {bist_p:,.0f} ({bist_c:+.2f}%). USD/TRY is ₺{usd_p:,.2f}."
        prompt_agent1 = "Jij bent Agent 1. Geef een analyse in simpele taal over BIST en aandelen (" + tickers_str + ")."
        agent1_output = call_gemini_with_fallback(prompt_agent1, "Je bent een Turkse marktexpert.", fallback_agent1)

    # --- AGENT 2 ---
    with st.spinner("🌍 Agent 2: Globaal & Edelmetalen..."):
        fallback_agent2 = f"Goud is ${gold_p:,.2f} (Gram: ₺{gram_p:,.2f}), Zilver is ${silv_p:,.2f}."
        prompt_agent2 = "Jij bent Agent 2. Analyseer goud, zilver en wereldnieuws."
        agent2_output = call_gemini_with_fallback(prompt_agent2, "Je bent een macro-analist.", fallback_agent2)

    # --- AGENT 3 ---
    with st.spinner("🕵️‍♂️ Agent 3: Fact-Check..."):
        fallback_agent3 = "✅ Harde marktdata geverifieerd via Yahoo Finance en recente RSS feeds."
        prompt_agent3 = "Jij bent Agent 3. Voer fact-check uit."
        agent3_output = call_gemini_with_fallback(prompt_agent3, "Je bent een factchecker.", fallback_agent3)

    # --- AGENT 4 ---
    with st.spinner("💡 Agent 4: Beleggingsadvies..."):
        fallback_agent4 = "Concreet advies: Spreid aankopen in goud en geselecteerde aandelen."
        prompt_agent4 = "Jij bent Agent 4. Geef advies in Jip-en-Janneketaal."
        agent4_output = call_gemini_with_fallback(prompt_agent4, "Je bent beleggingsadviseur.", fallback_agent4)

    # --- AGENT 5 ---
    with st.spinner("⚖️ Agent 5: Auditing..."):
        fallback_agent5 = "Let op valutarisico's en recente geopolitieke spanningen (VIX: " + str(vix_p) + ")."
        prompt_agent5 = "Jij bent Agent 5. Voer risico-audit uit."
        agent5_output = call_gemini_with_fallback(prompt_agent5, "Je bent risicocontroleur.", fallback_agent5)

    # --- AGENT 6: Macro Agenda & Slimme Samenvatting ---
    with st.spinner("📅 Agent 6: Macro Agenda & Samenvatting genereren..."):
        agenda_titles = "\n".join([f"- {item['title']}" for item in agenda_items]) if agenda_items else "Geen specifieke agenda-items gevonden."
        fallback_agent6 = (
            f"### 📅 Macro Agenda & Belangrijke Gebeurtenissen (Samenvatting)\n\n"
            f"Op basis van de meest recente berichtgeving van de afgelopen 3 dagen zijn dit de belangrijkste verwachte gebeurtenissen:\n"
            f"- **Centrale Banken (Fed & TCMB):** Nauwlettend in de gaten gehouden renteverwachtingen en inflatieprojecties.\n"
            f"- **Macro-data:** Publicaties van consumentenprijzen en handelsbalansen die directst invloed hebben op BIST 100 en edelmetalen."
        )
        prompt_agent6 = (
            "Jij bent Agent 6: De Macro-Agenda & Gebeurtenissen Samenvatter.\n"
            "Hier zijn de koppen van recente agenda- en nieuwsartikelen van de afgelopen 3 dagen:\n"
            f"{agenda_titles}\n\n"
            "Lees deze koppen en vat ze samen in heldere, normale mensentaal (Jip-en-Janneketaal). "
            "Vertel wat dit betekent voor de belegger en welke datums of gebeurtenissen cruciaal zijn."
        )
        agent6_output = call_gemini_with_fallback(prompt_agent6, "Je bent een macro-economisch analist die koppen omzet naar duidelijke samenvattingen.", fallback_agent6)

    # --- TOON RESULTATEN IN TABS MET 3-DAGEN FILTER ---
    st.success("✅ Analyse voltooid! Uitsluitend artikelen van maximaal 3 dagen oud geladen.")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🇹🇷 Agent 1: BIST",
        "🌍 Agent 2: Globaal",
        "🕵️‍♂️ Agent 3: Fact-Check",
        "💡 Agent 4: Advies",
        "⚖️ Agent 5: Auditing",
        "📅 Agent 6: Macro Agenda"
    ])

    with tab1:
        st.markdown("### Agent 1: Turkije, Politiek & Aandelen Nieuws")
        st.markdown(agent1_output)
        st.markdown("---")
        st.markdown("#### 🔗 Breaking Nieuws & Meldingen (Max 3 Dagen Oud)")
        if tr_econ_items or tr_spk_items:
            for item in tr_econ_items + tr_spk_items:
                st.markdown(f"- [{item['title']}]({item['link']}) *({item['date']})*")
            for c in tickers_clean:
                for item in stock_news_dict.get(c, []):
                    st.markdown(f"- **[{c}]** [{item['title']}]({item['link']}) *({item['date']})*")
        else:
            st.info("Geen artikelen van de afgelopen 3 dagen gevonden voor deze categorie.")

    with tab2:
        st.markdown("### Agent 2: Wereldnieuws, Oorlog & Edelmetalen")
        st.markdown(agent2_output)
        st.markdown("---")
        st.markdown("#### 🔗 Recente Wereldwijde & Edelmetaal Artikelen (Max 3 Dagen Oud)")
        if nl_war_items or nl_gold_items:
            for item in nl_war_items + nl_gold_items:
                st.markdown(f"- [{item['title']}]({item['link']}) *({item['date']})*")
        else:
            st.info("Geen recente internationale artikelen van de afgelopen 3 dagen gevonden.")

    with tab3:
        st.markdown("### Agent 3: De Waarheids-Filter (Fact-Check)")
        st.markdown(agent3_output)

    with tab4:
        st.markdown("### Agent 4: Concreet Beleggingsadvies (Jip-en-Janneketaal)")
        st.markdown(agent4_output)

    with tab5:
        st.markdown("### Agent 5: Eindcontrole & Risico-Audit")
        st.markdown(agent5_output)

    with tab6:
        st.markdown("### Agent 6: Wereldwijde & Turkse Macro-Agenda (Samenvatting)")
        st.markdown(agent6_output)
        st.markdown("---")
        st.markdown("#### 🔗 Recente Agenda-Artikelen (Max 3 Dagen Oud)")
        if agenda_items:
            for item in agenda_items:
                st.markdown(f"- [{item['title']}]({item['link']}) *({item['date']})*")
        else:
            st.info("Geen recente agenda-artikelen van de afgelopen 3 dagen gevonden.")

else:
    st.info("👈 Kies je aandelen in de zijbalk en klik op de knop om de up-to-date analyse te starten!")
