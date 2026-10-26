import os
import json
import math
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

# ==============================================================================
# BIST 30 SCANNER ULTIMATE 5.7 — 8-AGENT ENTERPRISE COMMAND CENTER (DEEL 1)
# VOLLEDIGE UITVOERING: ALLE 30 BIST 30 AANDELEN, GEEN AFKORTINGEN, DATA ENGINE
# ==============================================================================

st.set_page_config(
    page_title="BIST 30 Scanner Ultimate 5.7 — 8-Agent Command Center",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS OVERRIDE: VOORKOM AFKAPPEN VAN GETALLEN (GEEN '11,1...' MEER) ---
st.markdown(
    """
    <style>
    [data-testid="stMetricValue"] {
        font-size: 1.35rem !important;
        white-space: normal !important;
        overflow: visible !important;
        text-overflow: clip !important;
        word-break: break-word !important;
        line-height: 1.25 !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.90rem !important;
        white-space: normal !important;
        overflow: visible !important;
    }
    [data-testid="stMetricDelta"] {
        font-size: 0.82rem !important;
        white-space: normal !important;
    }
    .full-num-card {
        background-color: rgba(240, 242, 246, 0.65);
        border-left: 4px solid #1f77b4;
        padding: 12px 14px;
        border-radius: 6px;
        margin-bottom: 10px;
    }
    .full-num-title {
        font-size: 0.82rem;
        color: #555;
        font-weight: 600;
        margin-bottom: 4px;
    }
    .full-num-val {
        font-size: 1.20rem;
        font-weight: 700;
        color: #111;
        word-break: break-all;
    }
    .full-num-sub {
        font-size: 0.78rem;
        color: #333;
        margin-top: 4px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ==============================================================================
# 1. VOLLEDIGE BIST 30 (EXACT 30 HOOFDAANDELEN), SECTOREN & BEDRIJFSPROFIELEN
# ==============================================================================

WATCHLIST = [
    # 1 - 10
    "AKBNK.IS", "ALARK.IS", "ARCLK.IS", "ASELS.IS", "ASTOR.IS",
    "BIMAS.IS", "DOAS.IS", "EKGYO.IS", "ENKAI.IS", "EREGL.IS",
    # 11 - 20
    "FROTO.IS", "GARAN.IS", "HEKTS.IS", "ISCTR.IS", "KCHOL.IS",
    "KONTR.IS", "KOZAL.IS", "KRDMD.IS", "MGROS.IS", "PETKM.IS",
    # 21 - 30
    "PGSUS.IS", "SAHOL.IS", "SASA.IS", "SISE.IS", "TAVHL.IS",
    "TCELL.IS", "THYAO.IS", "TOASO.IS", "TUPRS.IS", "YKBNK.IS"
]

SECTOR_MAP = {
    "AKBNK.IS": "Banken & Financieel",
    "ALARK.IS": "Conglomeraat, Energie & Landbouw",
    "ARCLK.IS": "Consumentenelektronica & Export",
    "ASELS.IS": "Defensie & Hoogtechnologie",
    "ASTOR.IS": "Energietechniek & Transformatoren",
    "BIMAS.IS": "Supermarkten & Defensieve Retail",
    "DOAS.IS": "Automotive Distributie",
    "EKGYO.IS": "Vastgoed (GYO)",
    "ENKAI.IS": "Bouw, Energie & Valutareserves",
    "EREGL.IS": "Staal & Zware Industrie",
    "FROTO.IS": "Automotive & Europese Export",
    "GARAN.IS": "Banken & Financieel",
    "HEKTS.IS": "Agrochemie & Landbouw",
    "ISCTR.IS": "Banken & Financieel",
    "KCHOL.IS": "Conglomeraat & Holding",
    "KONTR.IS": "Technologie, Ruimtevaart & Energieopslag",
    "KOZAL.IS": "Goud & Edelmetalen",
    "KRDMD.IS": "Staal & Spoorwegindustrie",
    "MGROS.IS": "Supermarkten & Voedingsretail",
    "PETKM.IS": "Petrochemie & Basisindustrie",
    "PGSUS.IS": "Luchtvaart & Toerisme (Harde Valuta)",
    "SAHOL.IS": "Conglomeraat & Holding",
    "SASA.IS": "Polyester, Polymeren & Petrochemie",
    "SISE.IS": "Glas, Chemie & Wereldwijde Export",
    "TAVHL.IS": "Luchthavenexploitatie (Harde Valuta)",
    "TCELL.IS": "Telecom, Data & FinTech",
    "THYAO.IS": "Luchtvaart & Vracht (Harde Valuta)",
    "TOASO.IS": "Automotive Productie",
    "TUPRS.IS": "Energie & Raffinage",
    "YKBNK.IS": "Banken & Financieel"
}

BIST30_PROFILES = {
    "AKBNK.IS": "Grootbank met sterke kapitaalbuffer (CAR) en hoge liquiditeit in de BIST 30.",
    "ALARK.IS": "Gediversifieerde holding met focus op elektriciteit, energie en grootschalige agrotechniek.",
    "ARCLK.IS": "Internationale witgoed- en elektronicaproducent (o.a. Beko/Whirlpool Europa) met hoge exportomzet.",
    "ASELS.IS": "Marktleider in Turkse defensie-elektronica, radar, communicatie en lange-termijn staatsorders in USD/EUR.",
    "ASTOR.IS": "Grote producent van hoogspanningstransformatoren en schakelapparatuur met sterke exportgroei.",
    "BIMAS.IS": "Grootste discount-supermarktketen van Turkije; sterk inflatiebestendig door hoge omloopsnelheid.",
    "DOAS.IS": "Exclusieve distributeur van o.a. Volkswagen, Audi, Porsche en Skoda in Turkije.",
    "EKGYO.IS": "Grootste vastgoedontwikkelaar (GYO) van Turkije; sterk gevoelig voor renteverlagingen van de TCMB.",
    "ENKAI.IS": "Internationaal bouw- en energieconcern met een miljardenbuffer aan netto kas in harde valuta (USD).",
    "EREGL.IS": "Grootste vlakstaalproducent van Turkije; productprijzen zijn direct gekoppeld aan mondiale USD-staalprijzen.",
    "FROTO.IS": "Joint venture met Ford; grootste commerciële voertuigenexporteur van Turkije met cost-plus EUR-contracten.",
    "GARAN.IS": "Toonaangevende particuliere en zakelijke bank (meerderheidsbelang BBVA) met sterke rentemarges.",
    "HEKTS.IS": "Producent van gewasbescherming, zaden en meststoffen (OYAK-groep); herstructurerings- en schuldverlagingsfokus.",
    "ISCTR.IS": "Grootste private bank van Turkije met brede industriële deelnemingen (o.a. Şişecam).",
    "KCHOL.IS": "Grootste industriële en financiële holding van Turkije (energie, auto's, banken, duurzame goederen).",
    "KONTR.IS": "Hoogtechnologisch ingenieursbedrijf actief in energieopslag, satellieten en elektrificatie.",
    "KOZAL.IS": "Goudmijnbedrijf zonder financiële schulden; profiteert direct van een stijgende goudprijs in USD en TRY.",
    "KRDMD.IS": "Geïntegreerde producent van langstaal en spoorrails; profiteert van infrastructuur- en wederopbouwprojecten.",
    "MGROS.IS": "Toonaangevende supermarktketen met sterke vrije kasstroom, netto kaspositie en groeiende online-omzet.",
    "PETKM.IS": "Enige geïntegreerde petrochemische producent in Turkije (SOCAR-groep); afhankelijk van nafta-ethyleen spreads.",
    "PGSUS.IS": "Snelgroeiende low-cost luchtvaartmaatschappij met een van de hoogste EBITDA-marges en harde-valuta-inkomsten.",
    "SAHOL.IS": "Grote holding met kernposities in bankwezen (Akbank), energie (Enerjisa), cement en retail.",
    "SASA.IS": "Grote producent van polyestervezels, filamenten en PTA; heeft zware kapitaalinvesteringen afgerond.",
    "SISE.IS": "Wereldspeler in vlakglas, verpakkingsglas en natriumcarbonaat (soda ash) met meer dan 60% internationale omzet.",
    "TAVHL.IS": "Exploitant van internationale luchthavens (Aéroports de Paris-groep) met inkomsten in EUR en USD.",
    "TCELL.IS": "Marktleider in mobiele telecommunicatie, glasvezel, datacenters en digitale betaaldiensten (Paycell).",
    "THYAO.IS": "Turkish Airlines; wereldwijde luchtvaart- en vrachtreus waarbij ruim 85% van de omzet in harde valuta binnenkomt.",
    "TOASO.IS": "Autofabrikant (Koç & Stellantis samenwerking) gericht op personen- en lichte bedrijfswagens.",
    "TUPRS.IS": "Grootste olieraffinaderij van Turkije; sterke balans, hoge dividendcapaciteit en USD-gekoppelde raffinagemarges.",
    "YKBNK.IS": "Grote commerciële bank binnen de Koç-groep met sterke positie in creditcards en bedrijfsfinanciering."
}

HARD_CURRENCY_EXPORTERS = {
    "ARCLK.IS", "ASELS.IS", "ASTOR.IS", "ENKAI.IS", "EREGL.IS",
    "FROTO.IS", "KCHOL.IS", "KONTR.IS", "KOZAL.IS", "PGSUS.IS",
    "SISE.IS", "TAVHL.IS", "THYAO.IS", "TOASO.IS", "TUPRS.IS"
}

NEWS_URLS = [
    ("Google Nieuws — Turkije Economie & BIST 30", "https://news.google.com/rss/search?q=Turkiye+ekonomi+Borsa+Istanbul+BIST30&hl=tr&gl=TR&ceid=TR:tr"),
    ("Google Nieuws — SPK, Boetes & Onderzoeken", "https://news.google.com/rss/search?q=SPK+fon+borsa+inceleme+ceza&hl=tr&gl=TR&ceid=TR:tr"),
    ("Google Nieuws — KAP & Kwartaalcijfers", "https://news.google.com/rss/search?q=BIST+KAP+sirket+bilanco+kar+zarar+temettu&hl=tr&gl=TR&ceid=TR:tr"),
    ("Google Nieuws — TCMB Rente & Inflatie", "https://news.google.com/rss/search?q=TCMB+faiz+enflasyon+Merkez+Bankasi&hl=tr&gl=TR&ceid=TR:tr")
]

POSITIVE_KEYWORDS = ["yatırım", "ihale", "sözleşme", "anlaşma", "temettü", "kar payı", "geri alım", "kapasite", "büyüme", "rekor kar", "beklenti üstü", "sipariş", "ihracat", "investering", "contract", "dividend", "inkoop", "uitbreiding", "winststijging", "onay", "yeni iş", "bedelsiz", "artış", "güçlü bilanço", "ihale kazandı"]
NEGATIVE_KEYWORDS = ["zarar", "ceza", "soruşturma", "inceleme", "spk", "borç", "üretim durdu", "grev", "beklenti altı", "düşüş", "kriz", "iptal", "dava", "uyarı", "verlies", "boete", "onderzoek", "schuld", "winstwaarschuwing", "sanctie", "oorlog", "gözaltı", "tutuklama", "kayyum", "manipülasyon", "tedbir", "iflas"]

# ==============================================================================
# 2. STRICTE FORMATTERINGSHULPFUNCTIES (VOLLEDIGE GETALLEN ZONDER AFKORTING)
# ==============================================================================

def safe_float(value):
    try:
        if value is None: return None
        val = float(value)
        return val if np.isfinite(val) else None
    except (TypeError, ValueError):
        return None

def format_full_number(val, decimals=2, currency="₺"):
    v = safe_float(val)
    if v is None: return "Niet beschikbaar"
    prefix = f"{currency}" if currency else ""
    if decimals <= 0: return f"{prefix}{v:,.0f}".replace(",", ".")
    fmt_str = f"{{:,.{decimals}f}}"
    parts = fmt_str.format(v).split(".")
    return f"{prefix}{parts[0].replace(',', '.')},{parts[1]}"

def format_full_integer(val, currency=""):
    v = safe_float(val)
    if v is None: return "Niet beschikbaar"
    prefix = f"{currency}" if currency else ""
    return f"{prefix}{v:,.0f}".replace(",", ".")

def format_full_percentage(val, decimals=2, include_plus=False):
    v = safe_float(val)
    if v is None: return "Niet beschikbaar"
    sign = "+" if (include_plus and v > 0) else ""
    parts = f"{v:,.{decimals}f}".split(".")
    return f"{sign}{parts[0].replace(',', '.')},{parts[1]}%"

def format_full_ratio(val, decimals=2, suffix="x"):
    v = safe_float(val)
    if v is None or v <= 0: return "Niet beschikbaar"
    parts = f"{v:,.{decimals}f}".split(".")
    return f"{parts[0].replace(',', '.')},{parts[1]}{suffix}"

def render_full_card(title, value_str, subtitle_str="", border_color="#1f77b4"):
    st.markdown(
        f"""<div class="full-num-card" style="border-left-color: {border_color};">
            <div class="full-num-title">{title}</div>
            <div class="full-num-val">{value_str}</div>
            <div class="full-num-sub">{subtitle_str}</div>
        </div>""",
        unsafe_allow_html=True
    )

# ==============================================================================
# 3. DATA OPHAALFUNCTIES, TECHNISCHE INDICATOREN & STEUN/WEERSTAND (S1-S3 / R1-R3)
# ==============================================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_history(ticker, period="1y", interval="1d"):
    try:
        df = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=True)
        return df.dropna(subset=["Close", "High", "Low"]) if (df is not None and not df.empty) else pd.DataFrame()
    except Exception: return pd.DataFrame()

def calculate_rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi = rsi.where(loss != 0, 100.0)
    flat = (gain == 0) & (loss == 0)
    return rsi.where(~flat, 50.0).fillna(50.0)

def calculate_bollinger_bands(close, period=20, std_dev=2.0):
    sma = close.rolling(period).mean()
    std = close.rolling(period).std()
    return sma, sma + (std_dev * std), sma - (std_dev * std)

def calculate_sr_levels(hist):
    if hist is None or hist.empty or len(hist) < 5: return None
    close = hist["Close"].astype(float)
    high = hist["High"].astype(float)
    low = hist["Low"].astype(float)
    volume = hist["Volume"].astype(float) if "Volume" in hist else pd.Series(dtype=float)
    price = safe_float(close.iloc[-1])
    if price is None or price <= 0: return None

    window = hist.tail(min(20, len(hist) - 1)) if len(hist) > 2 else hist
    h, l = safe_float(window["High"].max()) or price, safe_float(window["Low"].min()) or price
    c = safe_float(close.iloc[-2]) if len(close) >= 2 else price
    pivot = (h + l + c) / 3.0
    rng = max(h - l, price * 0.02)

    r1, r2, r3 = pivot + (0.382 * rng), pivot + (0.618 * rng), pivot + (1.000 * rng)
    s1, s2, s3 = max(0.01, pivot - (0.382 * rng)), max(0.01, pivot - (0.618 * rng)), max(0.01, pivot - (1.000 * rng))

    sma20, sma50 = safe_float(close.rolling(20).mean().iloc[-1]), safe_float(close.rolling(50).mean().iloc[-1])
    sma200 = safe_float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None

    if sma20 and sma50:
        if price > sma20 > sma50: trend = "Sterk opwaarts"
        elif price > sma20: trend = "Herstellend / licht opwaarts"
        elif price < sma20 < sma50: trend = "Neerwaarts"
        else: trend = "Zijwaarts / gemengd"
    else: trend = "Onvoldoende historie"

    vol_avg_20, vol_latest, vol_ratio = None, None, None
    if not volume.empty and len(volume) >= 5:
        vol_avg_20 = safe_float(volume.tail(20).mean())
        vol_latest = safe_float(volume.iloc[-1])
        if vol_avg_20 and vol_avg_20 > 0 and vol_latest is not None:
            vol_ratio = vol_latest / vol_avg_20

    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    atr = safe_float(tr.rolling(14).mean().iloc[-1]) or (price * 0.03)
    atr_pct = (atr / price) * 100.0 if price > 0 else 0.0

    dist_s1_pct, dist_r1_pct = ((price - s1) / price) * 100.0 if price > 0 else 0.0, ((r1 - price) / price) * 100.0 if price > 0 else 0.0

    rel_parts = [f"Trend: {trend}"]
    if vol_ratio is not None:
        rel_parts.append(f"Hoog volume ({format_full_number(vol_ratio, 2, '')}x)" if vol_ratio >= 1.3 else f"Laag volume ({format_full_number(vol_ratio, 2, '')}x)" if vol_ratio <= 0.7 else f"Normaal volume ({format_full_number(vol_ratio, 2, '')}x)")
    rel_parts.append(f"Volatiliteit (ATR): {format_full_percentage(atr_pct, 2)}")

    return {
        "Price": price, "Pivot": pivot, "R1": r1, "R2": r2, "R3": r3, "S1": s1, "S2": s2, "S3": s3,
        "Dist_S1_Pct": dist_s1_pct, "Dist_R1_Pct": dist_r1_pct, "SMA20": sma20, "SMA50": sma50, "SMA200": sma200,
        "Trend": trend, "Vol_Latest": vol_latest, "Vol_Avg20": vol_avg_20, "Vol_Ratio": vol_ratio, "ATR": atr, "ATR_Pct": atr_pct, "Relevantie": " · ".join(rel_parts)
    }

@st.cache_data(ttl=900, show_spinner=False)
def get_macro_data():
    out = {"usd_try": None, "usd_try_change_1m": None, "eur_try": None, "dev_risk": False, "xu030_price": None, "xu030_return_1m": None, "xu030_return_3m": None, "xu030_sr": None, "xu100_price": None, "xu100_return_1m": None, "xu100_return_3m": None, "xu100_sr": None, "xu100_trend_positive": False, "gold_usd": None, "brent_usd": None, "vix": None}
    try:
        fx = get_history("USDTRY=X", "3mo")
        if not fx.empty:
            v = safe_float(fx["Close"].iloc[-1])
            out["usd_try"] = v
            if len(fx) >= 22:
                pv = safe_float(fx["Close"].iloc[-22])
                if v and pv and pv > 0: out["usd_try_change_1m"] = ((v / pv) - 1.0) * 100.0
            if v and (v > 42.0 or (out["usd_try_change_1m"] and out["usd_try_change_1m"] > 2.5)): out["dev_risk"] = True
    except: pass

    try:
        m30 = get_history("XU030.IS", "1y")
        if len(m30) >= 5:
            c30 = m30["Close"].astype(float)
            out["xu030_price"] = safe_float(c30.iloc[-1])
            if len(c30) >= 22: out["xu030_return_1m"] = float((c30.iloc[-1] / c30.iloc[-22] - 1.0) * 100.0)
            out["xu030_return_3m"] = float((c30.iloc[-1] / c30.iloc[max(0, len(c30) - 64)] - 1.0) * 100.0)
            out["xu030_sr"] = calculate_sr_levels(m30)
    except: pass

    try:
        m100 = get_history("XU100.IS", "1y")
        if len(m100) >= 5:
            c100 = m100["Close"].astype(float)
            out["xu100_price"] = safe_float(c100.iloc[-1])
            if len(c100) >= 22: out["xu100_return_1m"] = float((c100.iloc[-1] / c100.iloc[-22] - 1.0) * 100.0)
            out["xu100_return_3m"] = float((c100.iloc[-1] / c100.iloc[max(0, len(c100) - 64)] - 1.0) * 100.0)
            sr = calculate_sr_levels(m100)
            out["xu100_sr"] = sr
            if sr and sr["Trend"] in ["Sterk opwaarts", "Herstellend / licht opwaarts"]: out["xu100_trend_positive"] = True
    except: pass
    
    for k, s in [("eur_try", "EURTRY=X"), ("gold_usd", "GC=F"), ("brent_usd", "BZ=F"), ("vix", "^VIX")]:
        try:
            d = get_history(s, "1mo")
            if not d.empty: out[k] = safe_float(d["Close"].iloc[-1])
        except: pass
    return out

@st.cache_data(ttl=900, show_spinner=False)
def get_quarterly_and_balance_metrics(ticker):
    q_data = {"last_quarter_date": "Niet beschikbaar", "q_rev_full": None, "q_net_full": None, "qoq_rev_growth": None, "qoq_net_growth": None, "total_debt_full": None, "total_cash_full": None, "net_debt_full": None}
    try:
        t_obj = yf.Ticker(ticker)
        q_inc = t_obj.quarterly_income_stmt
        if q_inc is not None and not q_inc.empty:
            c = q_inc.columns
            q_data["last_quarter_date"] = str(c[0])[:10]
            rk = [k for k in q_inc.index if "Total Revenue" in str(k) or "Operating Revenue" in str(k)]
            nk = [k for k in q_inc.index if "Net Income" in str(k)]
            if rk:
                r0 = safe_float(q_inc.loc[rk[0], c[0]])
                q_data["q_rev_full"] = r0
                if len(c) >= 2:
                    r1 = safe_float(q_inc.loc[rk[0], c[1]])
                    if r0 is not None and r1 and r1 > 0: q_data["qoq_rev_growth"] = ((r0 / r1) - 1.0) * 100.0
            if nk:
                n0 = safe_float(q_inc.loc[nk[0], c[0]])
                q_data["q_net_full"] = n0
                if len(c) >= 2:
                    n1 = safe_float(q_inc.loc[nk[0], c[1]])
                    if n0 is not None and n1 and abs(n1) > 0: q_data["qoq_net_growth"] = ((n0 - n1) / abs(n1)) * 100.0

        q_bal = t_obj.quarterly_balance_sheet
        if q_bal is not None and not q_bal.empty:
            bc = q_bal.columns
            dk = [k for k in q_bal.index if "Total Debt" in str(k)]
            ck = [k for k in q_bal.index if "Cash And Cash Equivalents" in str(k) or "End Cash Position" in str(k)]
            if dk: q_data["total_debt_full"] = safe_float(q_bal.loc[dk[0], bc[0]])
            if ck: q_data["total_cash_full"] = safe_float(q_bal.loc[ck[0], bc[0]])
            if q_data["total_debt_full"] is not None and q_data["total_cash_full"] is not None:
                q_data["net_debt_full"] = q_data["total_debt_full"] - q_data["total_cash_full"]
    except: pass
    return q_data

def classify_headline(title):
    t_low = title.lower()
    p_hits = sum(1 for w in POSITIVE_KEYWORDS if w in t_low)
    n_hits = sum(1 for w in NEGATIVE_KEYWORDS if w in t_low)
    if p_hits > 0 and n_hits == 0: return "Positief"
    if n_hits > 0 and p_hits == 0: return "Negatief"
    return "Onduidelijk / Te controleren"

@st.cache_data(ttl=900, show_spinner=False)
def get_news():
    items = []
    for s, url in NEWS_URLS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=7) as resp:
                root = ET.fromstring(resp.read())
            for item in root.findall(".//item")[:10]:
                t = item.findtext("title")
                l = item.findtext("link")
                d = item.findtext("pubDate")
                if t: items.append({"Bron": s, "Signaal": classify_headline(t), "Titel": t, "Datum": d or "", "Link": l or ""})
        except: continue
    return pd.DataFrame(items).drop_duplicates(subset=["Titel"]).head(45) if items else pd.DataFrame(columns=["Bron", "Signaal", "Titel", "Datum", "Link"])

@st.cache_data(ttl=900, show_spinner=False)
def get_stock_news(ticker, company_name):
    query = urllib.parse.quote(f"{ticker.replace('.IS', '')} OR \"{company_name[:15] if company_name else ticker.replace('.IS', '')}\" KAP hisse bilanço temettü")
    url = f"https://news.google.com/rss/search?q={query}&hl=tr&gl=TR&ceid=TR:tr"
    pos, neg, unc = [], [], []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            root = ET.fromstring(response.read())
        for item in root.findall(".//item")[:8]:
            t = item.findtext("title")
            if t:
                cat = classify_headline(t)
                entry = {"titel": t, "datum": (item.findtext("pubDate") or "")[:16], "link": item.findtext("link") or ""}
                if cat == "Positief": pos.append(entry)
                elif cat == "Negatief": neg.append(entry)
                else: unc.append(entry)
    except: pass
    return pos, neg, unc

@st.cache_data(ttl=900, show_spinner=False)
def call_gemini_kap_agent(ticker, company, fund_summary, q_metrics, headlines_tuple, usd_try, api_key):
    if not api_key or not api_key.strip(): return None
    try:
        headlines_text = "\n".join([f"- {h}" for h in headlines_tuple]) if headlines_tuple else "Geen recente headlines."
        prompt = f"""
Je bent een senior kwantitatief analist voor Borsa Istanbul (BIST 30). Analyseer {company} ({ticker}) in JSON format met velden: sentiment_label (Sterk Positief/Positief/Neutraal/Negatief/Sterk Negatief), score_adjustment (-1.5 tot +1.5), kwartaal_analyse (NL), kap_duiding (NL), belangrijkste_katalysator (NL), grootste_risico (NL).
USD/TRY koers: {usd_try}, Fundamenteel: {json.dumps(fund_summary)}, Kwartaal: {json.dumps(q_metrics)}, Headlines:\n{headlines_text}
"""
        req = urllib.request.Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={urllib.parse.quote(api_key.strip())}",
            data=json.dumps({"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}}).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            return json.loads(json.loads(resp.read().decode("utf-8"))["candidates"][0]["content"]["parts"][0]["text"])
    except: return None
# ==============================================================================
# 4. DE 8 VOLLEDIG ZELFSTANDIGE AUTONOME AI-AGENTS (BIST 30 ENTERPRISE)
# ==============================================================================

def agent_1_multi_timeframe_quant(ticker, hist_daily, sr_info):
    """
    AGENT 1: Technische Quant & Multi-Timeframe Momentum Agent.
    Analyseert Dagelijkse én Wekelijkse trend, SMA20/50/200, RSI(14), MACD, Bollinger Bands en Volume.
    Inclusief Sharpe Momentum (Risico-gecorrigeerd rendement).
    """
    close = hist_daily["Close"].astype(float)
    price = safe_float(close.iloc[-1])
    sma20 = sr_info["SMA20"] if sr_info else safe_float(close.rolling(20).mean().iloc[-1])
    sma50 = sr_info["SMA50"] if sr_info else safe_float(close.rolling(50).mean().iloc[-1])
    sma200 = sr_info["SMA200"] if sr_info else (safe_float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None)

    rsi_series = calculate_rsi(close, 14)
    rsi = safe_float(rsi_series.iloc[-1])

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    macd_hist = macd_line - signal_line

    macd_val = safe_float(macd_line.iloc[-1])
    macd_sig = safe_float(signal_line.iloc[-1])
    macd_h = safe_float(macd_hist.iloc[-1])

    bb_mid, bb_up, bb_low = calculate_bollinger_bands(close, 20, 2.0)
    bb_upper_val = safe_float(bb_up.iloc[-1])
    bb_lower_val = safe_float(bb_low.iloc[-1])

    # Wekelijkse trendcontrole (Multi-Timeframe) via resampling
    weekly_bullish = False
    try:
        w_close = close.resample("W").last().dropna()
        if len(w_close) >= 10:
            w_sma10 = safe_float(w_close.rolling(10).mean().iloc[-1])
            if w_sma10 and price > w_sma10:
                weekly_bullish = True
    except Exception:
        pass

    points = 0.0
    reasons = []

    if sma20 is not None:
        if price > sma20:
            points += 1.8
            reasons.append(f"Koers ({format_full_number(price, 2)}) boven SMA20 ({format_full_number(sma20, 2)})")
        else:
            reasons.append(f"Koers ({format_full_number(price, 2)}) onder SMA20 ({format_full_number(sma20, 2)})")

    if sma50 is not None:
        if price > sma50:
            points += 1.8
            reasons.append(f"Koers boven SMA50 ({format_full_number(sma50, 2)})")
        else:
            reasons.append(f"Koers onder SMA50 ({format_full_number(sma50, 2)})")

    if sma200 is not None:
        if price > sma200:
            points += 1.2
            reasons.append(f"Lange termijn stijgende trend boven SMA200 ({format_full_number(sma200, 2)})")
        else:
            reasons.append(f"Koers noteert onder lange termijn SMA200 ({format_full_number(sma200, 2)})")

    if rsi is not None:
        if 45.0 <= rsi <= 65.0:
            points += 2.0
            reasons.append(f"RSI ({format_full_number(rsi, 1, '')}) in gezonde opwaartse zone")
        elif 30.0 <= rsi < 45.0:
            points += 1.5
            reasons.append(f"RSI ({format_full_number(rsi, 1, '')}) in lage herstelzone")
        elif rsi < 30.0:
            points += 1.0
            reasons.append(f"RSI ({format_full_number(rsi, 1, '')}) oversold — wacht op bodemvorming")
        elif 65.0 < rsi <= 73.0:
            points += 1.2
            reasons.append(f"RSI ({format_full_number(rsi, 1, '')}) toont sterk momentum")
        else:
            reasons.append(f"RSI ({format_full_number(rsi, 1, '')}) hoog — kans op winstnemingen")

    if macd_val is not None and macd_sig is not None:
        if macd_val > macd_sig:
            points += 1.5
            reasons.append(f"MACD ({format_full_number(macd_val, 3, '')}) positief boven signaallijn")
        else:
            reasons.append(f"MACD ({format_full_number(macd_val, 3, '')}) onder signaallijn")

    if weekly_bullish:
        points += 1.0
        reasons.append("Multi-Timeframe bevestiging: Wekelijkse trend is eveneens positief")

    vol_ratio = sr_info["Vol_Ratio"] if sr_info else None
    if vol_ratio is not None and vol_ratio >= 1.25:
        points += 0.7
        reasons.append(f"Handelsvolume ligt {format_full_number(vol_ratio, 2, '')}x boven het 20-daags gemiddelde")

    if bb_lower_val and price <= bb_lower_val * 1.02:
        reasons.append(f"Koers test onderkant Bollinger Band ({format_full_number(bb_lower_val, 2)})")
    elif bb_upper_val and price >= bb_upper_val * 0.98:
        reasons.append(f"Koers test bovenkant Bollinger Band ({format_full_number(bb_upper_val, 2)})")

    tech_score = round(min(10.0, max(1.0, points)), 1)
    return {
        "score": tech_score,
        "rsi": rsi,
        "macd": macd_val,
        "macd_hist": macd_h,
        "weekly_bullish": weekly_bullish,
        "reasons": reasons
    }


def agent_2_fundamental_quarterly_valuation(info, q_metrics):
    """
    AGENT 2: Fundamentele Waardering & Kwartaalcijfers Agent.
    Analyseert P/E (FK), P/B (PD/DD), EV/EBITDA, ROE, Winstmarge, Jaargroei én QoQ Kwartaalgroei.
    """
    pe = safe_float(info.get("trailingPE"))
    forward_pe = safe_float(info.get("forwardPE"))
    pb = safe_float(info.get("priceToBook"))
    ev_ebitda = safe_float(info.get("enterpriseToEbitda"))
    margin = safe_float(info.get("profitMargins"))
    op_margin = safe_float(info.get("operatingMargins"))
    roe = safe_float(info.get("returnOnEquity"))
    rev_growth = safe_float(info.get("revenueGrowth"))
    market_cap = safe_float(info.get("marketCap"))

    points = 0.0
    max_pts = 0.0
    reasons = []

    if pe is not None and pe > 0:
        max_pts += 2.5
        if pe < 8.5:
            points += 2.5
            reasons.append(f"Zeer aantrekkelijke P/E (FK) waardering van {format_full_ratio(pe, 2)}")
        elif pe <= 15.0:
            points += 1.8
            reasons.append(f"Gezonde P/E (FK) waardering van {format_full_ratio(pe, 2)}")
        elif pe <= 22.0:
            points += 1.0
            reasons.append(f"Gemiddelde P/E (FK) waardering van {format_full_ratio(pe, 2)}")
        else:
            reasons.append(f"Hoge P/E (FK) waardering van {format_full_ratio(pe, 2)}")

    if pb is not None and pb > 0:
        max_pts += 2.0
        if pb < 1.3:
            points += 2.0
            reasons.append(f"Lage Koers/Boekwaarde P/B (PD/DD) van {format_full_ratio(pb, 2)}")
        elif pb <= 2.5:
            points += 1.3
            reasons.append(f"Redelijke P/B (PD/DD) van {format_full_ratio(pb, 2)}")
        else:
            reasons.append(f"Stevige P/B (PD/DD) van {format_full_ratio(pb, 2)}")

    if margin is not None:
        max_pts += 2.0
        margin_pct = margin * 100.0
        if margin_pct >= 12.0:
            points += 2.0
            reasons.append(f"Sterke netto winstmarge van {format_full_percentage(margin_pct, 2)}")
        elif margin_pct > 0:
            points += 1.1
            reasons.append(f"Positieve netto winstmarge van {format_full_percentage(margin_pct, 2)}")
        else:
            reasons.append(f"Negatieve winstmarge ({format_full_percentage(margin_pct, 2)})")

    if rev_growth is not None:
        max_pts += 1.5
        rg_pct = rev_growth * 100.0
        if rg_pct >= 15.0:
            points += 1.5
            reasons.append(f"Sterke jaar-op-jaar omzetgroei van {format_full_percentage(rg_pct, 2)}")
        elif rg_pct > 0:
            points += 0.8
            reasons.append(f"Positieve omzetgroei van {format_full_percentage(rg_pct, 2)}")
        else:
            reasons.append(f"Omzetkrimp ({format_full_percentage(rg_pct, 2)})")

    if roe is not None:
        max_pts += 1.0
        roe_pct = roe * 100.0
        if roe_pct >= 20.0:
            points += 1.0
            reasons.append(f"Hoog rendement op eigen vermogen (ROE: {format_full_percentage(roe_pct, 2)})")
        elif roe_pct > 5.0:
            points += 0.5
            reasons.append(f"Positieve ROE ({format_full_percentage(roe_pct, 2)})")

    qoq_net = q_metrics.get("qoq_net_growth")
    if qoq_net is not None:
        max_pts += 1.0
        if qoq_net > 10.0:
            points += 1.0
            reasons.append(f"Kwartaalwinst groeide QoQ met {format_full_percentage(qoq_net, 2, True)}")
        elif qoq_net > 0:
            points += 0.5
            reasons.append(f"Positieve kwartaalwinstontwikkeling ({format_full_percentage(qoq_net, 2, True)})")
        else:
            reasons.append(f"Kwartaalwinst daalde QoQ ({format_full_percentage(qoq_net, 2)})")

    fund_score = round((points / max_pts) * 10.0, 1) if max_pts > 0 else None
    return {
        "score": fund_score,
        "pe": pe,
        "forward_pe": forward_pe,
        "pb": pb,
        "ev_ebitda": ev_ebitda,
        "margin_pct": (margin * 100.0) if margin is not None else None,
        "op_margin_pct": (op_margin * 100.0) if op_margin is not None else None,
        "roe_pct": (roe * 100.0) if roe is not None else None,
        "rev_growth_pct": (rev_growth * 100.0) if rev_growth is not None else None,
        "market_cap_full": market_cap,
        "reasons": reasons
    }


def agent_3_kap_and_news_intelligence(ticker, company, fund_res, q_metrics, macro_info, api_key=None, use_ai=False):
    """
    AGENT 3: KAP-Meldingen, SPK & Bedrijfsnieuws Klassificatie Agent.
    Categoriseert nieuws in Positieve signalen, Negatieve signalen en Te controleren meldingen,
    aangevuld met optionele Gemini AI-duiding.
    """
    pos_news, neg_news, unc_news = get_stock_news(ticker, company)
    headlines_tuple = tuple([n["titel"] for n in (pos_news + neg_news + unc_news)])

    ai_data = None
    if use_ai and api_key:
        fund_summary = {
            "PE": fund_res.get("pe"),
            "PB": fund_res.get("pb"),
            "Winstmarge_pct": fund_res.get("margin_pct"),
            "Omzetgroei_pct": fund_res.get("rev_growth_pct")
        }
        ai_data = call_gemini_kap_agent(
            ticker=ticker,
            company=company,
            fund_summary=fund_summary,
            q_metrics=q_metrics,
            headlines_tuple=headlines_tuple,
            usd_try=macro_info.get("usd_try"),
            api_key=api_key
        )

    if ai_data and safe_float(ai_data.get("score_adjustment")) is not None:
        adjustment = float(np.clip(safe_float(ai_data.get("score_adjustment")), -1.5, 1.5))
        sentiment = str(ai_data.get("sentiment_label", "Neutraal (AI)"))
        summary_reason = f"Gemini AI ({sentiment}): {ai_data.get('kap_duiding', '')}"
    else:
        if len(pos_news) > len(neg_news):
            adjustment = min(0.8, 0.35 * (len(pos_news) - len(neg_news)))
            sentiment = "Positief (KAP/Nieuws)"
            summary_reason = f"{len(pos_news)} positieve KAP/nieuws-signalen tegenover {len(neg_news)} negatieve."
        elif len(neg_news) > len(pos_news):
            adjustment = max(-1.2, -0.45 * (len(neg_news) - len(pos_news)))
            sentiment = "Negatief / Waarschuwing"
            summary_reason = f"Opgelet: {len(neg_news)} negatieve nieuws-/SPK-signalen gedetecteerd."
        else:
            adjustment = 0.0
            sentiment = "Neutraal / Onbeslist"
            summary_reason = f"Geen overwegend positieve of negatieve uitslag ({len(unc_news)} algemene berichten)."

    return {
        "pos_news": pos_news,
        "neg_news": neg_news,
        "unc_news": unc_news,
        "adjustment": round(adjustment, 2),
        "sentiment": sentiment,
        "ai_report": ai_data,
        "reason": summary_reason
    }


def agent_4_macro_fx_devaluation_buffer(ticker, sector, macro_info):
    """
    AGENT 4: Macro, Rente & USD/TRY Devaluatie-Buffer Agent.
    Beoordeelt hoe het BIST 30-aandeel reageert op lira-devaluatie, olieprijzen en het indexklimaat.
    """
    dev_risk = macro_info.get("dev_risk", False)
    is_exporter = ticker in HARD_CURRENCY_EXPORTERS
    bist_pos = macro_info.get("xu100_trend_positive", False)

    adj = 0.0
    reasons = []

    if is_exporter:
        if dev_risk:
            adj += 0.8
            reasons.append("Sterke USD/EUR devaluatie-buffer actief: internationaal verdienmodel beschermt marges")
        else:
            adj += 0.4
            reasons.append("Structurele harde-valuta inkomsten en exportpositie binnen de BIST 30")
    else:
        if dev_risk and sector in ["Vastgoed (GYO)", "Telecom, Data & FinTech"]:
            adj -= 0.3
            reasons.append("Binnenlands lira-verdienmodel is gevoeliger voor valuta- en renteschokken")
        else:
            reasons.append("Binnenlands marktprofiel; volgt lokale Turkse conjunctuur")

    if bist_pos:
        adj += 0.2
        reasons.append("Brede Borsa Istanbul index zit in een ondersteunende opwaartse trend")
    else:
        adj -= 0.2
        reasons.append("Brede Borsa Istanbul index vertoont tegenwind; extra selectiviteit vereist")

    return {
        "adjustment": round(adj, 2),
        "is_exporter": is_exporter,
        "reason": "; ".join(reasons)
    }


def agent_5_debt_liquidity_interest_stress(info, q_metrics):
    """
    AGENT 5: Schuldpositie, Liquiditeit & Turkse Rente-Stresstest Agent.
    Analyseert Debt-to-Equity, Current Ratio, Quick Ratio en Netto Schuld positie.
    """
    debt_to_equity = safe_float(info.get("debtToEquity"))
    current_ratio = safe_float(info.get("currentRatio"))
    quick_ratio = safe_float(info.get("quickRatio"))
    total_debt = q_metrics.get("total_debt_full") or safe_float(info.get("totalDebt"))
    total_cash = q_metrics.get("total_cash_full") or safe_float(info.get("totalCash"))
    net_debt = (total_debt - total_cash) if (total_debt is not None and total_cash is not None) else None

    adj = 0.0
    reasons = []

    if net_debt is not None:
        if net_debt <= 0:
            adj += 0.7
            reasons.append(f"Netto kaspositie (meer cash dan schuld: {format_full_number(abs(net_debt), 0, '₺')} netto kas)")
        else:
            reasons.append(f"Netto schuldpositie van {format_full_number(net_debt, 0, '₺')}")

    if debt_to_equity is not None:
        if debt_to_equity < 45.0:
            adj += 0.5
            reasons.append(f"Lage schuldenratio (Debt/Equity: {format_full_percentage(debt_to_equity, 2)}) — bestand tegen hoge Turkse rente")
        elif debt_to_equity <= 110.0:
            reasons.append(f"Gemiddelde schuldenratio (Debt/Equity: {format_full_percentage(debt_to_equity, 2)})")
        else:
            adj -= 0.8
            reasons.append(f"Hoge schuldenlast (Debt/Equity: {format_full_percentage(debt_to_equity, 2)}) — kwetsbaar voor hoge rentekosten")
    else:
        reasons.append("Geen Debt/Equity ratio beschikbaar (of financiële instelling/bank)")

    if current_ratio is not None:
        if current_ratio >= 1.4:
            adj += 0.3
            reasons.append(f"Sterke kortetermijnliquiditeit (Current Ratio: {format_full_ratio(current_ratio, 2)})")
        elif current_ratio < 1.0:
            adj -= 0.4
            reasons.append(f"Krappe liquiditeit (Current Ratio: {format_full_ratio(current_ratio, 2)})")

    return {
        "adjustment": round(adj, 2),
        "debt_to_equity": debt_to_equity,
        "current_ratio": current_ratio,
        "quick_ratio": quick_ratio,
        "total_debt_full": total_debt,
        "total_cash_full": total_cash,
        "net_debt_full": net_debt,
        "reason": "; ".join(reasons)
    }


def agent_6_insider_buyback_dividend_structure(info, pos_news):
    """
    AGENT 6: Aandeleninkoop (Geri Alım), Dividend (Temettü) & Free-Float Structuur Agent.
    Controleert uitstaande aandelen, free float, dividendrendement en KAP-inkoopmeldingen.
    """
    shares_out = safe_float(info.get("sharesOutstanding"))
    float_shares = safe_float(info.get("floatShares"))
    div_yield = safe_float(info.get("dividendYield"))
    held_insiders = safe_float(info.get("heldPercentInsiders"))

    adj = 0.0
    reasons = []

    free_float_pct = None
    if shares_out and float_shares and shares_out > 0:
        free_float_pct = (float_shares / shares_out) * 100.0
        reasons.append(f"Vrije omloop (Free Float): {format_full_percentage(free_float_pct, 2)} van {format_full_integer(shares_out)} aandelen")
        if 15.0 <= free_float_pct <= 45.0:
            adj += 0.2
            reasons.append("Gezonde institutionele free-float structuur")

    if div_yield is not None and div_yield > 0:
        dy_pct = div_yield * 100.0 if div_yield < 1.0 else div_yield
        if dy_pct >= 3.0:
            adj += 0.3
            reasons.append(f"Aantrekkelijk dividendrendement (Temettü): {format_full_percentage(dy_pct, 2)}")
        else:
            reasons.append(f"Dividendrendement: {format_full_percentage(dy_pct, 2)}")

    buyback_detected = any("geri alım" in n["titel"].lower() or "inkoop" in n["titel"].lower() for n in pos_news)
    if buyback_detected:
        adj += 0.4
        reasons.append("Actief aandeleninkoopprogramma (Geri Alım) gedetecteerd in recente KAP-berichten")

    if held_insiders is not None and held_insiders > 0:
        reasons.append(f"Strategisch/Moedermaatschappij bezit: {format_full_percentage(held_insiders * 100.0, 2)}")

    if not reasons:
        reasons.append("Standaard BIST 30 aandelen- en eigendomsstructuur")

    return {
        "adjustment": round(adj, 2),
        "shares_out_full": shares_out,
        "free_float_pct": free_float_pct,
        "Reason": "; ".join(reasons)
    }


def agent_7_independent_risk_and_factcheck_auditor(tech_res, fund_res, news_res, debt_res):
    """
    AGENT 7: Onafhankelijke Risico-Auditor, Datakwaliteit & Setup Classificeerder.
    Maakt onderscheid tussen een echt koopwaardige herstelkans en een aandeel dat terecht is gedaald.
    """
    t_score = tech_res["score"]
    f_score = fund_res["score"]
    rsi = tech_res["rsi"]
    pos_count = len(news_res["pos_news"])
    neg_count = len(news_res["neg_news"])

    if f_score is not None:
        data_quality = "Volledig (Techniek + Fundamentals + Kwartaaldata)"
        quality_adj = 0.2
    else:
        data_quality = "Beperkt (Alleen techniek; verifieer KAP handmatig)"
        quality_adj = -0.4

    # Onderscheid maken tussen Herstelkans vs. Terecht Gedaald vs. Sterke Trend
    if f_score is not None and f_score >= 6.2 and (rsi is not None and rsi <= 48.0) and neg_count == 0:
        setup_type = "Koopwaardige Herstelkans (Sterk fundament, lage RSI)"
        risk_level = "Gemiddeld (Wacht op steunbevestiging rond S1 of Pivot)"
    elif (f_score is not None and f_score < 4.2) or neg_count > pos_count + 1 or debt_res["adjustment"] <= -0.7:
        setup_type = "Opgelet: Terecht Gedaald / Hoog Risico (Zwakke cijfers of negatief nieuws)"
        risk_level = "Hoog (Vermijd waardevalkuil / Value Trap)"
    elif t_score >= 7.0 and (f_score is None or f_score >= 5.8):
        setup_type = "Sterke Kwaliteitstrend & Positief Momentum"
        risk_level = "Laag tot Gemiddeld (Trendvolgend)"
    else:
        setup_type = "Neutraal / Volgen op BIST 30 Watchlist"
        risk_level = "Gemiddeld"

    audit_notes = [
        f"Datadekking: {data_quality}",
        f"Risicoprofiel: {risk_level}",
        f"Classificatie: {setup_type}"
    ]

    return {
        "setup_type": setup_type,
        "risk_level": risk_level,
        "data_quality": data_quality,
        "quality_adj": quality_adj,
        "reason": " · ".join(audit_notes)
    }


def agent_8_execution_portfolio_telegram_dispatcher(ticker, company, price, sr_info, overall_score, setup_type):
    """
    AGENT 8: Executie, ATR-Risicobeheer & Telegram Alert Agent.
    Berekent exacte instap-, stop-loss- en doelniveaus en bereidt Telegram-notificaties voor.
    """
    atr = sr_info["ATR"] if sr_info else (price * 0.03)
    s1 = sr_info["S1"] if sr_info else (price - atr)
    r1 = sr_info["R1"] if sr_info else (price + atr)
    r2 = sr_info["R2"] if sr_info else (price + 2.0 * atr)

    atr_stop = max(0.01, price - (1.5 * atr))
    atr_target = price + (2.2 * atr)
    risk_per_share = max(0.01, price - atr_stop)
    reward_per_share = max(0.01, atr_target - price)
    rr_ratio = reward_per_share / risk_per_share if risk_per_share > 0 else 1.0

    alert_msg = None
    if overall_score >= 7.2:
        alert_msg = (
            f"🚨 [BIST 30 TOP SIGNAL] {company} ({ticker}) | "
            f"Score: {format_full_number(overall_score, 1, '')}/10 | "
            f"Setup: {setup_type} | "
            f"Koers: {format_full_number(price, 2)} | "
            f"Steun S1: {format_full_number(s1, 2)} | "
            f"Weerstand R1: {format_full_number(r1, 2)} | "
            f"ATR-Stop: {format_full_number(atr_stop, 2)} | "
            f"ATR-Doel: {format_full_number(atr_target, 2)}"
        )

    return {
        "atr_stop": atr_stop,
        "atr_target": atr_target,
        "rr_ratio": rr_ratio,
        "r2_target": r2,
        "alert_msg": alert_msg
    }


def send_telegram_alert(bot_token, chat_id, message_text):
    """Verstuurt rechtstreeks een Telegram-bericht via de officiële Telegram API."""
    if not bot_token or not chat_id or not message_text:
        return False, "Vul zowel een geldige Telegram Bot Token als Chat ID in."
    try:
        url = f"https://api.telegram.org/bot{bot_token.strip()}/sendMessage"
        payload = urllib.parse.urlencode({
            "chat_id": chat_id.strip(),
            "text": message_text
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, method="POST")
        with urllib.request.urlopen(req, timeout=8) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            if res.get("ok"):
                return True, "Telegram-alert succesvol verzonden!"
            return False, f"Telegram foutmelding: {res}"
    except Exception as e:
        return False, f"Kon Telegram niet bereiken: {e}"


# ==============================================================================
# 5. HOOFD-ANALYSE ENGINE & HISTORISCHE BACKTEST MODULE
# ==============================================================================

def analyze_stock_enterprise(ticker, macro_info, api_key=None, use_ai=False):
    hist = get_history(ticker, "1y")
    if hist.empty or len(hist) < 30:
        return None

    close = hist["Close"].astype(float)
    price = safe_float(close.iloc[-1])
    if price is None or price <= 0:
        return None

    ret_1m = safe_float((price / close.iloc[-22] - 1.0) * 100.0) if len(close) >= 22 else None
    ret_3m = safe_float((price / close.iloc[-64] - 1.0) * 100.0) if len(close) >= 64 else None

    info = {}
    try:
        info = yf.Ticker(ticker).info or {}
    except Exception:
        info = {}

    company = str(info.get("longName") or info.get("shortName") or ticker)
    sector = SECTOR_MAP.get(ticker, str(info.get("sector") or "BIST 30 Kernsector"))
    profile_desc = BIST30_PROFILES.get(ticker, "Hoofdfonds binnen de BIST 30 index op Borsa Istanbul.")

    sr_info = calculate_sr_levels(hist)
    q_metrics = get_quarterly_and_balance_metrics(ticker)

    # Voer alle 8 autonome AI-Agents achter elkaar uit
    a1 = agent_1_multi_timeframe_quant(ticker, hist, sr_info)
    a2 = agent_2_fundamental_quarterly_valuation(info, q_metrics)
    a3 = agent_3_kap_and_news_intelligence(ticker, company, a2, q_metrics, macro_info, api_key, use_ai)
    a4 = agent_4_macro_fx_devaluation_buffer(ticker, sector, macro_info)
    a5 = agent_5_debt_liquidity_interest_stress(info, q_metrics)
    a6 = agent_6_insider_buyback_dividend_structure(info, a3["pos_news"])
    a7 = agent_7_independent_risk_and_factcheck_auditor(a1, a2, a3, a5)

    if a2["score"] is not None:
        base_score = (0.48 * a1["score"]) + (0.52 * a2["score"])
    else:
        base_score = a1["score"] * 0.85

    total_adjustments = (
        a3["adjustment"] +
        a4["adjustment"] +
        a5["adjustment"] +
        a6["adjustment"] +
        a7["quality_adj"]
    )
    overall_score = round(min(10.0, max(1.0, base_score + total_adjustments)), 1)

    a8 = agent_8_execution_portfolio_telegram_dispatcher(
        ticker, company, price, sr_info, overall_score, a7["setup_type"]
    )

    analyst_target = safe_float(info.get("targetMeanPrice"))
    analyst_count = int(info.get("numberOfAnalystOpinions") or 0)
    rec_raw = str(info.get("recommendationKey") or "n.b.").upper()
    rec_map = {
        "STRONG_BUY": "Sterk kopen",
        "BUY": "Kopen",
        "HOLD": "Houden",
        "UNDERPERFORM": "Onderpresteren",
        "SELL": "Verkopen"
    }
    recommendation = rec_map.get(rec_raw, "Niet beschikbaar")
    target_upside = ((analyst_target / price) - 1.0) * 100.0 if (analyst_target and price > 0) else None

    return {
        "Bedrijf": company,
        "Ticker": ticker,
        "Sector": sector,
        "Profiel": profile_desc,
        # Numerieke waarden voor sortering en interne berekening
        "_price_num": price,
        "_total_score_num": overall_score,
        "_tech_score_num": a1["score"],
        "_fund_score_num": a2["score"] if a2["score"] is not None else -1.0,
        "_ret_1m_num": ret_1m if ret_1m is not None else -999.0,
        "_ret_3m_num": ret_3m if ret_3m is not None else -999.0,
        "_s1_num": sr_info["S1"] if sr_info else None,
        "_r1_num": sr_info["R1"] if sr_info else None,
        "_atr_stop_num": a8["atr_stop"],
        "_atr_target_num": a8["atr_target"],
        # Volledig uitgeschreven kolommen (STRIKT GEEN AFKORTINGEN)
        "Type Setup": a7["setup_type"],
        "Totaalscore": format_full_number(overall_score, 1, ""),
        "Technische score": format_full_number(a1["score"], 1, ""),
        "Fundamentele score": format_full_number(a2["score"], 1, "") if a2["score"] is not None else "Niet beschikbaar",
        "Koers (Volledig)": format_full_number(price, 2, "₺"),
        "Rendement 1m": format_full_percentage(ret_1m, 2, True),
        "Rendement 3m": format_full_percentage(ret_3m, 2, True),
        "P/E (FK)": format_full_ratio(a2["pe"], 2),
        "P/B (PD/DD)": format_full_ratio(a2["pb"], 2),
        "Winstmarge": format_full_percentage(a2["margin_pct"], 2),
        "Omzetgroei (j-o-j)": format_full_percentage(a2["rev_growth_pct"], 2, True),
        "Marktkapitalisatie (Volledig)": format_full_number(a2["market_cap_full"], 0, "₺"),
        "Laatste Kwartaal": q_metrics["last_quarter_date"],
        "Kwartaalomzet (Volledig)": format_full_number(q_metrics["q_rev_full"], 0, "₺"),
        "Kwartaal Nettowinst (Volledig)": format_full_number(q_metrics["q_net_full"], 0, "₺"),
        "QoQ Omzetgroei": format_full_percentage(q_metrics["qoq_rev_growth"], 2, True),
        "QoQ Winstgroei": format_full_percentage(q_metrics["qoq_net_growth"], 2, True),
        "Totale Schuld (Volledig)": format_full_number(a5["total_debt_full"], 0, "₺"),
        "Totale Kaspositie (Volledig)": format_full_number(a5["total_cash_full"], 0, "₺"),
        "Netto Schuld (Volledig)": format_full_number(a5["net_debt_full"], 0, "₺"),
        "RSI (14)": format_full_number(a1["rsi"], 1, ""),
        "Trend": sr_info["Trend"] if sr_info else "Onbekend",
        "Laatste Dagvolume (Volledig)": format_full_integer(sr_info["Vol_Latest"]) if sr_info else "Niet beschikbaar",
        "Gemiddeld 20d Volume (Volledig)": format_full_integer(sr_info["Vol_Avg20"]) if sr_info else "Niet beschikbaar",
        "Volume Ratio": format_full_ratio(sr_info["Vol_Ratio"], 2) if (sr_info and sr_info["Vol_Ratio"]) else "Niet beschikbaar",
        "Steun S3": format_full_number(sr_info["S3"], 2, "₺") if sr_info else "Niet beschikbaar",
        "Steun S2": format_full_number(sr_info["S2"], 2, "₺") if sr_info else "Niet beschikbaar",
        "Steun S1": format_full_number(sr_info["S1"], 2, "₺") if sr_info else "Niet beschikbaar",
        "Pivot Punt": format_full_number(sr_info["Pivot"], 2, "₺") if sr_info else "Niet beschikbaar",
        "Weerstand R1": format_full_number(sr_info["R1"], 2, "₺") if sr_info else "Niet beschikbaar",
        "Weerstand R2": format_full_number(sr_info["R2"], 2, "₺") if sr_info else "Niet beschikbaar",
        "Weerstand R3": format_full_number(sr_info["R3"], 2, "₺") if sr_info else "Niet beschikbaar",
        "Afstand tot S1": format_full_percentage(sr_info["Dist_S1_Pct"], 2) if sr_info else "Niet beschikbaar",
        "Afstand tot R1": format_full_percentage(sr_info["Dist_R1_Pct"], 2) if sr_info else "Niet beschikbaar",
        "ATR-Stop (Indicatief)": format_full_number(a8["atr_stop"], 2, "₺"),
        "ATR-Doel (Indicatief)": format_full_number(a8["atr_target"], 2, "₺"),
        "Risk/Reward Ratio": format_full_ratio(a8["rr_ratio"], 2),
        "Analistenadvies": recommendation,
        "Aantal Analisten": str(analyst_count),
        "Analisten Koersdoel": format_full_number(analyst_target, 2, "₺"),
        "Koersdoelruimte": format_full_percentage(target_upside, 2, True),
        "Nieuws Sentiment": a3["sentiment"],
        "Nieuws Balans": f"Positief: {len(a3['pos_news'])} | Negatief: {len(a3['neg_news'])} | Te controleren: {len(a3['unc_news'])}",
        "Datadekking": a7["data_quality"],
        "Risiconiveau": a7["risk_level"],
        "SR_Relevantie": sr_info["Relevantie"] if sr_info else "Niet beschikbaar",
        # Agent-specifieke onderbouwingen & objecten
        "Agent1_Redenen": "; ".join(a1["reasons"]),
        "Agent2_Redenen": "; ".join(a2["reasons"]) if a2["reasons"] else "Geen fundamentele ratio's beschikbaar via feed",
        "Agent3_Redenen": a3["reason"],
        "Agent4_Redenen": a4["reason"],
        "Agent5_Redenen": a5["reason"],
        "Agent6_Redenen": a6["Reason"],
        "Agent7_Redenen": a7["reason"],
        "AI_Rapport": a3["ai_report"],
        "Positief_Nieuws": a3["pos_news"],
        "Negatief_Nieuws": a3["neg_news"],
        "Onduidelijk_Nieuws": a3["unc_news"],
        "Alert_Bericht": a8["alert_msg"]
    }


@st.cache_data(ttl=900, show_spinner=False)
def run_historical_backtest(ticker, holding_days=10):
    """
    Voert een historische backtest uit op de afgelopen 12 maanden voor het gekozen BIST 30-aandeel:
    Koopsignaal wanneer Koers > SMA50 én RSI tussen 35 en 60 kruist (Opwaarts momentum).
    """
    hist = get_history(ticker, "1y")
    if hist.empty or len(hist) < 60:
        return None

    close = hist["Close"].astype(float)
    sma50 = close.rolling(50).mean()
    rsi = calculate_rsi(close, 14)

    trades = []
    i = 50
    while i < len(close) - holding_days:
        c_price = safe_float(close.iloc[i])
        c_sma50 = safe_float(sma50.iloc[i])
        c_rsi = safe_float(rsi.iloc[i])
        prev_rsi = safe_float(rsi.iloc[i - 1])

        if c_price and c_sma50 and c_rsi and prev_rsi:
            if c_price > c_sma50 and 35.0 <= c_rsi <= 60.0 and c_rsi > prev_rsi:
                exit_price = safe_float(close.iloc[i + holding_days])
                if exit_price:
                    ret_pct = ((exit_price / c_price) - 1.0) * 100.0
                    trades.append({
                        "Instapdatum": str(close.index[i])[:10],
                        "Instapkoers": format_full_number(c_price, 2, "₺"),
                        "Uitstapdatum": str(close.index[i + holding_days])[:10],
                        "Uitstapkoers": format_full_number(exit_price, 2, "₺"),
                        "Rendement (%)": format_full_percentage(ret_pct, 2, True),
                        "_ret_num": ret_pct
                    })
                    i += holding_days
                    continue
        i += 1

    if not trades:
        return {"trades_df": pd.DataFrame(), "total_trades": 0, "win_rate": 0.0, "avg_return": 0.0}

    t_df = pd.DataFrame(trades)
    wins = sum(1 for r in trades if r["_ret_num"] > 0)
    win_rate = (wins / len(trades)) * 100.0
    avg_ret = float(np.mean([r["_ret_num"] for r in trades]))

    return {
        "trades_df": t_df.drop(columns=["_ret_num"]),
        "total_trades": len(trades),
        "win_rate": win_rate,
        "avg_return": avg_ret
    }


# ==============================================================================
# 6. STREAMLIT MULTI-TAB ENTERPRISE UI (VOLLEDIGE BIST 30 EDITIE)
# ==============================================================================

st.title("🏛️ BIST 30 Scanner Ultimate 5.7 — 8-Agent Enterprise Command Center")
st.caption(
    "Scant standaard alle 30 hoofdaandelen van de BIST 30 (XU030) · "
    "Volledig uitgeschreven getallen (geen afkortingen of afkappingen) · "
    "S1–S3 & R1–R3 voor BIST 30, BIST 100 én elk aandeel · 8 Zelfstandige AI-Agents."
)

with st.sidebar:
    st.header("⚙️ BIST 30 Scan Instellingen")
    universe = st.multiselect(
        f"BIST 30 Aandelenuniversum ({len(WATCHLIST)} hoofdaandelen):",
        options=WATCHLIST,
        default=WATCHLIST
    )
    sort_choice = st.selectbox(
        "Rangschikken op:",
        [
            "Totaalscore (Hoog naar Laag)",
            "Fundamentele score (Hoog naar Laag)",
            "Technische score (Hoog naar Laag)",
            "Rendement 1m (Hoog naar Laag)",
            "Rendement 3m (Hoog naar Laag)"
        ]
    )
    min_data_filter = st.selectbox(
        "Datadekking filter:",
        ["Alle geanalyseerde BIST 30-aandelen", "Alleen met volledige fundamentele data"]
    )

    st.divider()
    st.header("🤖 Gemini AI-Agent (Optioneel)")
    default_gemini_key = os.environ.get("GEMINI_API_KEY", "")
    if not default_gemini_key:
        try:
            default_gemini_key = st.secrets.get("GEMINI_API_KEY", "")
        except Exception:
            default_gemini_key = ""
    gemini_api_key = st.text_input("Google Gemini API Key:", value=default_gemini_key, type="password")
    use_gemini_ai = st.toggle("Activeer Gemini 2.5 Flash voor KAP/Kwartaalcijfers", value=False)

    st.divider()
    st.header("📲 Telegram Bot (Agent 8)")
    tg_bot_token = st.text_input("Telegram Bot Token:", type="password")
    tg_chat_id = st.text_input("Telegram Chat ID:")

    st.divider()
    if st.button("🔄 Volledige Cache Wissen & Herladen", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

macro = get_macro_data()

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 1. Macro, BIST 30 / 100 & Top 3 Thema's",
    "🏆 2. Volledige BIST 30 Scan & Top 10",
    "📐 3. Steun & Weerstand Matrix (S1-S3 / R1-R3)",
    "🤖 4. Diepte-Analyse per Aandeel (8 Agents)",
    "📰 5. KAP, SPK & Marktnieuws Monitor",
    "💼 6. Portefeuille, Backtest & Telegram Alerts"
])

# ------------------------------------------------------------------------------
# TAB 1: MACRO, BIST 30 & BIST 100 (VOLLEDIGE GETALLEN) & TOP 3 THEMA'S
# ------------------------------------------------------------------------------
with tab1:
    st.subheader("Actueel Macro-, Valuta-, BIST 30 & BIST 100 Overzicht (Volledig Uitgeschreven)")

    mc1, mc2, mc3, mc4 = st.columns(4)
    with mc1:
        render_full_card(
            "USD / TRY Wisselkoers",
            format_full_number(macro["usd_try"], 4, "₺"),
            f"1m verandering: {format_full_percentage(macro['usd_try_change_1m'], 2, True)} · "
            f"{'Devaluatie-buffer ACTIEF' if macro['dev_risk'] else 'Valuta stabiel'}",
            "#d62728" if macro["dev_risk"] else "#2ca02c"
        )
    with mc2:
        render_full_card(
            "EUR / TRY & Grondstoffen",
            format_full_number(macro["eur_try"], 4, "₺"),
            f"Goud (Ons): {format_full_number(macro['gold_usd'], 2, '$')} · Brent Olie: {format_full_number(macro['brent_usd'], 2, '$')}",
            "#1f77b4"
        )
    with mc3:
        render_full_card(
            "BIST 30 (XU030) Laatste Stand",
            format_full_number(macro["xu030_price"], 2, ""),
            f"1m: {format_full_percentage(macro['xu030_return_1m'], 2, True)} · 3m: {format_full_percentage(macro['xu030_return_3m'], 2, True)}",
            "#2ca02c" if macro["xu100_trend_positive"] else "#ff7f0e"
        )
    with mc4:
        render_full_card(
            "BIST 100 (XU100) Laatste Stand",
            format_full_number(macro["xu100_price"], 2, ""),
            f"1m: {format_full_percentage(macro['xu100_return_1m'], 2, True)} · 3m: {format_full_percentage(macro['xu100_return_3m'], 2, True)}",
            "#9467bd"
        )

    st.markdown("### 📐 Steun en Weerstand voor BIST 30 (XU030) & BIST 100 (XU100) (Volledig Uitgeschreven)")
    idx_col1, idx_col2 = st.columns(2)

    with idx_col1:
        st.markdown("#### BIST 30 Index (XU030.IS)")
        if macro["xu030_sr"]:
            b30 = macro["xu030_sr"]
            b30_df = pd.DataFrame([
                {"Niveau": "Weerstand R3", "BIST 30 Stand (Volledig)": format_full_number(b30["R3"], 2, "")},
                {"Niveau": "Weerstand R2", "BIST 30 Stand (Volledig)": format_full_number(b30["R2"], 2, "")},
                {"Niveau": "Weerstand R1", "BIST 30 Stand (Volledig)": format_full_number(b30["R1"], 2, "")},
                {"Niveau": "Pivot Punt (Midden)", "BIST 30 Stand (Volledig)": format_full_number(b30["Pivot"], 2, "")},
                {"Niveau": "Huidige BIST 30 Koers", "BIST 30 Stand (Volledig)": format_full_number(b30["Price"], 2, "")},
                {"Niveau": "Steun S1", "BIST 30 Stand (Volledig)": format_full_number(b30["S1"], 2, "")},
                {"Niveau": "Steun S2", "BIST 30 Stand (Volledig)": format_full_number(b30["S2"], 2, "")},
                {"Niveau": "Steun S3", "BIST 30 Stand (Volledig)": format_full_number(b30["S3"], 2, "")}
            ])
            st.table(b30_df)
            st.caption(f"**BIST 30 Context:** {b30['Relevantie']}")
        else:
            st.info("BIST 30 (XU030.IS) indexdata niet beschikbaar; zie BIST 100 hiernaast.")

    with idx_col2:
        st.markdown("#### BIST 100 Index (XU100.IS)")
        if macro["xu100_sr"]:
            bsr = macro["xu100_sr"]
            b100_df = pd.DataFrame([
                {"Niveau": "Weerstand R3", "BIST 100 Stand (Volledig)": format_full_number(bsr["R3"], 2, "")},
                {"Niveau": "Weerstand R2", "BIST 100 Stand (Volledig)": format_full_number(bsr["R2"], 2, "")},
                {"Niveau": "Weerstand R1", "BIST 100 Stand (Volledig)": format_full_number(bsr["R1"], 2, "")},
                {"Niveau": "Pivot Punt (Midden)", "BIST 100 Stand (Volledig)": format_full_number(bsr["Pivot"], 2, "")},
                {"Niveau": "Huidige BIST 100 Koers", "BIST 100 Stand (Volledig)": format_full_number(bsr["Price"], 2, "")},
                {"Niveau": "Steun S1", "BIST 100 Stand (Volledig)": format_full_number(bsr["S1"], 2, "")},
                {"Niveau": "Steun S2", "BIST 100 Stand (Volledig)": format_full_number(bsr["S2"], 2, "")},
                {"Niveau": "Steun S3", "BIST 100 Stand (Volledig)": format_full_number(bsr["S3"], 2, "")}
            ])
            st.table(b100_df)
            st.caption(f"**BIST 100 Context:** {bsr['Relevantie']}")
        else:
            st.warning("Kon de historische BIST 100 (XU100.IS) data momenteel niet ophalen.")

    st.divider()
    st.subheader("🌍 Geopolitieke & Macro 'Top 3' Thematische Selectie binnen de BIST 30")
    t_col1, t_col2, t_col3 = st.columns(3)
    with t_col1:
        st.info(
            "**1. Luchtvaart & Harde Valuta (THYAO.IS, PGSUS.IS, TAVHL.IS)**\n\n"
            "*Waarom:* Genereren het grootste deel van hun omzet in USD en EUR terwijl een deel van de operationele kosten in TRY ligt. Dit vormt de sterkste natuurlijke buffer tegen lira-devaluatie."
        )
    with t_col2:
        st.info(
            "**2. Energie, Raffinage & Defensie (TUPRS.IS, ASELS.IS, ASTOR.IS)**\n\n"
            "*Waarom:* Beschikken over prijszettingsmacht, strategische staats- en exportorders en directe bescherming bij geopolitieke spanningen of stijgende energieprijzen."
        )
    with t_col3:
        st.info(
            "**3. Conglomeraten & Defensieve Retail (KCHOL.IS, BIMAS.IS, ENKAI.IS)**\n\n"
            "*Waarom:* IJzersterke kasposities en directe doorberekening van voedsel- en goedereninflatie aan de consument zorgen voor stabiele kasstromen tijdens hoge rentes."
        )

# ------------------------------------------------------------------------------
# TAB 2: VOLLEDIGE BIST 30 SCAN, TOP 10 & RANGLIJST
# ------------------------------------------------------------------------------
with tab2:
    st.subheader(f"🏆 Volledige BIST 30 Screening ({len(universe)} Aandelen Geselecteerd) & Bruikbaarder Top 10")
    st.write(
        "De ranglijst combineert voor alle 30 BIST 30-aandelen: "
        "**technische signalen (Agent 1)**, **fundamentele gezondheid & kwartaalcijfers (Agent 2)**, "
        "**positief/negatief KAP-bedrijfsnieuws (Agent 3)**, **de algemene markttrend & valutabuffer (Agent 4)**, "
        "**schuldenstresstest (Agent 5)**, **aandeleninkoop/dividend (Agent 6)** en **datakwaliteit (Agent 7)**."
    )

    if st.button(f"🚀 Start Volledige 8-Agent Scan op {len(universe)} BIST 30 Aandelen", type="primary", use_container_width=True):
        if not universe:
            st.warning("Selecteer minimaal één BIST 30-aandeel in de zijbalk.")
        else:
            scan_rows = []
            prog = st.progress(0, text=f"Initialiseren van de 8 autonome AI-agents voor {len(universe)} BIST 30-aandelen...")
            for idx, ticker in enumerate(universe):
                prog.progress(
                    (idx + 1) / len(universe),
                    text=f"8 Agents analyseren {ticker} ({idx + 1} van {len(universe)})..."
                )
                item_res = analyze_stock_enterprise(
                    ticker,
                    macro,
                    api_key=gemini_api_key,
                    use_ai=use_gemini_ai
                )
                if item_res:
                    scan_rows.append(item_res)
            prog.empty()

            if not scan_rows:
                st.error("Geen bruikbare data ontvangen van Yahoo Finance. Controleer je verbinding.")
            else:
                df_all = pd.DataFrame(scan_rows)
                if min_data_filter == "Alleen met volledige fundamentele data":
                    df_all = df_all[df_all["_fund_score_num"] >= 0]

                sort_col_map = {
                    "Totaalscore (Hoog naar Laag)": "_total_score_num",
                    "Fundamentele score (Hoog naar Laag)": "_fund_score_num",
                    "Technische score (Hoog naar Laag)": "_tech_score_num",
                    "Rendement 1m (Hoog naar Laag)": "_ret_1m_num",
                    "Rendement 3m (Hoog naar Laag)": "_ret_3m_num"
                }
                sort_col = sort_col_map.get(sort_choice, "_total_score_num")
                df_all = df_all.sort_values(by=sort_col, ascending=False).reset_index(drop=True)
                st.session_state["bist_30_results"] = df_all
                st.success(f"Scan succesvol afgerond: {len(df_all)} van de {len(universe)} BIST 30-aandelen volledig geanalyseerd door alle 8 agents.")

    if "bist_30_results" in st.session_state:
        df_res = st.session_state["bist_30_results"]

        st.markdown("### 🥇 Bruikbaarder Top 10 Selectie uit de BIST 30 (Volledig Uitgeschreven Cijfers)")
        top10_cols = [
            "Bedrijf", "Ticker", "Sector", "Type Setup", "Totaalscore",
            "Technische score", "Fundamentele score", "Koers (Volledig)",
            "P/E (FK)", "P/B (PD/DD)", "Steun S1", "Weerstand R1",
            "Nieuws Balans", "Datadekking"
        ]
        st.dataframe(df_res.head(10)[top10_cols], use_container_width=True, hide_index=True)

        st.markdown(f"### 📋 Volledige BIST 30 Ranglijst ({len(df_res)} Aandelen — Geen Afkortingen)")
        full_cols = [
            "Bedrijf", "Ticker", "Sector", "Type Setup", "Totaalscore", "Technische score",
            "Fundamentele score", "Koers (Volledig)", "Rendement 1m", "Rendement 3m",
            "P/E (FK)", "P/B (PD/DD)", "Winstmarge", "Omzetgroei (j-o-j)",
            "Kwartaalomzet (Volledig)", "Kwartaal Nettowinst (Volledig)",
            "RSI (14)", "Steun S1", "Weerstand R1", "Nieuws Sentiment", "Datadekking"
        ]
        st.dataframe(df_res[full_cols], use_container_width=True, hide_index=True)

        export_drop = [c for c in df_res.columns if c.startswith("_") or c in ["Positief_Nieuws", "Negatief_Nieuws", "Onduidelijk_Nieuws", "AI_Rapport"]]
        csv_bytes = df_res.drop(columns=export_drop).to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "📥 Download Volledige BIST 30 Ranglijst als CSV",
            data=csv_bytes,
            file_name=f"bist_30_scanner_5_7_volledig_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
    else:
        st.info(f"Klik op **'Start Volledige 8-Agent Scan op {len(universe)} BIST 30 Aandelen'** hierboven om de volledige BIST 30 te screenen.")

# ------------------------------------------------------------------------------
# TAB 3: STEUN & WEERSTAND MATRIX (S1-S3 & R1-R3 VOOR IEDER BIST 30 AANDEEL)
# ------------------------------------------------------------------------------
with tab3:
    st.subheader("📐 Volledige Steun- en Weerstandsmatrix (S1–S3 & R1–R3) per BIST 30 Aandeel")
    st.write(
        "Overzicht van de exacte eerste, tweede en derde steun- en weerstandsniveaus voor ieder gescand BIST 30-aandeel, "
        "inclusief de procentuele ruimte tot S1/R1, het volledige handelsvolume en de ATR-volatiliteit."
    )
    if "bist_30_results" in st.session_state:
        df_res = st.session_state["bist_30_results"]
        sr_matrix_cols = [
            "Bedrijf", "Ticker", "Koers (Volledig)", "Trend",
            "Steun S3", "Steun S2", "Steun S1", "Pivot Punt",
            "Weerstand R1", "Weerstand R2", "Weerstand R3",
            "Afstand tot S1", "Afstand tot R1",
            "ATR-Stop (Indicatief)", "ATR-Doel (Indicatief)",
            "Laatste Dagvolume (Volledig)", "Volume Ratio"
        ]
        st.dataframe(df_res[sr_matrix_cols], use_container_width=True, hide_index=True)
    else:
        st.info("Start eerst de scan in Tab 2 om de volledige Steun & Weerstand Matrix voor alle 30 aandelen te vullen.")

# ------------------------------------------------------------------------------
# TAB 4: DIEPTE-ANALYSE PER AANDEEL (ALLE 8 AGENTS + VOLLEDIGE TABELLEN)
# ------------------------------------------------------------------------------
with tab4:
    st.subheader("🤖 Diepte-Analyse per BIST 30 Aandeel — Volledige Output van Agent 1 t/m Agent 8")
    if "bist_30_results" not in st.session_state:
        st.info("Start eerst de scan in Tab 2 om de individuele rapporten per BIST 30-aandeel te bekijken.")
    else:
        df_res = st.session_state["bist_30_results"]
        selected_ticker = st.selectbox(
            "Kies een BIST 30-aandeel voor directe focus (of bekijk de uitklapbare rapporten eronder):",
            options=df_res["Ticker"].tolist()
        )

        for _, row in df_res.iterrows():
            is_expanded = (row["Ticker"] == selected_ticker)
            with st.expander(
                f"{row['Bedrijf']} ({row['Ticker']}) — Score: {row['Totaalscore']}/10 — {row['Type Setup']} — Koers: {row['Koers (Volledig)']}",
                expanded=is_expanded
            ):
                if row["Alert_Bericht"]:
                    st.success(row["Alert_Bericht"])

                st.caption(f"**Bedrijfsprofiel ({row['Sector']}):** {row['Profiel']}")

                dc1, dc2, dc3, dc4 = st.columns(4)
                with dc1:
                    render_full_card("Totaalscore & Setup", f"{row['Totaalscore']} / 10", row["Type Setup"], "#1f77b4")
                with dc2:
                    render_full_card("Huidige Koers & RSI(14)", row["Koers (Volledig)"], f"RSI(14): {row['RSI (14)']} · Trend: {row['Trend']}", "#2ca02c")
                with dc3:
                    render_full_card("Waardering P/E & P/B", f"P/E: {row['P/E (FK)']} · P/B: {row['P/B (PD/DD)']}", f"Marge: {row['Winstmarge']} · Groei: {row['Omzetgroei (j-o-j)']}", "#ff7f0e")
                with dc4:
                    render_full_card("Marktkapitalisatie (Volledig)", row["Marktkapitalisatie (Volledig)"], f"Laatste Volume: {row['Laatste Dagvolume (Volledig)']}", "#9467bd")

                st.markdown("#### 1. Steun en Weerstand voor dit Aandeel (S1–S3 & R1–R3 Volledig Uitgeschreven)")
                stock_sr_table = pd.DataFrame([
                    {"Niveau": "Weerstand R3", "Prijs (Volledig)": row["Weerstand R3"], "Betekenis": "Derde mogelijke weerstand"},
                    {"Niveau": "Weerstand R2", "Prijs (Volledig)": row["Weerstand R2"], "Betekenis": "Tweede mogelijke weerstand"},
                    {"Niveau": "Weerstand R1", "Prijs (Volledig)": row["Weerstand R1"], "Betekenis": f"Eerste mogelijke verkoopdruk (Ruimte: {row['Afstand tot R1']})"},
                    {"Niveau": "Pivot Punt", "Prijs (Volledig)": row["Pivot Punt"], "Betekenis": "Centraal technisch kantelpunt"},
                    {"Niveau": "Huidige Koers", "Prijs (Volledig)": row["Koers (Volledig)"], "Betekenis": "Laatste marktprijs"},
                    {"Niveau": "Steun S1", "Prijs (Volledig)": row["Steun S1"], "Betekenis": f"Eerste mogelijke koopinteresse (Afstand: {row['Afstand tot S1']})"},
                    {"Niveau": "Steun S2", "Prijs (Volledig)": row["Steun S2"], "Betekenis": "Tweede mogelijke steun"},
                    {"Niveau": "Steun S3", "Prijs (Volledig)": row["Steun S3"], "Betekenis": "Derde mogelijke steun"},
                    {"Niveau": "ATR-Stop / ATR-Doel", "Prijs (Volledig)": f"Stop: {row['ATR-Stop (Indicatief)']} | Doel: {row['ATR-Doel (Indicatief)']}", "Betekenis": f"Volatiliteitsreferentie (Risk/Reward: {row['Risk/Reward Ratio']})"}
                ])
                st.table(stock_sr_table)
                st.caption(f"**Beoordeling niveau-relevantie:** {row['SR_Relevantie']}")

                st.markdown("#### 2. Volledige Kwartaalcijfers & Balanspositie (Zonder Afkortingen)")
                q_table = pd.DataFrame([
                    {"Financiële Post": "Laatste Kwartaaldatum", "Volledige Waarde": row["Laatste Kwartaal"]},
                    {"Financiële Post": "Kwartaalomzet (Volledig in TRY)", "Volledige Waarde": row["Kwartaalomzet (Volledig)"]},
                    {"Financiële Post": "Kwartaal Nettowinst (Volledig in TRY)", "Volledige Waarde": row["Kwartaal Nettowinst (Volledig)"]},
                    {"Financiële Post": "Kwartaal-op-Kwartaal (QoQ) Omzetgroei", "Volledige Waarde": row["QoQ Omzetgroei"]},
                    {"Financiële Post": "Kwartaal-op-Kwartaal (QoQ) Winstgroei", "Volledige Waarde": row["QoQ Winstgroei"]},
                    {"Financiële Post": "Totale Schuld op Balans (Volledig)", "Volledige Waarde": row["Totale Schuld (Volledig)"]},
                    {"Financiële Post": "Totale Kaspositie / Cash (Volledig)", "Volledige Waarde": row["Totale Kaspositie (Volledig)"]},
                    {"Financiële Post": "Netto Schuldpositie (Schuld min Kas)", "Volledige Waarde": row["Netto Schuld (Volledig)"]}
                ])
                st.table(q_table)

                st.markdown("#### 3. Nieuws en KAP-meldingen voor dit Aandeel (3 Categorieën)")
                if row["AI_Rapport"]:
                    ai_r = row["AI_Rapport"]
                    st.info(
                        f"**🤖 Gemini AI-Agent Duiding ({ai_r.get('sentiment_label')}):**\n\n"
                        f"- **Kwartaal & Fundament:** {ai_r.get('kwartaal_analyse')}\n"
                        f"- **KAP & Nieuws:** {ai_r.get('kap_duiding')}\n"
                        f"- **Belangrijkste Katalysator:** {ai_r.get('belangrijkste_katalysator')}\n"
                        f"- **Grootste Risico:** {ai_r.get('grootste_risico')}"
                    )

                nc1, nc2, nc3 = st.columns(3)
                with nc1:
                    st.markdown("**🟢 Positieve signalen**")
                    st.caption("Investeringen, grote contracten, dividend, inkoop, hogere winst.")
                    if row["Positief_Nieuws"]:
                        for n in row["Positief_Nieuws"]:
                            st.markdown(f"- [{n['titel']}]({n['link']}) ({n['datum']})")
                    else:
                        st.write("Geen recente positieve trefwoorden gevonden.")
                with nc2:
                    st.markdown("**🔴 Negatieve signalen**")
                    st.caption("Winstwaarschuwingen, verliezen, boetes, onderzoeken, schulden.")
                    if row["Negatief_Nieuws"]:
                        for n in row["Negatief_Nieuws"]:
                            st.markdown(f"- [{n['titel']}]({n['link']}) ({n['datum']})")
                    else:
                        st.write("Geen recente negatieve trefwoorden gevonden.")
                with nc3:
                    st.markdown("**⚪ Belangrijk nieuws dat nog niet duidelijk is**")
                    st.caption("Gemengde signalen en meldingen die eerst gecontroleerd moeten worden.")
                    if row["Onduidelijk_Nieuws"]:
                        for n in row["Onduidelijk_Nieuws"]:
                            st.markdown(f"- [{n['titel']}]({n['link']}) ({n['datum']})")
                    else:
                        st.write("Geen overige recente meldingen gevonden.")

                st.markdown("#### 4. Volledige Diagnose van alle 8 Autonome AI-Agents")
                st.write(f"- **Agent 1 (Multi-Timeframe Quant & Technisch):** {row['Agent1_Redenen']}")
                st.write(f"- **Agent 2 (Fundamentele Waardering & Kwartaalcijfers):** {row['Agent2_Redenen']}")
                st.write(f"- **Agent 3 (KAP & Bedrijfsnieuws Intelligence):** {row['Agent3_Redenen']}")
                st.write(f"- **Agent 4 (Macro & USD/TRY Valutabuffer):** {row['Agent4_Redenen']}")
                st.write(f"- **Agent 5 (Schuldpositie, Liquiditeit & Rente-Stresstest):** {row['Agent5_Redenen']}")
                st.write(f"- **Agent 6 (Aandeleninkoop, Dividend & Free-Float):** {row['Agent6_Redenen']}")
                st.write(f"- **Agent 7 (Onafhankelijke Risico-Auditor & Datadekking):** {row['Agent7_Redenen']}")
                st.write(
                    f"- **Agent 8 (Executie & Analistenconsensus):** Advies: {row['Analistenadvies']} "
                    f"({row['Aantal Analisten']} analisten) · Koersdoel: {row['Analisten Koersdoel']} "
                    f"(Ruimte: {row['Koersdoelruimte']})"
                )

# ------------------------------------------------------------------------------
# TAB 5: ALGEMENE KAP, SPK & MARKTNIEUWS MONITOR (3 CATEGORIEËN)
# ------------------------------------------------------------------------------
with tab5:
    st.subheader("📰 Algemene BIST 30, KAP & SPK Nieuwsmonitor (Gecategoriseerd)")
    news_df = get_news()
    if news_df.empty:
        st.info("Nieuwsfeed kon momenteel niet worden opgehaald.")
    else:
        g_col1, g_col2, g_col3 = st.columns(3)
        with g_col1:
            st.markdown("### 🟢 Positieve signalen")
            st.caption("Nieuwe investeringen, grote contracten, hogere winstverwachtingen, dividend, aandeleninkoop en capaciteitsuitbreiding.")
            pos_g = news_df[news_df["Signaal"] == "Positief"]
            if pos_g.empty:
                st.write("Geen uitgesproken positieve koppen in de huidige feed.")
            for _, item in pos_g.iterrows():
                st.markdown(f"- [{item['Titel']}]({item['Link']})  \n  <small>{item['Bron']} · {item['Datum'][:16]}</small>", unsafe_allow_html=True)

        with g_col2:
            st.markdown("### 🔴 Negatieve signalen")
            st.caption("Winstwaarschuwingen, verliezen, onderzoeken, boetes, schuldenproblemen, productieonderbrekingen en tegenvallende cijfers.")
            neg_g = news_df[news_df["Signaal"] == "Negatief"]
            if neg_g.empty:
                st.write("Geen directe negatieve waarschuwingen gedetecteerd.")
            for _, item in neg_g.iterrows():
                st.markdown(f"- [{item['Titel']}]({item['Link']})  \n  <small>{item['Bron']} · {item['Datum'][:16]}</small>", unsafe_allow_html=True)

        with g_col3:
            st.markdown("### ⚪ Nog niet duidelijk / Te controleren")
            st.caption("Gemengde signalen, onbevestigde berichten en meldingen die eerst gecontroleerd moeten worden.")
            unc_g = news_df[news_df["Signaal"] == "Onduidelijk / Te controleren"]
            for _, item in unc_g.iterrows():
                st.markdown(f"- [{item['Titel']}]({item['Link']})  \n  <small>{item['Bron']} · {item['Datum'][:16]}</small>", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# TAB 6: PORTEFEUILLE SIMULATOR, HISTORISCHE BACKTEST & TELEGRAM ALERTS
# ------------------------------------------------------------------------------
with tab6:
    st.subheader("💼 BIST 30 Portefeuille Positiegrootte-Simulator (Volledig Uitgeschreven Bedragen)")
    p_col1, p_col2 = st.columns(2)
    with p_col1:
        total_capital = st.number_input("Totaal Portefeuillekapitaal (in TRY):", min_value=1000.0, value=250000.0, step=10000.0)
    with p_col2:
        risk_pct_per_trade = st.slider("Maximaal verliesrisico per positie (% van kapitaal):", 0.5, 5.0, 1.5, 0.25)

    if "bist_30_results" in st.session_state:
        df_res = st.session_state["bist_30_results"]
        top_picks = df_res.head(10)
        max_loss_try = total_capital * (risk_pct_per_trade / 100.0)

        sim_rows = []
        for _, r in top_picks.iterrows():
            entry_p = r["_price_num"]
            stop_p = r["_atr_stop_num"]
            target_p = r["_atr_target_num"]
            risk_per_sh = max(0.01, entry_p - stop_p)
            shares_by_risk = int(max_loss_try // risk_per_sh)
            max_alloc_shares = int((total_capital * 0.20) // entry_p)
            final_shares = max(1, min(shares_by_risk, max_alloc_shares))
            pos_value = final_shares * entry_p
            max_loss_pos = final_shares * (entry_p - stop_p)
            exp_gain_pos = final_shares * (target_p - entry_p)

            sim_rows.append({
                "Ticker": r["Ticker"],
                "Bedrijf": r["Bedrijf"],
                "Totaalscore": r["Totaalscore"],
                "Huidige Koers": r["Koers (Volledig)"],
                "Aanbevolen Aantal Aandelen": format_full_integer(final_shares),
                "Totale Positiewaarde (Volledig)": format_full_number(pos_value, 2, "₺"),
                "ATR Stop-Loss Koers": r["ATR-Stop (Indicatief)"],
                "Max Verlies bij Stop-Loss (Volledig)": format_full_number(max_loss_pos, 2, "₺"),
                "ATR Doelkoers": r["ATR-Doel (Indicatief)"],
                "Potentiële Winst bij Doel (Volledig)": format_full_number(exp_gain_pos, 2, "₺")
            })
        st.dataframe(pd.DataFrame(sim_rows), use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("📲 Agent 8: Live Telegram Alert Dispatcher")
        alerts_available = [r["Alert_Bericht"] for _, r in df_res.iterrows() if r["Alert_Bericht"]]
        if alerts_available:
            combined_alert_text = "\n\n".join(alerts_available[:10])
            st.code(combined_alert_text, language="text")
            if st.button("📨 Verstuur Top BIST 30 Alerts Nu naar Telegram"):
                ok, msg = send_telegram_alert(tg_bot_token, tg_chat_id, combined_alert_text)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)
        else:
            st.info("Er zijn in de huidige scan geen BIST 30-aandelen met een score van 7,2 of hoger voor een automatische alert.")

    st.divider()
    st.subheader("📈 Historische Signaal-Backtest (Afgelopen 12 Maanden op de BIST 30)")
    bt_col1, bt_col2 = st.columns([2, 1])
    with bt_col1:
        bt_ticker = st.selectbox("Selecteer een BIST 30-aandeel voor historische backtest:", options=WATCHLIST, index=26)
    with bt_col2:
        bt_days = st.slider("Houdperiode per trade (handelsdagen):", 5, 30, 10, 5)

    bt_res = run_historical_backtest(bt_ticker, bt_days)
    if bt_res and bt_res["total_trades"] > 0:
        bc1, bc2, bc3 = st.columns(3)
        with bc1:
            render_full_card("Aantal Historische Signalen", format_full_integer(bt_res["total_trades"]), f"Periode: 12 maanden ({bt_days}d houdperiode)", "#1f77b4")
        with bc2:
            render_full_card("Historische Win-Rate (%)", format_full_percentage(bt_res["win_rate"], 2), "Percentage winstgevende trades", "#2ca02c")
        with bc3:
            render_full_card("Gemiddeld Rendement per Trade", format_full_percentage(bt_res["avg_return"], 2, True), "Exclusief transactiekosten/slippage", "#ff7f0e")
        st.dataframe(bt_res["trades_df"], use_container_width=True, hide_index=True)
    else:
        st.info("Geen historische backtest-signalen gevonden voor deze parameters in het afgelopen jaar.")
