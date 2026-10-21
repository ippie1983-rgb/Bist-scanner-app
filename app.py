import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import urllib.request
import xml.etree.ElementTree as ET

st.set_page_config(page_title="BIST Quant Scanner", page_icon="🏆", layout="centered")

WATCHLIST = [
    'GARAN.IS', 'YKBNK.IS', 'AKBNK.IS', 'ISCTR.IS',
    'EREGL.IS', 'THYAO.IS', 'TUPRS.IS', 'SAHOL.IS',
    'KCHOL.IS', 'BIMAS.IS', 'ASELS.IS', 'SISE.IS', 'MGROS.IS'
]

# --- MACRO, BIST 100 INDEX & INDEX STEUN/WEERSTAND ---
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
            
            # Index Pivot Points berekenen voor de BIST 100 in zijn geheel
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

# --- NEDERLANDSTALIGE NIEUWS- EN GEOPOLITIEK FILTER ---
@st.cache_data(ttl=900)
def get_dutch_geopolitical_news():
    feeds = [
        ("Turkije Economie", "https://www.dailysabah.com/rssFeed/economy"),
        ("Wereld & Geopolitiek", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114")
    ]
    geo_items, risk_items, gen_items = [], [], []
    
    vertalingen = {
        "central bank": "centrale bank", "inflation": "inflatie", "interest rate": "rente",
        "middle east": "midden-oosten", "oil": "olie", "energy": "energie", "defense": "defensie",
        "sanctions": "sancties", "investigation": "onderzoek", "fine": "boete", "crisis": "crisis",
        "growth": "groei", "profit": "winst", "export": "export", "lira": "lira", "stocks": "aandelen"
    }

    geo_keys = ['turkey', 'türkiye', 'central bank', 'tcmb', 'inflation', 'rate', 'middle east', 'oil', 'energy', 'defense', 'nato', 'export', 'lira', 'bist']
    risk_keys = ['scandal', 'spk', 'investigation', 'fine', 'fraud', 'sanction', 'conflict', 'war', 'crisis']

    for src, url in feeds:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                root = ET.fromstring(resp.read())
                for item in root.findall('.//item')[:8]:
                    title = item.find('title').text if item.find('title') is not None else ""
                    if not title:
                        continue
                    
                    t_nl = title
                    for eng, nld in vertalingen.items():
                        t_nl = t_nl.replace(eng, nld).replace(eng.capitalize(), nld.capitalize())

                    tl = t_nl.lower()
                    if any(k in tl for k in risk_keys):
                        risk_items.append(f"🚨 **Marktrisico ({src}):** {t_nl}")
                    elif any(k in tl for k in geo_keys):
                        geo_items.append(f"🌍 **Geopolitiek & Macro ({src}):** {t_nl}")
                    else:
                        gen_items.append(f"📰 **Beursnieuws ({src}):** {t_nl}")
        except:
            continue
            
    if not risk_items and not geo_items:
        geo_items.append("🌍 **Geopolitieke Status:** Geen directe conflicten of economische schokken gedetecteerd die invloed hebben op de BIST 100.")

    return risk_items[:4], geo_items[:5], gen_items[:4]

@st.cache_data
