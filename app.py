import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import urllib.request
import xml.etree.ElementTree as ET

# Pagina-configuratie
st.set_page_config(
    page_title="BIST 100 Pro Quant Scanner",
    page_icon="🚀",
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
                    title_elem = item.find('title')
                    title = title_elem.text if title_elem is not None and title_elem.text else ""
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

# 4. Technische, MACD & Uitputtingsanalyse per Aandeel
@st.cache_data(ttl=900)
def analyze_stock(ticker, dev_risk, mkt_ret):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="3mo")
        if hist is None or hist.empty or len(hist) < 30:
            return None

        info = stock.info or {}
        name = str(info.get('longName') or ticker.replace('.IS', ''))
        price = float(hist['Close'].iloc[-1])

        # Daytrading Pivot Points
        h = float(hist['High'].iloc[-2])
        l = float(hist['Low'].iloc[-2])
        c = float(hist['Close'].iloc[-2])
        pivot = (h + l + c) / 3
        r1 = round((2 * pivot) - l, 2)
        s1 = round((2 * pivot) - h, 2)

        upside_to_r1 = round(((r1 - price) / price) * 100, 2)

        sma10 = float(hist['Close'].rolling(10).mean().iloc[-1])
        sma50 = float(hist['Close'].rolling(min(50, len(hist))).mean().iloc[-1])
        
        delta = hist['Close'].diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss
        rsi_series = 100 - (100 / (1 + rs))
        
        clean_rsi = rsi_series.dropna()
        if not clean_rsi.empty:
            rsi = float(clean_rsi.iloc[-1])
        else:
            rsi = 50.0

        exp12 = hist['Close'].ewm(span=12, adjust=False).mean()
        exp26 = hist['Close'].ewm(span=26, adjust=False).mean()
        macd_line = exp12 - exp26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        macd_val = float(macd_line.iloc[-1])
        signal_val = float(signal_line.iloc[-1])
        macd_bullish = macd_val > signal_val

        stock_ret_3m = round(float((price - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100, 2)
        rel_strength = round(stock_ret_3m - mkt_ret, 2)

        points = 4.0
        reasons = []

        if price > sma10:
            points += 1.0
            reasons.append("Koers boven 10-daags SMA (+1.0p)")
        if price > sma50:
