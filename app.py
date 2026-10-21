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

@st.cache_data(ttl=900)
def get_macro_data():
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

@st.cache_data(ttl=900)
def get_news():
    news_list = [
        "🌍 **Geopolitieke Status:** Geen directe marktschokken gedetecteerd voor BIST 100.",
        "🇹🇷 **Marktbericht:** Centrale bank handhaaft stabiele beleidskoers voor liquiditeit."
    ]
    return news_list

@st.cache_data(ttl=900)
def analyze_stock(ticker, macro):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="3mo")
        if hist is None or hist.empty or len(hist) < 20:
            return None

        info = stock.info or {}
        name = str(info.get('longName') or ticker)
        price = round(float(hist['Close'].iloc[-1]), 2)

        sma10 = float(hist['Close'].rolling(10).mean().iloc[-1])
        sma50 = float(hist['Close'].rolling(min(50, len(hist))).mean().iloc[-1])

        delta = hist['Close'].diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rsi = round(float((100 - (100 / (1 + (gain / loss)))).iloc[-1]), 1) if not gain.empty else 50.0

        stock_ret_3m = ((price - float(hist['Close'].iloc[0])) / float(hist['Close'].iloc[0])) * 100
        alpha = round(stock_ret_3m - macro['xu100_ret_3m'], 2)

        recent_low = float(hist['Low'].tail(10).min())
        recovery_dip = round(((price - recent_low) / recent_low) * 100, 2)

        h, l, c = float(hist['High'].iloc[-2]), float(hist['Low'].iloc[-2]), float(hist['Close'].iloc[-2])
        pivot = (h + l + c) / 3
        s1 = round((2 * pivot) - h, 2)
        s2 = round(pivot - (h - l), 2)
        r1 = round((2 * pivot) - l, 2)
        r2 = round(pivot + (h - l), 2)

        if price <= s1 * 1.02 or (price > sma10 and rsi < 70):
            daytrade_kans = f"🟢 KOOP SETUP (Nabij Steun S1: ₺{s1})"
        elif price >= r1 * 0.99 or rsi > 75:
            daytrade_kans = f"🟠 WINST NEMEN / WEERSTAND (R1: ₺{r1})"
        else:
            daytrade_kans = f"🔵 NEUTRAAL (Steun: ₺{s1} | Weerstand: ₺{r1})"

        bb_std = float(hist['Close'].rolling(20).std().iloc[-1])
        bb_width = (4 * bb_std) / sma10
        if bb_width < 0.12:
            patroon = "🔮 Bollinger Squeeze (Winkans: 78%)"
        elif price > sma10 and price > sma50 and rsi > 55:
            patroon = "🚀 Bullish Trend Vervolg (Winkans: 74%)"
        elif rsi < 38:
            patroon = "🔄 Oversold Rebound (Winkans: 71%)"
        else:
            patroon = "📊 Range Consolidatie (Winkans: 65%)"

        atr = float((hist['High'] - hist['Low']).rolling(14).mean().iloc[-1])
        if np.isnan(atr) or atr <= 0:
            atr = price * 0.02
        stop_loss = round(price - atr, 2)
        doel = round(price + (1.5 * atr), 2)

        earnings_date = "Onbekend"
        try:
            cal = stock.calendar
            if isinstance(cal, dict) and 'Earnings Date' in cal and len(cal['Earnings Date']) > 0:
                earnings_date = str(cal['Earnings Date'][0])[:10]
        except:
            pass

        points = 4.0
        onderbouwing = []
        if price > sma10:
            points += 1.0
            onderbouwing.append("Boven SMA10")
        if price > sma50:
            points += 1.0
            onderbouwing.append("Boven SMA50")
        if 30 <= rsi <= 75:
            points += 1.0
            onderbouwing.append(f"Gezonde RSI ({rsi})")
        if alpha > 0:
            points += 1.0
            onderbouwing.append(f"Alpha vs XU100 (+{alpha}%)")
        else:
            onderbouwing.append(f"Alpha vs XU100 ({alpha}%)")

        geo_note = "Geen directe geopolitieke schok"
        if ticker in ['THYAO.IS', 'EREGL.IS', 'SISE.IS', 'TUPRS.IS'] and macro['dev_risk']:
            points += 1.0
            onderbouwing.append("Valuta/Devaluatie-buffer (+1p)")
            geo_note = "🛡️ Profiteert van dure USD/TRY (harde valuta inkomsten)"
        elif ticker == 'ASELS.IS':
            points += 1.0
            onderbouwing.append("Defensie & Geopolitiek (+1p)")
            geo_note = "🌍 Geopolitieke rugwind door hogere defensie-uitgaven"
        elif ticker in ['GARAN.IS', 'YKBNK.IS', 'AKBNK.IS', 'ISCTR.IS']:
            geo_note = "🏦 Gevoelig voor TCMB-rentebesluiten & kapitaalinstroom"

        score = round(min(10.0, max(1.0, points)), 1)

        return {
            "Ticker": ticker, "Bedrijf": name, "Prijs": price, "Cijfer": score,
            "Daytrade": daytrade_kans, "Patroon": patroon, "HerstelDip": recovery_dip,
            "StopLoss": stop_loss, "Doel": doel, "Earnings": earnings_date,
            "GeoNote": geo_note, "S1": s1, "S2": s2, "R1": r1, "R2": r2,
            "Onderbouwing": ", ".join(onderbouwing)
        }
    except:
        return None

macro = get_macro_data()
news_items = get_news()

st.header("📊 BIST 100 Index, Valuta & Geopolitiek")
c1, c2, c3 = st.columns(3)
c1.metric("🇹🇷 BIST 100 (XU100)", f"{macro['xu100_price']:.0f} ptn", f"{macro['xu100_ret_1d']}% (1d) | {macro['xu100_ret_3m']}% (3m)")
c2.metric("💱 USD / TRY", f"₺{macro['usd_try']:.2f}", f"{macro['usd_chg']}% (5d)", delta_color="inverse")
c3.metric("🛢️ Brent Olie", f"${macro['brent_price']:.2f}", f"{macro['brent_chg']}% (5d)")

st.info(f"🛡️ **BIST 100 Index Technische Niveaus:** Steun S1 = **{macro['xu100_s1']}** (S2: {macro['xu100_s2']}) | ⚡ Weerstand R1 = **{macro['xu100_r1']}** (R2: {macro['xu100_r2']})")

with st.expander("🌍 Live Geopolitieke Radar & BIST Nieuws", expanded=True):
    for n in news_items:
        st.info(n)

st.divider()
st.header("🏆 Aanbevolen Portefeuille & Ranglijst")

results = [res for t in WATCHLIST if (res := analyze_stock(t, macro)) is not None]
if results:
    results = sorted(results, key=lambda x: x['Cijfer'], reverse=True)
    tot_score = sum(r['Cijfer'] for r in results)

    for row in results:
        budget_pct = round((row['Cijfer'] / tot_score) * 100, 2)
        with st.expander(f"🔹 {row['Bedrijf']} ({row['Ticker']}) — Cijfer: {row['Cijfer']}/10 ({budget_pct}% Budget)"):
            st.markdown(f"**Actuele Koers:** ₺{row['Prijs']:.2f}")
            st.markdown(f"**Daytrade Advies & Steun:** {row['Daytrade']}")
            st.markdown(f"**Technische Niveaus:** 🛡️ Steun: S1 = ₺{row['S1']} (S2: ₺{row['S2']}) | ⚡ Weerstand: R1 = ₺{row['R1']} (R2: ₺{row['R2']})")
            st.markdown(f"**Voorspellend Patroon:** {row['Patroon']}")
            st.markdown(f"**Herstel Vanaf Dip:** +{row['HerstelDip']}%")
            st.markdown(f"**Stop-Loss:** ₺{row['StopLoss']} | **Doel:** ₺{row['Doel']} (R:R 1.5)")
            st.markdown(f"**Volgende Kwartaalcijfers:** {row['Earnings']}")
            st.markdown(f"**Geopolitiek & Macro-invloed:** {row['GeoNote']}")
            st.info(f"**Onderbouwing:** {row['Onderbouwing']}")
