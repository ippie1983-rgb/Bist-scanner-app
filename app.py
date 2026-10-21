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
            r1 = round((2 * p) - l, 0)
            r2 = round(p + (h - l), 0)
    except:
        pass

    brent_p, brent_chg = 75.0, 0.0
    try:
        df_oil = yf.Ticker("BZ=F").history(period="5d")
        if not df_oil.empty and len(df_oil) > 1:
            brent_p = float(df_oil['Close'].iloc[-1])
            brent_chg = round(((brent_p - float(df_oil['Close'].iloc[0])) / float(df_oil['Close'].iloc[0])) * 100, 2)
    except:
        pass

    return {
        "usd": usd_try, "xu100": xu100_p, "xu100_r3m": xu100_r3m, "xu100_r1d": xu100_r1d,
        "brent": brent_p, "brent_chg": brent_chg, "s1": s1, "s2": s2, "r1": r1, "r2": r2, 
        "dev": usd_try > 48.0
    }

# --- UITGEBREIDE WEKELIJKS INZICHT & PROGNOSES ---
@st.cache_data(ttl=900)
def get_detailed_weekly_outlook(macro):
    huidige_week = (
        "📅 **Verwachting voor deze week:**\n"
        f"• **Marktstatus & Technische Zone:** De BIST 100 noteert rond {macro['xu100']:.0f} punten, manoeuvrerend tussen de harde steun op **{macro['s1']}** en de weerstand op **{macro['r1']}**. "
        "De markt laat momenteel verhoogde volatiliteit zien door liquiditeitsherstructurering bij lokale fondsen en winstnemingen in het bankenveld.\n"
        "• **Korte Termijn Katalysatoren:** Handelen blijft voornamelijk gedreven door dagelijkse macro-data, valutaschommelingen (USD/TRY rond ₺{macro['usd']:.2f}) en institutionele herbalancering richting het einde van de week. "
        "Zolang de steun van S1 standhoudt, is een technische opleving vanaf oververkochte niveaus waarschijnlijk."
    )
    
    volgende_week = (
        "🔮 **Verwachting voor volgende week & Middellange termijn:**\n"
        "• **Macro- en Rente-Agenda:** Volgende week verschuift de focus volledig naar de macro-economische cijfers en eventuele signalen van de centrale banken (TCMB, Fed en ECB) omtrent het rentetraject. "
        "Dit bepaalt direct of de buitenlandse kapitaalinstroom (via MSCI-indexen
