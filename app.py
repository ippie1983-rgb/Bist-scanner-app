import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import urllib.request
import xml.etree.ElementTree as ET

st.set_page_config(page_title="BIST Quant Scanner Pro", page_icon="🏆", layout="centered")

# Uitgebreide Watchlist ingedeeld per sector
SECTORS = {
    "Alle Aandelen (Totaal)": ['GARAN.IS', 'YKBNK.IS', 'AKBNK.IS', 'ISCTR.IS', 'EREGL.IS', 'THYAO.IS', 'TUPRS.IS', 'SAHOL.IS', 'KCHOL.IS', 'BIMAS.IS', 'ASELS.IS', 'SISE.IS', 'MGROS.IS'],
    "Banken & Financiën": ['GARAN.IS', 'YKBNK.IS', 'AKBNK.IS', 'ISCTR.IS'],
    "Export, Industrie & Energie": ['EREGL.IS', 'THYAO.IS', 'TUPRS.IS', 'SISE.IS', 'KCHOL.IS', 'SAHOL.IS'],
    "Defensie, Retail & Consument": ['ASELS.IS', 'BIMAS.IS', 'MGROS.IS']
}

# --- 1. MACRO & BIST 100 INDEX ---
@st.cache_data(ttl=900)
def get_macro_and_bist100():
    usd_try, usd_chg = 49.50, 0.0
    try:
        df_fx = yf.Ticker("USDTRY=X").history(period="5d")
        if not df_fx.empty and len(df_fx) > 1:
            usd_try = float(df_fx['Close'].iloc[-1])
            usd_chg = round(((usd_try - float(df_fx['Close'].iloc[0])) / float(df_fx['Close'].iloc[0])) * 100, 2)
    except:
        pass

    xu100_price, xu100_ret_3m, xu100_ret_1d = 0.0, 0.0, 0.0
    xu100_s1, xu100_s2, xu100_r1, xu100_r2 = 0.0, 0.0, 0.0, 0.0
    try:
        df_xu = yf.Ticker("XU100.IS").history(period="3mo")
        if not df_xu.empty and len(df_xu) > 1:
            xu100_price = round(float(df_xu['Close'].iloc[-1]), 0)
            xu100_ret_3m = round(float((df_xu['Close'].iloc[-1] - df_xu['Close'].iloc[0]) / df_xu['Close'].iloc[0]) * 100, 2)
            xu100_ret_1d = round(float((df_xu['Close'].iloc[-1] - df_xu['Close'].iloc[-2]) / df_xu['Close'].iloc[-2]) * 100, 2)
            
            h, l, c = float(df_xu['High'].iloc[-2]), float(df_xu['Low'].iloc[-2]), float(df_xu['Close'].iloc[-2])
            pivot = (h + l + c) / 3
            xu100_s1 = round((2 * pivot) - h, 0)
            xu100_s2 = round(pivot - (h - l), 0)
            xu100_r1 = round((2 * pivot) - l, 0)
            xu100_r2 = round(pivot + (h - l), 0)
    except:
        pass

    brent_price, brent_chg = 75.0, 0.0
    try:
        df_oil = yf.Ticker("BZ=F").history(period="5d")
        if not df_oil.empty and len(df_oil) > 1:
            brent_price = round(float(df_oil['Close'].iloc[-1]), 2)
            brent_chg = round(((brent_price - float(df_oil['Close'].iloc[0])) / float(df_oil['Close'].iloc[0])) * 100, 2)
    except:
        pass

    return {
        "usd_try": usd_try, "usd_chg": usd_chg,
        "xu100_price": xu100_price, "xu100_ret_3m": xu100_ret_3m, "xu100_ret_1d": xu100_ret_1d,
        "brent_price": brent_price, "brent_chg": brent_chg,
        "xu100_s1": xu100_s1, "xu100_s2": xu100_s2, "xu100_r1": xu100_r1, "xu100_r2": xu100_r2,
        "dev_risk": usd_try > 48.0
    }

# --- 2. LIVE NIEUWS- EN SCHANDAALSCANNER (NEDERLANDSTALIG) ---
@st.cache_data(ttl=900)
def get_dutch_geopolitical_news():
    feeds = [
        ("Turkije & BIST", "https://www.dailysabah.com/rssFeed/economy"),
        ("Wereld & Centrale Banken", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114")
    ]
    
    risk_items, geo_items, gen_items = [], [], []
    vertalingen = {
        "central bank": "centrale bank", "fed": "Federal Reserve", "ecb": "Europese Centrale Bank",
        "inflation": "inflatie", "interest rate": "rentebesluit", "rates": "rente",
        "middle east": "midden-oosten", "oil": "olie", "energy": "energie", "defense": "defensie",
        "sanctions": "sancties", "investigation": "onderzoek (SPK/Justitie)", "
