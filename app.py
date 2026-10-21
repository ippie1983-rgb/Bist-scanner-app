import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import urllib.request
import xml.etree.ElementTree as ET

st.set_page_config(page_title="BIST Quant & Fundamentele Analyse", layout="wide")

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

    global_warnings = []
    try:
        url = "https://news.google.com/rss/search?q=Turkije+economie+geopolitiek+olie&hl=nl&gl=NL&ceid=NL:nl"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)
            for item in root.findall('.//item')[:5]:
                title = item.find('text') or item.find('title')
                if title is not None and title.text:
                    t_lower = title.text.lower()
                    if any(w in t_lower for w in ['oorlog', 'olie', 'crisis', 'sanctie', 'inflatie', 'onderzoek', 'spk', 'risico', 'geopolitiek', 'turkije']):
                        global_warnings.append(title.text)
    except Exception:
        pass

    dev_risk = usd_try > 48.0
    return dev_risk, mkt_ret, usd_try, global_warnings

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
        raw_rec = str(info.get('recommendationKey', 'hold')).upper()
        
        advies_map = {'BUY': 'KOPEN', 'STRONG_BUY': 'STERK KOPEN', 'HOLD': 'HOUDEN', 'UNDERPERFORM': 'ONDERPRESTATIE', 'SELL': 'VERKOPEN'}
        analyst_recommendation = advies_map.get(raw_rec, 'HOUDEN')
        num_analysts = info.get('numberOfAnalystOpinions', 0)
        
        profit_margin = info.get('profitMargins', 0.0)
        profit_margin_pct = round(profit_margin * 100, 2) if profit_margin else 0.0
        
        revenue_growth = info.get('revenueGrowth', 0.0)
        revenue_growth_pct = round(revenue_growth * 100, 2) if revenue_growth else 0.0
        
        # P/E (Fiyat / Kazanç) en P/B (Piyasa Değeri / Defter Değeri)
        pe_ratio = info.get('trailingPE')
        pe_val = round(pe_ratio, 2) if pe_ratio and pe_ratio > 0 else 0.0
        
        pb_ratio = info.get('priceToBook')
        pb_val = round(pb_ratio, 2) if pb_ratio and pb_ratio > 0 else 0.0
        
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
            
        if raw_rec in ['BUY', 'STRONG_BUY']:
            points += 1.0
            reasons.append(f"Analisten consensus: {analyst_recommendation} (+1.0p)")
        elif raw_rec in ['UNDERPERFORM', 'SELL']:
            points -= 1.0
            reasons.append(f"Analisten consensus: {analyst_recommendation} (-1.0p)")
            
        score = round(min(10.0, max(1.0, points)), 1)
        
        if len(hist) >= 14:
            atr = float((hist['High'] - hist['Low']).rolling(14).mean().iloc[-1])
        else:
            atr = price * 0.03
        
        toekomst_outlook = f"Winstmarge: {profit_margin_pct}%. Omzetgroei j-o-j: {revenue_growth_pct}%. Koersdoel analisten: ₺{target_mean if target_mean else 'N.B.'}."

        stock_data = {
            "Ticker": ticker, 
            "Bedrijf": name, 
            "Prijs (TRY)": round(price, 2), 
            "RSI": round(rsi, 1),
            "Cijfer": score, 
            "P/E (FK)": pe_val,
            "P/B (PD/DD)": pb_val,
            "Winstmarge %": profit_margin_pct,
            "Omzetgroei %": revenue_growth_pct,
            "Koersdoel (₺)": round(target_mean, 2) if target_mean else 0.0,
            "Advies": analyst_recommendation,
            "Analisten": num_analysts,
            "Res1": r1, 
            "Sup1": s1, 
            "StopLoss": round(price - atr, 2),
            "Doel": round(price + (1.5 * atr), 2), 
            "Toekomst Outlook": toekomst_outlook,
            "Onderbouwing": ", ".join(reasons)
        }
        return stock_data

    except Exception:
        return None

st.title("🧠 BIST Quant Trading Bot & Fundamentele Suite")
st.markdown("---")

dev_risk, mkt_ret, usd_try, global_warnings = analyze_macro_and_global_news()

col1, col2 = st.columns(2)
with col1:
    st.metric(label="💱 USD/TRY Koers", value=f"₺{usd_try:.2f}", delta="Devaluatie-risico actief" if dev_risk else "Stabiel")
with col2:
    st.metric(label="📈 BIST 100 (3m Rendement)", value=f"{mkt_ret}%")

st.markdown("### 🌍 Geopolitieke Risico's & Wereldnieuws Scanner")
if global_warnings:
    for warning in global_warnings[:3]:
        st.warning(f"⚠️ **Geopolitiek signaal:** {warning}")
else:
    st.success("🛡️ Geen directe
