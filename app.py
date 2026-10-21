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
                    title = item.find('title').text if item.find('title') is not None else ""
                    if title:
                        headlines.append(title)
                        title_lower = title.lower()
                        if any(k in title_lower for k in POSITIVE_KEYWORDS):
                            pos_hits += 1
                        if any(k in title_lower for k in NEGATIVE_KEYWORDS
