import os
import json
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

# ==============================================================================
# CONFIGURATIE & SECTOR MAPPING
# ==============================================================================
st.set_page_config(page_title="BIST Scanner 3.5 — Pro Hedgefund Edition", layout="wide")

WATCHLIST = [
    "GARAN.IS", "AKBNK.IS", "YKBNK.IS", "ISCTR.IS", "HALKB.IS", "VAKBN.IS",
    "EREGL.IS", "KRDMD.IS", "THYAO.IS", "PGSUS.IS", "TAVHL.IS",
    "TUPRS.IS", "PETKM.IS", "SISE.IS", "KCHOL.IS", "SAHOL.IS", "BIMAS.IS",
    "MGROS.IS", "TCELL.IS", "TTKOM.IS", "ASELS.IS", "FROTO.IS", "TOASO.IS",
    "ENKAI.IS", "ARCLK.IS", "TTRAK.IS", "AEFES.IS", "ULKER.IS", "DOAS.IS", "EKGYO.IS"
]

SECTOR_MAP = {
    "GARAN.IS": "Banken", "AKBNK.IS": "Banken", "YKBNK.IS": "Banken", "ISCTR.IS": "Banken", "HALKB.IS": "Banken", "VAKBN.IS": "Banken",
    "EREGL.IS": "Staal & Metaal", "KRDMD.IS": "Staal & Metaal",
    "THYAO.IS": "Luchtvaart", "PGSUS.IS": "Luchtvaart", "TAVHL.IS": "Luchtvaart",
    "TUPRS.IS": "Energie", "PETKM.IS": "Energie",
    "SISE.IS": "Conglomeraten", "KCHOL.IS": "Conglomeraten", "SAHOL.IS": "Conglomeraten", "ENKAI.IS": "Conglomeraten",
    "BIMAS.IS": "Retail", "MGROS.IS": "Retail",
    "TCELL.IS": "Telecom", "TTKOM.IS": "Telecom",
    "ASELS.IS": "Defensie/Tech",
    "FROTO.IS": "Automotive", "TOASO.IS": "Automotive", "ARCLK.IS": "Automotive", "TTRAK.IS": "Automotive", "DOAS.IS": "Automotive",
    "AEFES.IS": "Voeding & Dranken", "ULKER.IS": "Voeding & Dranken",
    "EKGYO.IS": "Vastgoed"
}

NEWS_URLS = [
    ("Google Nieuws — Turkije economie", "https://news.google.com/rss/search?q=Turkiye+ekonomi+Borsa+Istanbul&hl=tr&gl=TR&ceid=TR:tr"),
    ("Google Nieuws — SPK en fondsen", "https://news.google.com/rss/search?q=SPK+fon+borsa+inceleme&hl=tr&gl=TR&ceid=TR:tr"),
    ("Google Nieuws — KAP & Bedrijfsresultaten", "https://news.google.com/rss/search?q=BIST+KAP+sirket+bilanco+kar+zarar&hl=tr&gl=TR&ceid=TR:tr"),
    ("Google Nieuws — Geopolitiek & Olie (NL)", "https://news.google.com/rss/search?q=Turkije+economie+geopolitiek+olie&hl=nl&gl=NL&ceid=NL:nl"),
]

POSITIVE_KEYWORDS = ["yatırım", "ihale", "sözleşme", "anlaşma", "temettü", "kar payı", "geri alım", "kapasite", "büyüme", "rekor kar", "beklenti üstü", "sipariş", "ihracat", "investering", "contract", "dividend", "inkoop", "uitbreiding", "winststijging"]
NEGATIVE_KEYWORDS = ["zarar", "ceza", "soruşturma", "inceleme", "spk", "borç", "üretim durdu", "grev", "beklenti altı", "düşüş", "kriz", "iptal", "dava", "uyarı", "verlies", "boete", "onderzoek", "schuld", "winstwaarschuwing", "sanctie", "oorlog"]

def safe_float(v):
    try:
        val = float(v)
        return val if np.isfinite(val) else None
    except:
        return None

@st.cache_data(ttl=300, show_spinner=False)
def get_history(ticker, period="1y", interval="1d"):
    try:
        df = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=True)
        if df is None or df.empty: return pd.DataFrame()
        return df.dropna(subset=["Close", "High", "Low"])
    except:
        return pd.DataFrame()

@st.cache_data(ttl=900, show_spinner=False)
def get_quarterly_metrics(ticker):
    q_data = {"last_quarter_date": None, "q_rev_m": None, "q_net_m": None, "qoq_rev_growth": None, "qoq_net_growth": None}
    try:
        q_inc = yf.Ticker(ticker).quarterly_income_stmt
        if q_inc is not None and not q_inc.empty:
            cols = q_inc.columns
            q_data["last_quarter_date"] = str(cols[0])[:10]
            rev_keys = [k for k in q_inc.index if "Total Revenue" in str(k) or "Operating Revenue" in str(k)]
            net_keys = [k for k in q_inc.index if "Net Income" in str(k)]
            if rev_keys:
                r0 = safe_float(q_inc.loc[rev_keys[0], cols[0]])
                if r0 is not None: q_data["q_rev_m"] = round(r0 / 1e6, 1)
                if len(cols) >= 2:
                    r1 = safe_float(q_inc.loc[rev_keys[0], cols[1]])
                    if r0 is not None and r1 and r1 > 0: q_data["qoq_rev_growth"] = round(((r0 / r1) - 1) * 100, 1)
            if net_keys:
                n0 = safe_float(q_inc.loc[net_keys[0], cols[0]])
                if n0 is not None:
                    q_data["q_net_m"] = round(n0 / 1e6, 1)
                if len(cols) >= 2:
                    n1 = safe_float(q_inc.loc[net_keys[0], cols[1]])
                    if n0 is not None and n1 and abs(n1) > 0:
                        q_data["qoq_net_growth"] = round(((n0 - n1) / abs(n1)) * 100, 1)
    except:
        pass
    return q_data

def calculate_rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.where(loss != 0, 100)
    flat = (gain == 0) & (loss == 0)
    rsi = rsi.where(~flat, 50)
    return rsi.fillna(50)

def calculate_sr_levels(hist):
    if hist is None or hist.empty or len(hist) < 5: return None
    close = hist["Close"].astype(float)
    high = hist["High"].astype(float)
    low = hist["Low"].astype(float)
    volume = hist["Volume"].astype(float) if "Volume" in hist else pd.Series(dtype=float)

    price = safe_float(close.iloc[-1])
    if price is None: return None

    window = hist.tail(min(20, len(hist)-1)) if len(hist) > 2 else hist
    h = safe_float(window["High"].max()) or price
    l = safe_float(window["Low"].min()) or price
    c = safe_float(close.iloc[-2]) if len(close) >= 2 else price

    pivot = (h + l + c) / 3.0
    rng = max(h - l, price * 0.02)

    r1
