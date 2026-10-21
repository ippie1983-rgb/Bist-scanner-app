import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import urllib.request
import xml.etree.ElementTree as ET

st.set_page_config(page_title="BIST Quant Scanner Beast Pro", page_icon="🏆", layout="centered")

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

    brent_p, brent_chg = 75.0, 0.0
    try:
        df_oil = yf.Ticker("BZ=F").history(period="5d")
        if not df_oil.empty and len(df_oil) > 1:
            brent_p = float(df_oil['Close'].iloc[-1])
            brent_chg = round(((brent_p - float(df_oil['Close'].iloc[0])) / float(df_oil['Close'].iloc[0])) * 100, 2)
    except: pass

    oil_shock = brent_chg > 4.0

    return {
        "usd": usd_try, "usd_chg": usd_chg, "xu100": xu100_p, "xu100_r3m": xu100_r3m, "xu100_r1d": xu100_r1d,
        "brent": brent_p, "brent_chg": brent_chg, "s1": s1, "s2": s2, "r1": r1, "r2": r2, 
        "dev": usd_try > 48.0, "oil_shock": oil_shock
    }

# --- ACTUELE MACRO- & MSCI-INELICHTINGEN ---
@st.cache_data(ttl=900)
def get_current_market_intelligence(macro):
    intel = []
    
    # Brandstof & Olie schok analyse
    if macro['oil_shock']:
        intel.append("🚨 **Brandstof- & Olieprijsschok:** Stijgende olieprijzen verhogen de inflatiedruk in Turkije en drukken op de brandstofkosten van luchtvaart (THYAO) en raffinagemarges, terwijl energie-exporteurs profiteren.")
    else:
        intel.append(f"🛢️ **Energie-markt (Brent ${macro['brent']:.2f}):** Olieprijzen tonen een stabiel patroon; geen directe acute energiecrisis voor de BIST 100.")

    # MSCI & Buitenlandse Fondsen
    intel.append("🌐 **MSCI & Internationale Kapitaalstromen:** Buitenlandse investeringsbanken letten scherp op de MSCI Turkey Index wegingen. Instroom van westerse fondsen hangt af van het voortzetten van het orthodoxe monetaire beleid door de Turkse centrale bank (TCMB).")

    # Politiek & Schandalen
    intel.append("🏛️ **Politiek & Economische Hervormingen:** Regeringsverklaringen over begrotingsdiscipline en juridische stappen voor meer markttransparantie zorgen voor een buffer tegen externe volatiliteit.")
    
    return intel

@st.cache_data(ttl=900)
def analyze(ticker, macro):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="3mo")
        if hist.empty or len(hist) < 15: return None
        
        info = stock.info or {}
        name = str(info.get('longName') or ticker)
        price = float(hist['Close'].iloc[-1])
        
        sma
