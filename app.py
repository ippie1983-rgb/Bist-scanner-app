import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import urllib.request
import xml.etree.ElementTree as ET

# Pagina-configuratie
st.set_page_config(
    page_title="BIST 100 Quant Scanner",
    page_icon="📈",
    layout="wide"
)

# 1. Watchlist & Trefwoorden (Volledig en correct afgesloten)
WATCHLIST = [
    'GARAN.IS', 'AKBNK.IS', 'EREGL.IS', 'THYAO.IS', 
    'TUPRS.IS', 'KCHOL.IS', 'SAHOL.IS', 'BIMAS.IS',
    'YKBNK.IS', 'ISCTR.IS', 'ASELS.IS', 'SISE.IS', 'MGROS.IS'
]

EXPORT_BUFFERS = ['THYAO.IS', 'EREGL.IS', 'SISE.IS', 'TUPRS.IS', 'ASELS.IS']

POSITIVE
