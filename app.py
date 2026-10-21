import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="BIST Quant Scanner", page_icon="🏆", layout="centered")

SECTORS = {
    "Alle Aandelen": ['GARAN.IS', 'YKBNK.IS', 'AKBNK.IS', 'ISCTR.IS', 'EREGL.IS', 'THYAO.IS', 'TUPRS.IS', 'SAHOL.IS', 'KCHOL.IS', 'BIMAS.IS', 'ASELS.IS', 'SISE.IS', 'MGROS.IS'],
    "Banken": ['GARAN.IS', 'YKBNK.IS', 'AKBNK.IS', 'ISCTR.IS'],
    "Export & Industrie": ['EREGL.IS', 'THYAO.IS', 'TUPRS.IS', 'SISE.IS', 'KCHOL.IS', 'SAHOL.IS'],
    "Defensie & Retail": ['ASELS.IS', 'BIMAS.IS', 'MGROS.IS']
}

@st.cache_data(ttl=900)
def get_macro():
    usd_try = 49.50
    try:
        df_fx = yf.Ticker("USDTRY=X").history(period="5d")
        if not df_fx.empty: usd_try = float(df_fx['Close'].iloc[-1])
    except: pass

    xu100_p, xu100_r3m, s1, r1 = 0.0, 0.0, 0.0, 0.0
    try:
        df_xu = yf.Ticker("XU100.IS").history(period="3mo")
        if not df_xu.empty:
            xu100_p = float(df_xu['Close'].iloc[-1])
            xu100_r3m = float((xu100_p - df_xu['Close'].iloc[0]) / df_xu['Close'].iloc[0]) * 100
            h, l, c = float(df_xu['High'].iloc[-2]), float(df_xu['Low'].iloc[-2]), float(df_xu['Close'].iloc[-2])
            p = (h + l + c) / 3
            s1, r1 = round((2 * p) - h, 0), round((2 * p) - l, 0)
    except: pass

    return {"usd": usd_try, "xu100": xu100_p, "xu100_r3m": xu100_r3m, "s1": s1, "r1": r1, "dev": usd_try > 48.0}

@st.cache_data(ttl=900)
def analyze(ticker, macro):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="3mo")
        if hist.empty or len(hist) < 15: return None
        
        name = str(stock.info.get('longName') or ticker)
        price = float(hist['Close'].iloc[-1])
        
        sma10 = float(hist['Close'].rolling(10).mean().iloc[-1])
        rsi = float(50.0)
        try:
            delta = hist['Close'].diff()
            gain = delta.clip(lower=0).rolling(14).mean()
            loss = (-delta.clip(upper=0)).rolling(14).mean()
            rsi = float((100 - (100 / (1 + (gain / loss)))).iloc[-1])
        except: pass

        h, l, c = float(hist['High'].iloc[-2]), float(hist['Low'].iloc[-2]), float(hist['Close'].iloc[-2])
        p = (h + l + c) / 3
        s1, r1 = round((2 * p) - l, 2), round((2 * p) - h, 2)
        
        score = 5.0
        reasons = []
        if price > sma10: score += 1.5; reasons.append("Boven SMA10")
        if 30 <= rsi <= 75: score += 1.5; reasons.append(f"Gezonde RSI ({rsi:.1f})")
        if ticker in ['THYAO.IS', 'EREGL.IS', 'TUPRS.IS'] and macro['dev']:
            score += 2.0; reasons.append("Devaluatie-buffer actief")

        score = round(min(10.0, max(1.0, score)), 1)
        atr = float((hist['High'] - hist['Low']).rolling(14).mean().iloc[-1])
        
        return {
            "ticker": ticker, "name": name, "price": round(price, 2), "score": score,
            "s1": s1, "r1": r1, "stop": round(price - atr, 2), "target": round(price + (1.5 * atr), 2),
            "reasons": reasons
        }
    except: return None

st.sidebar.header("⚙️ Instellingen")
sec = st.sidebar.selectbox("Selecteer Sector", list(SECTORS.keys()))
watchlist = SECTORS[sec]

macro = get_macro()

st.header("📊 BIST 100 & Macro")
col1, col2, col3 = st.columns(3)
col1.metric("BIST 100", f"{macro['xu100']:.0f} ptn", f"{macro['xu100_r3m']:.1f}% (3m)")
col2.metric("USD / TRY", f"₺{macro['usd']:.2f}")
col3.metric("BIST 100 Steun S1", f"{macro['s1']:.0f}")

st.divider()
st.header(f"🏆 Ranglijst: {sec}")

results = [res for t in watchlist if (res := analyze(t, macro)) is not None]
if results:
    results = sorted(results, key=lambda x: x['score'], reverse=True)
    tot = sum(r['score'] for r in results)
    
    for row in results:
        w = round((row['score'] / tot) * 100, 1)
        with st.expander(f"🔹 {row['name']} ({row['ticker']}) — Cijfer: {row['score']}/10 ({w}% Budget)"):
            st.markdown(f"**Koers:** ₺{row['price']} | **Steun S1:** ₺{row['s1']} | **Weerstand R1:** ₺{row['r1']}")
            st.markdown(f"**Stop-Loss:** ₺{row['stop']} | **Doel:** ₺{row['target']}")
            st.info(f"**Onderbouwing:** {', '.join(row['reasons'])}")
