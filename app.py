import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="BIST Quant Scanner Beast Pro", page_icon="🏆", layout="centered")

SECTORS = {
    "Alle Aandelen": ['GARAN.IS', 'YKBNK.IS', 'AKBNK.IS', 'ISCTR.IS', 'EREGL.IS', 'THYAO.IS', 'TUPRS.IS', 'SAHOL.IS', 'KCHOL.IS', 'BIMAS.IS', 'ASELS.IS', 'SISE.IS', 'MGROS.IS'],
    "Banken": ['GARAN.IS', 'YKBNK.IS', 'AKBNK.IS', 'ISCTR.IS'],
    "Export & Industrie": ['EREGL.IS', 'THYAO.IS', 'TUPRS.IS', 'SISE.IS', 'KCHOL.IS', 'SAHOL.IS'],
    "Defensie & Retail": ['ASELS.IS', 'BIMAS.IS', 'MGROS.IS']
}

@st.cache_data(ttl=900)
def get_macro():
    usd_try = 49.50
    try:
        df_fx = yf.Ticker("USDTRY=X").history(period="5d")
        if not df_fx.empty:
            usd_try = float(df_fx['Close'].iloc[-1])
    except:
        pass

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
            r1 = round((2 * p) - l,
