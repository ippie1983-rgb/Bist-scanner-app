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
        num_analysts = info.get('numberOfAnalystOpinions', 
