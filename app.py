import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import urllib.request
import xml.etree.ElementTree as ET

# Pagina configuratie
st.set_page_config(page_title="BIST Quant Trading Bot", layout="wide")

WATCHLIST = [
    'GARAN.IS', 'AKBNK.IS', 'EREGL.IS', 'THYAO.IS', 
    'TUPRS.IS', 'KCHOL.IS', 'SAHOL.IS', 'BIMAS.IS',
    'YKBNK.IS', 'ISCTR.IS', 'ASELS.IS', 'SISE.IS', 'MGROS.IS'
]

@st.cache_data(ttl=300)
def analyze_macro_and_global_news():
    usd_try = 49.50
    try:
        df = yf.Ticker("USDTRY=X").history(period="5d")
        if not df.empty and 'Close' in df.columns:
            usd_try = float(df['Close'].iloc[-1])
    except Exception:
        pass
        
    mkt_ret = 0.0
    try:
        df = yf.Ticker("XU100.IS").history(period="3mo")
        if not df.empty and len(df) > 1 and 'Close' in df.columns:
            mkt_ret = round(float((df['Close'].iloc[-1] - df['Close'].iloc[0]) / df['Close'].iloc[0]) * 100, 2)
    except Exception:
        pass

    dev_risk = usd_try > 48.0
    return dev_risk, mkt_ret, usd_try

def analyze_stock(ticker, dev_risk):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1mo")
        if hist is None or hist.empty or len(hist) < 5: 
            return None
        
        info = stock.info or {}
        name = str(info.get('longName') or ticker)
        price = float(hist['Close'].iloc[-1])
        
        target_mean = info.get('targetMeanPrice')
        analyst_recommendation = str(info.get('recommendationKey', 'hold')).upper()
        num_analysts = info.get('numberOfAnalystOpinions', 0)
        
        if len(hist) >= 2:
            h, l, c = float(hist['High'].iloc[-2]), float(hist['Low'].iloc[-2]), float(hist['Close'].iloc[-2])
        else:
            h, l, c = price, price, price
            
        pivot = (h + l + c) / 3
        r1 = round((2 * pivot) - l, 2)
        s1 = round((2 * pivot) - h, 2)
        
        sma = float(hist['Close'].rolling(min(10, len(hist))).mean().iloc[-1])
        delta = hist['Close'].diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        
        rsi = 50.0
        if not gain.empty and not loss.empty:
            rs_val = gain / loss
            rsi_series = 100 - (100 / (1 + rs_val))
            if not rsi_series.empty:
                rsi = float(rsi_series.iloc[-1])
        
        points = 4.0
        reasons = []
        
        if price > sma: 
            points += 1.5
            reasons.append("Koers boven korte SMA (+1.5p)")
        if 30 <= rsi <= 80: 
            points += 1.5
            reasons.append(f"Gezonde RSI ({rsi:.1f}) (+1.5p)")
            
        if ticker in ['THYAO.IS', 'EREGL.IS', 'SISE.IS', 'TUPRS.IS'] and dev_risk:
            points += 2.0
            reasons.append("Devaluatie-buffer actief (+2.0p)")
            
        if analyst_recommendation in ['BUY', 'STRONG_BUY']:
            points += 1.0
            reasons.append(f"Analisten consensus: {analyst_recommendation} (+1.0p)")
        elif analyst_recommendation in ['UNDERPERFORM', 'SELL']:
            points -= 1.0
            reasons.append(f"Analisten consensus: {analyst_recommendation} (+1.0p)")
            
        score = round(min(10.0, max(1.0, points)), 1)
        
        if len(hist) >= 14:
            atr = float((hist['High'] - hist['Low']).rolling(14).mean().iloc[-1])
        else:
            atr = price * 0.03
        
        return {
            "Ticker": ticker, 
            "Bedrijf": name, 
            "Prijs (TRY)": round(price, 2), 
            "RSI": round(rsi, 1),
            "Cijfer": score, 
            "Res1": r1, 
            "Sup1": s1, 
            "StopLoss": round(price - atr, 2),
            "Doel": round(price + (1.5 * atr), 2), 
            "AnalistenDoel": round(target_mean, 2) if target_mean else 0.0,
            "Advies": analyst_recommendation,
            "Analisten": num_analysts,
            "Onderbouwing": ", ".join(reasons)
        }
    except Exception:
        return None

# Streamlit Interface
st.title("🧠 BIST Quant Trading Bot & Dashboard")
st.markdown("---")

dev_risk, mkt_ret, usd_try = analyze_macro_and_global_news()

col1, col2 = st.columns(2)
with col1:
    st.metric(label="💱 USD/TRY Koers", value=f"₺{usd_try:.2f}", delta="Risico actief" if dev_risk else "Stabiel")
with col2:
    st.metric(label="📈 BIST 100 (3m Rendement)", value=f"{mkt_ret}%")

st.markdown("### 🏆 Live Ranglijst & Niveaus")

if st.button("Start Analyse Scan"):
    with st.spinner("Gegevens ophalen van Yahoo Finance... Even geduld..."):
        results = []
        for t in WATCHLIST:
            res = analyze_stock(t, dev_risk)
            if res: 
                results.append(res)
            
        if results:
            df_res = pd.DataFrame(results)
            df_res = df_res.sort_values(by="Cijfer", ascending=False).reset_index(drop=True)
            
            tot = df_res["Cijfer"].sum()
            df_res["Weging %"] = df_res["Cijfer"].apply(lambda x: round((x / tot) * 100, 2) if tot > 0 else 0)
            
            st.success("Analyse voltooid!")
            st.dataframe(df_res, use_container_width=True)
            
            for index, row in df_res.iterrows():
                with st.expander(f"{row['Bedrijf']} ({row['Ticker']}) - Cijfer: {row['Cijfer']}/10"):
                    st.write(f"**Huidige Koers:** ₺{row['Prijs (TRY)']} | **RSI:** {row['RSI']}")
                    st.write(f"**Analisten Advies:** {row['Advies']} (Doel: ₺{row['AnalistenDoel']} | {row['Analisten']} analisten)")
                    st.write(f"**Daytrading Niveaus:** Weerstand R1: ₺{row['Res1']} | Steun S1: ₺{row['Sup1']}")
                    st.write(f"**Risicobeheer:** Stop-Loss: ₺{row['StopLoss']} | Doel: ₺{row['Doel']}")
                    st.write(f"**Onderbouwing:** {row['Onderbouwing']}")
        else:
                st.warning("Geen resultaten gevonden.")
else:
    st.info("Klik op de knop hierboven om de scan te starten.")
