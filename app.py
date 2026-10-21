import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import urllib.request
import xml.etree.ElementTree as ET

st.set_page_config(page_title="BIST Ultiem Quant & Fundamenteel Rapport", layout="wide")

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
        
    # BIST 100 index analyse (XU100.IS)
    xu100_close = 11000.0
    xu100_low_52w = 8500.0
    xu100_high_52w = 11500.0
    mkt_ret = 0.0
    try:
        ticker_xu = yf.Ticker("XU100.IS")
        hist_xu = ticker_xu.history(period="1y")
        if not hist_xu.empty and 'Close' in hist_xu.columns:
            xu100_close = float(hist_xu['Close'].iloc[-1])
            xu100_low_52w = float(hist_xu['Low'].min())
            xu100_high_52w = float(hist_xu['High'].max())
            if len(hist_xu) >= 60:
                mkt_ret = round(float((hist_xu['Close'].iloc[-1] - hist_xu['Close'].iloc[-60]) / hist_xu['Close'].iloc[-60]) * 100, 2)
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
                    global_warnings.append(title.text)
    except Exception:
        pass

    dev_risk = usd_try > 48.0
    return dev_risk, mkt_ret, usd_try, xu100_close, xu100_low_52w, xu100_high_52w, global_warnings

def analyze_stock(ticker, dev_risk, usd_try):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="3mo")
        if hist is None or hist.empty or len(hist) < 14: 
            return None
        
        info = stock.info or {}
        name = str(info.get('longName') or ticker)
        price = float(hist['Close'].iloc[-1])
        price_usd = price / usd_try if usd_try > 0 else 0
        
        target_mean = info.get('targetMeanPrice')
        raw_rec = str(info.get('recommendationKey', 'hold')).upper()
        
        advies_map = {
            'BUY': 'KOPEN',
            'STRONG_BUY': 'STERK KOPEN',
            'HOLD': 'HOUDEN',
            'UNDERPERFORM': 'ONDERPRE
