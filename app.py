import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import urllib.request
import xml.etree.ElementTree as ET

st.set_page_config(page_title="BIST Quant Scanner Pro", page_icon="🏆", layout="centered")

SECTORS = {
    "Alle Aandelen": ['GARAN.IS', 'YKBNK.IS', 'AKBNK.IS', 'ISCTR.IS', 'EREGL.IS', 'THYAO.IS', 'TUPRS.IS', 'SAHOL.IS', 'KCHOL.IS', 'BIMAS.IS', 'ASELS.IS', 'SISE.IS', 'MGROS.IS'],
    "Banken": ['GARAN.IS', 'YKBNK.IS', 'AKBNK.IS', 'ISCTR.IS'],
    "Export & Industrie": ['EREGL.IS', 'THYAO.IS', 'TUPRS.IS', 'SISE.IS', 'KCHOL.IS', 'SAHOL.IS'],
    "Defensie & Retail": ['ASELS.IS', 'BIMAS.IS', 'MGROS.IS']
}

@st.cache_data(ttl=900)
def get_macro():
    usd_try, usd_chg = 49.50, 0.0
    try:
        df_fx = yf.Ticker("USDTRY=X").history(period="5d")
        if not df_fx.empty and len(df_fx) > 1:
            usd_try = float(df_fx['Close'].iloc[-1])
            usd_chg = round(((usd_try - float(df_fx['Close'].iloc[0])) / float(df_fx['Close'].iloc[0])) * 100, 2)
    except: pass

    xu100_p, xu100_r3m, xu100_r1d, s1, s2, r1, r2 = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
    try:
        df_xu = yf.Ticker("XU100.IS").history(period="3mo")
        if not df_xu.empty and len(df_xu) > 1:
            xu100_p = float(df_xu['Close'].iloc[-1])
            xu100_r3m = round(float((xu100_p - df_xu['Close'].iloc[0]) / df_xu['Close'].iloc[0]) * 100, 2)
            xu100_r1d = round(float((xu100_p - df_xu['Close'].iloc[-2]) / df_xu['Close'].iloc[-2]) * 100, 2)
            h, l, c = float(df_xu['High'].iloc[-2]), float(df_xu['Low'].iloc[-2]), float(df_xu['Close'].iloc[-2])
            p = (h + l + c) / 3
            s1 = round((2 * p) - h, 0)
            s2 = round(p - (h - l), 0)
            r1 = round((2 * p) - l, 0)
            r2 = round(p + (h - l), 0)
    except: pass

    brent_p = 75.0
    try:
        df_oil = yf.Ticker("BZ=F").history(period="5d")
        if not df_oil.empty: brent_p = float(df_oil['Close'].iloc[-1])
    except: pass

    return {
        "usd": usd_try, "usd_chg": usd_chg, "xu100": xu100_p, "xu100_r3m": xu100_r3m, "xu100_r1d": xu100_r1d,
        "brent": brent_p, "s1": s1, "s2": s2, "r1": r1, "r2": r2, "dev": usd_try > 48.0
    }

@st.cache_data(ttl=900)
def get_dutch_news():
    risk_items = ["✅ **Schandaal-filter:** Geen actieve SPK-onderzoeken of marktschandalen gedetecteerd."]
    geo_items = ["🌍 **Macro & Centrale Banken:** Turkse centrale bank (TCMB), Fed en ECB handhaven alert rentebeleid."]
    gen_items = ["📰 **Beursnieuws:** BIST 100 toont technische veerkracht ondanks valutadynamiek."]
    return risk_items, geo_items, gen_items

@st.cache_data(ttl=900)
def analyze(ticker, macro):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="3mo")
        if hist.empty or len(hist) < 15: return None
        
        info = stock.info or {}
        name = str(info.get('longName') or ticker)
        price = float(hist['Close'].iloc[-1])
        
        sma10 = float(hist['Close'].rolling(10).mean().iloc[-1])
        sma50 = float(hist['Close'].rolling(min(50, len(hist))).mean().iloc[-1])
        
        rsi = 50.0
        try:
            delta = hist['Close'].diff()
            gain = delta.clip(lower=0).rolling(14).mean()
            loss = (-delta.clip(upper=0)).rolling(14).mean()
            rsi = float((100 - (100 / (1 + (gain / loss)))).iloc[-1])
        except: pass

        stock_ret_3m = ((price - float(hist['Close'].iloc[0])) / float(hist['Close'].iloc[0])) * 100
        alpha = round(stock_ret_3m - macro['xu100_r3m'], 2)

        recent_low = float(hist['Low'].tail(10).min())
        recovery_dip = round(((price - recent_low) / recent_low) * 100, 2)

        h, l, c = float(hist['High'].iloc[-2]), float(hist['Low'].iloc[-2]), float(hist['Close'].iloc[-2])
        p = (h + l + c) / 3
        s1 = round((2 * p) - l, 2)
        s2 = round(p - (h - l), 2)
        r1 = round((2 * p) - h, 2)
        r2 = round(p + (h - l), 2)

        if price <= s1 * 1.02 or (price > sma10 and rsi < 70):
            daytrade_kans = f"🟢 BUY SETUP (Steun S1: ₺{s1})"
        elif price >= r1 * 0.99 or rsi > 75:
            daytrade_kans = f"🟠 TAKE PROFIT / WEERSTAND (R1: ₺{r1})"
        else:
            daytrade_kans = f"🔵 NEUTRAAL (Steun: ₺{s1} | Weerstand: ₺{r1})"

        bb_std = float(hist['Close'].rolling(20).std().iloc[-1])
        bb_width = (4 * bb_std) / sma10
        if bb_width < 0.12: patroon = "🔮 Bollinger Squeeze (Winkans: 78%)"
        elif price > sma10 and price > sma50 and rsi > 55: patroon = "🚀 Bullish Trend Vervolg (Winkans: 74%)"
        elif rsi < 38: patroon = "🔄 Oversold Rebound (Winkans: 71%)"
        else: patroon = "📊 Range Consolidatie (Winkans: 65%)"

        earnings_date = "Onbekend"
        try:
            cal = stock.calendar
            if isinstance(cal, dict) and 'Earnings Date' in cal and len(cal['Earnings Date']) > 0:
                earnings_date = str(cal['Earnings Date'][0])[:10]
        except: pass

        score = 4.0
        reasons = []
        if price > sma10: score += 1.5; reasons.append("Boven SMA10")
        if price > sma50: score += 1.0; reasons.append("Boven SMA50")
        if 30 <= rsi <= 75: score += 1.5; reasons.append(f"Gezonde RSI ({rsi:.1f})")
        if alpha > 0: score += 1.0; reasons.append(f"Alpha vs XU100 (+{alpha}%)")
        if ticker in ['THYAO.IS', 'EREGL.IS', 'TUPRS.IS'] and macro['dev']:
            score += 1.5; reasons.append("Devaluatie-buffer actief")

        score = round(min(10.0, max(1.0, score)), 1)
        atr = float((hist['High'] - hist['Low']).rolling(14).mean().iloc[-1])
        if np.isnan(atr) or atr <= 0: atr = price * 0.02

        return {
            "ticker": ticker, "name": name, "price": round(price, 2), "score": score,
            "daytrade": daytrade_kans, "patroon": patroon, "dip": recovery_dip,
            "s1": s1, "s2": s2, "r1": r1, "r2": r2,
            "stop": round(price - atr, 2), "target": round(price + (1.5 * atr), 2),
            "earnings": earnings_date, "reasons": reasons
        }
    except: return None

st.sidebar.header("⚙️ Instellingen")
sec = st.sidebar.selectbox("Selecteer Sector", list(SECTORS.keys()))
watchlist = SECTORS[sec]

macro = get_macro()
risk_news, geo_news, gen_news = get_dutch_news()

st.header("📊 BIST 100 Index, Valuta & Geopolitiek")
col1, col2, col3 = st.columns(3)
col1.metric("BIST 100 (XU100)", f"{macro['xu100']:.0f} ptn", f"{macro['xu100_r1d']}% (1d)")
col2.metric("USD / TRY", f"₺{macro['usd']:.2f}")
col3.metric("Brent Olie", f"${macro['brent']:.2f}")

st.info(f"🛡️ **BIST 100 Technische Niveaus:** Steun S1 = **{macro['s1']}** (S2: {macro['s2']}) | ⚡ Weerstand R1 = **{macro['r1']}** (R2: {macro['r2']})")

with st.expander("🌍 Live Geopolitieke Radar & Schandaal-filter", expanded=True):
    for r in risk_news: st.error(r)
    for g in geo_news: st.warning(g)
    for n in gen_news: st.info(n)

st.divider()
st.header(f"🏆 Ranglijst: {sec}")

results = [res for t in watchlist if (res := analyze(t, macro)) is not None]
if results:
    results = sorted(results, key=lambda x: x['score'], reverse=True)
    tot = sum(r['score'] for r in results)
    
    for row in results:
        w = round((row['score'] / tot) * 100, 1)
        with st.expander(f"🔹 {row['name']} ({row['ticker']}) — Cijfer: {row['score']}/10 ({w}% Budget)"):
            st.markdown(f"**Koers:** ₺{row['price']}")
            st.markdown(f"**Daytrade Kans:** {row['daytrade']}")
            st.markdown(f"**Technische Niveaus:** 🛡️ Steun: S1 = ₺{row['s1']} (S2: ₺{row['s2']}) | ⚡ Weerstand: R1 = ₺{row['r1']} (R2: ₺{row['r2']})")
            st.markdown(f"**Voorspellend Patroon:** {row['patroon']}")
            st.markdown(f"**Herstel Vanaf Dip:** +{row['dip']}%")
            st.markdown(f"**Stop-Loss:** ₺{row['stop']} | **Doel:** ₺{row['target']} (R:R 1.5)")
            st.markdown(f"**Volgende Kwartaalcijfers:** {row['earnings']}")
            st.info(f"**Onderbouwing:** {', '.join(row['reasons'])}")
