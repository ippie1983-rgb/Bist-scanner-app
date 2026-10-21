import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import urllib.request
import xml.etree.ElementTree as ET

# Pagina-configuratie
st.set_page_config(
    page_title="BIST 100 Quant Scanner",
    page_icon="📈",
    layout="wide"
)

# 1. Watchlist & Trefwoorden
WATCHLIST = [
    'GARAN.IS', 'AKBNK.IS', 'EREGL.IS', 'THYAO.IS', 
    'TUPRS.IS', 'KCHOL.IS', 'SAHOL.IS', 'BIMAS.IS',
    'YKBNK.IS', 'ISCTR.IS', 'ASELS.IS', 'SISE.IS', 'MGROS.IS'
]

EXPORT_BUFFERS = ['THYAO.IS', 'EREGL.IS', 'SISE.IS', 'TUPRS.IS', 'ASELS.IS']

POSITIVE_KEYWORDS = [
    'rekor', 'kar', 'temettü', 'büyüme', 'ihracat', 
    'anlaşma', 'yatırım', 'sipariş', 'onay', 'artış', 
    'güçlü', 'hedef fiyat', 'al tavsiyesi', 'kapasite'
]

NEGATIVE_KEYWORDS = [
    'zarar', 'ceza', 'soruşturma', 'spk', 'düşüş', 
    'kriz', 'iptal', 'grev', 'dava', 'borç', 
    'risk', 'satış baskısı', 'skandal', 'enflasyon'
]

# 2. Macro & FX Analyse
@st.cache_data(ttl=900)
def analyze_macro():
    usd_try = 49.50
    try:
        df_fx = yf.Ticker("USDTRY=X").history(period="5d")
        if not df_fx.empty:
            usd_try = float(df_fx['Close'].iloc[-1])
    except Exception:
        pass

    mkt_ret = 0.0
    try:
        df_bist = yf.Ticker("XU100.IS").history(period="3mo")
        if not df_bist.empty and len(df_bist) > 1:
            mkt_ret = round(float((df_bist['Close'].iloc[-1] - df_bist['Close'].iloc[0]) / df_bist['Close'].iloc[0]) * 100, 2)
    except Exception:
        pass

    dev_risk = usd_try > 48.0
    return usd_try, mkt_ret, dev_risk

# 3. Live RSS Nieuws & Sentiment Scanner
@st.cache_data(ttl=900)
def fetch_news_sentiment():
    rss_urls = [
        "https://www.investing.com/rss/news_25.rss",
        "https://tr.investing.com/rss/news_25.rss"
    ]
    headlines = []
    pos_hits = 0
    neg_hits = 0

    for url in rss_urls:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                xml_data = response.read()
                root = ET.fromstring(xml_data)
                for item in root.findall('.//item')[:8]:
                    title = item.find('title').text if item.find('title') is not None else ""
                    if title:
                        headlines.append(title)
                        title_lower = title.lower()
                        if any(k in title_lower for k in POSITIVE_KEYWORDS):
                            pos_hits += 1
                        if any(k in title_lower for k in NEGATIVE_KEYWORDS):
                            neg_hits += 1
        except Exception:
            continue

    return headlines[:10], pos_hits, neg_hits

# 4. Technische & Quant Analyse per Aandeel
@st.cache_data(ttl=900)
def analyze_stock(ticker, dev_risk, mkt_ret):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="3mo")
        if hist is None or hist.empty or len(hist) < 15:
            return None

        info = stock.info or {}
        name = str(info.get('longName') or ticker.replace('.IS', ''))
        price = float(hist['Close'].iloc[-1])

        # Daytrading Pivot Points (gebaseerd op voorgaande handelsdag)
        h = float(hist['High'].iloc[-2])
        l = float(hist['Low'].iloc[-2])
        c = float(hist['Close'].iloc[-2])
        pivot = (h + l + c) / 3
        r1 = round((2 * pivot) - l, 2)
        s1 = round((2 * pivot) - h, 2)

        # Korte SMA (10 dagen) & RSI (14 dagen)
        sma10 = float(hist['Close'].rolling(min(10, len(hist))).mean().iloc[-1])
        
        delta = hist['Close'].diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss
        rsi_series = 100 - (100 / (1 + rs))
        rsi = float(rsi_series.iloc[-1]) if not rsi_series.dropna().empty else 50.0

        # Relatieve sterkte t.o.v. BIST 100 (3 maanden)
        stock_ret_3m = round(float((price - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100, 2)
        rel_strength = round(stock_ret_3m - mkt_ret, 2)

        # Quant Scoring Systeem (Schaal 1 tot 10)
        points = 4.0
        reasons = []

        if price > sma10:
            points += 1.5
            reasons.append("Koers boven 10-daags SMA (+1.5p)")
        
        if 35 <= rsi <= 70:
            points += 1.5
            reasons.append(f"Gezonde RSI van {rsi:.1f} (+1.5p)")
        elif rsi < 35:
            points += 2.0
            reasons.append(f"Oversold RSI van {rsi:.1f} - Rebound kans (+2.0p)")
        elif rsi > 75:
            points -= 1.0
            reasons.append(f"Overbought RSI van {rsi:.1f} (-1.0p)")

        if rel_strength > 0:
            points += 1.0
            reasons.append(f"Outperformance BIST 100 met +{rel_strength}% (+1.0p)")

        if ticker in EXPORT_BUFFERS and dev_risk:
            points += 2.0
            reasons.append("🚨 Devaluatie-buffer & harde valuta inkomsten (+2.0p)")

        score = round(min(10.0, max(1.0, points)), 1)
        atr = float((hist['High'] - hist['Low']).rolling(14).mean().iloc[-1])

        return {
            "Ticker": ticker.replace('.IS', ''),
            "Bedrijf": name,
            "Prijs (₺)": round(price, 2),
            "RSI": round(rsi, 1),
            "3M Rel. Sterkte (%)": rel_strength,
            "Steun S1 (₺)": s1,
            "Weerstand R1 (₺)": r1,
            "Stop-Loss (₺)": round(price - atr, 2),
            "Doel (₺)": round(price + (1.5 * atr), 2),
            "Cijfer": score,
            "Onderbouwing": " | ".join(reasons)
        }
    except Exception:
        return None

# --- STREAMLIT UI DASHBOARD ---
st.title("🧠 BIST 100 Quant & Macro Scanner")
st.markdown("Live technische analyse, devaluatie-buffers, relatieve sterkte en daytrading-pivots voor Borsa Istanbul.")

usd_try, mkt_ret, dev_risk = analyze_macro()
headlines, pos_hits, neg_hits = fetch_news_sentiment()

# Macro Metrics Rij
col1, col2, col3, col4 = st.columns(4)
col1.metric("💱 USD/TRY Koers", f"₺{usd_try:.2f}", "Devaluatierisico Hoog" if dev_risk else "Stabiel", delta_color="inverse" if dev_risk else "normal")
col2.metric("📊 BIST 100 (3M Rendement)", f"{mkt_ret}%")
col3.metric("🟢 Positieve Nieuws-triggers", pos_hits)
col4.metric("🔴 Risico / Schandaal-triggers", neg_hits)

st.divider()

# Aandelen Scannen
with st.spinner("BIST-aandelen en marktdata analyseren..."):
    results = []
    for t in WATCHLIST:
        res = analyze_stock(t, dev_risk, mkt_ret)
        if res:
            results.append(res)

if results:
    df_res = pd.DataFrame(results).sort_values(by="Cijfer", ascending=False).reset_index(drop=True)
    tot_score = df_res["Cijfer"].sum()
    df_res["Portefeuille Weging (%)"] = ((df_res["Cijfer"] / tot_score) * 100).round(1)

    st.subheader("🏆 Quant Ranglijst & Daytrading Niveaus")
    
    # Overzichtelijke Tabel
    display_cols = [
        "Ticker", "Bedrijf", "Cijfer", "Portefeuille Weging (%)", 
        "Prijs (₺)", "RSI", "3M Rel. Sterkte (%)", 
        "Steun S1 (₺)", "Weerstand R1 (₺)", "Stop-Loss (₺)", "Doel (₺)"
    ]
    st.dataframe(df_res[display_cols], use_container_width=True, hide_index=True)

    # Gedetailleerde Kaarten per Aandeel
    st.subheader("🔍 Gedetailleerde Onderbouwing per Aandeel")
    for _, row in df_res.iterrows():
        with st.expander(f"⭐ {row['Ticker']} - {row['Bedrijf']} | Cijfer: {row['Cijfer']}/10 (Weging: {row['Portefeuille Weging (%)']}%)"):
            c1, c2, c3 = st.columns(3)
            c1.write(f"**Huidige Koers:** ₺{row['Prijs (₺)']} (RSI: {row['RSI']})")
            c2.write(f"**Daytrading Range:** S1: ₺{row['Steun S1 (₺)']} | R1: ₺{row['Weerstand R1 (₺)']}")
            c3.write(f"**Risicobeheer:** Stop-Loss: ₺{row['Stop-Loss (₺)']} | Doel: ₺{row['Doel (₺)']}")
            st.info(f"**Analyse:** {row['Onderbouwing']}")
else:
    st.warning("Kon momenteel geen koersdata ophalen van Yahoo Finance. Probeer het over enkele seconden opnieuw.")

# Live Nieuws Sectie
if headlines:
    st.divider()
    st.subheader("📰 Laatste Markt- & Macrokoppen (RSS)")
    for h in headlines:
        st.markdown(f"- {h}")
