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
# BIST 30 SCANNER ULTIMATE 5.8 — 8-AGENT ENTERPRISE COMMAND CENTER
# INCLUSIEF: GOLDEN BOUNCE, ELASTIEK-PENALTY & 1:2 RISK/REWARD DISPATCHER
# ==============================================================================

st.set_page_config(
    page_title="BIST 30 Scanner Ultimate 5.8 — 8-Agent Command Center",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS OVERRIDE: VOORKOM AFKAPPEN VAN GETALLEN ---
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
    "AKBNK.IS", "ALARK.IS", "ARCLK.IS", "ASELS.IS", "ASTOR.IS",
    "BIMAS.IS", "DOAS.IS", "EKGYO.IS", "ENKAI.IS", "EREGL.IS",
    "FROTO.IS", "GARAN.IS", "HEKTS.IS", "ISCTR.IS", "KCHOL.IS",
    "KONTR.IS", "KOZAL.IS", "KRDMD.IS", "MGROS.IS", "PETKM.IS",
    "PGSUS.IS", "SAHOL.IS", "SASA.IS", "SISE.IS", "TAVHL.IS",
    "TCELL.IS", "THYAO.IS", "TOASO.IS", "TUPRS.IS", "YKBNK.IS"
]

SECTOR_MAP = {
    "AKBNK.IS": "Banken & Financieel", "ALARK.IS": "Conglomeraat, Energie & Landbouw",
    "ARCLK.IS": "Consumentenelektronica & Export", "ASELS.IS": "Defensie & Hoogtechnologie",
    "ASTOR.IS": "Energietechniek & Transformatoren", "BIMAS.IS": "Supermarkten & Defensieve Retail",
    "DOAS.IS": "Automotive Distributie", "EKGYO.IS": "Vastgoed (GYO)",
    "ENKAI.IS": "Bouw, Energie & Valutareserves", "EREGL.IS": "Staal & Zware Industrie",
    "FROTO.IS": "Automotive & Europese Export", "GARAN.IS": "Banken & Financieel",
    "HEKTS.IS": "Agrochemie & Landbouw", "ISCTR.IS": "Banken & Financieel",
    "KCHOL.IS": "Conglomeraat & Holding", "KONTR.IS": "Technologie, Ruimtevaart & Energie",
    "KOZAL.IS": "Goud & Edelmetalen", "KRDMD.IS": "Staal & Spoorwegindustrie",
    "MGROS.IS": "Supermarkten & Voedingsretail", "PETKM.IS": "Petrochemie & Basisindustrie",
    "PGSUS.IS": "Luchtvaart (Harde Valuta)", "SAHOL.IS": "Conglomeraat & Holding",
    "SASA.IS": "Polyester, Polymeren & Petrochemie", "SISE.IS": "Glas, Chemie & Export",
    "TAVHL.IS": "Luchthavenexploitatie (Harde Valuta)", "TCELL.IS": "Telecom, Data & FinTech",
    "THYAO.IS": "Luchtvaart & Vracht (Harde Valuta)", "TOASO.IS": "Automotive Productie",
    "TUPRS.IS": "Energie & Raffinage", "YKBNK.IS": "Banken & Financieel"
}

HARD_CURRENCY_EXPORTERS = {
    "ARCLK.IS", "ASELS.IS", "ASTOR.IS", "ENKAI.IS", "EREGL.IS",
    "FROTO.IS", "KCHOL.IS", "KONTR.IS", "KOZAL.IS", "PGSUS.IS",
    "SISE.IS", "TAVHL.IS", "THYAO.IS", "TOASO.IS", "TUPRS.IS"
}

NEWS_URLS = [
    ("Google Nieuws — Turkije Economie", "https://news.google.com/rss/search?q=Turkiye+ekonomi+Borsa+Istanbul+BIST30&hl=tr&gl=TR&ceid=TR:tr"),
    ("Google Nieuws — SPK & Boetes", "https://news.google.com/rss/search?q=SPK+fon+borsa+inceleme+ceza&hl=tr&gl=TR&ceid=TR:tr"),
    ("Google Nieuws — KAP & Bilanço", "https://news.google.com/rss/search?q=BIST+KAP+sirket+bilanco+kar+zarar+temettu&hl=tr&gl=TR&ceid=TR:tr"),
    ("Google Nieuws — TCMB Rente", "https://news.google.com/rss/search?q=TCMB+faiz+enflasyon+Merkez+Bankasi&hl=tr&gl=TR&ceid=TR:tr")
]

POSITIVE_KEYWORDS = ["yatırım", "ihale", "sözleşme", "anlaşma", "temettü", "kar payı", "geri alım", "kapasite", "büyüme", "rekor kar", "beklenti üstü", "sipariş", "ihracat", "investering", "contract", "dividend", "inkoop", "uitbreiding", "winststijging", "onay", "yeni iş", "bedelsiz", "artış", "güçlü bilanço", "ihale kazandı"]
NEGATIVE_KEYWORDS = ["zarar", "ceza", "soruşturma", "inceleme", "spk", "borç", "üretim durdu", "grev", "beklenti altı", "düşüş", "kriz", "iptal", "dava", "uyarı", "verlies", "boete", "onderzoek", "schuld", "winstwaarschuwing", "sanctie", "oorlog", "gözaltı", "tutuklama", "kayyum", "manipülasyon", "tedbir", "iflas"]

# ==============================================================================
# 2. STRICTE FORMATTERINGSHULPFUNCTIES
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
    parts = f"{{:,.{decimals}f}}".format(v).split(".")
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
        </div>""", unsafe_allow_html=True
    )

# ==============================================================================
# 3. DATA OPHAALFUNCTIES, TECHNISCHE INDICATOREN & STEUN/WEERSTAND
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
    return rsi.where(~((gain == 0) & (loss == 0)), 50.0).fillna(50.0)

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
    dist_s1_pct, dist_r1_pct = ((price - s1) / s1) * 100.0 if s1 > 0 else 0.0, ((r1 - price) / price) * 100.0 if price > 0 else 0.0

    return {
        "Price": price, "Pivot": pivot, "R1": r1, "R2": r2, "R3": r3, "S1": s1, "S2": s2, "S3": s3,
        "Dist_S1_Pct": dist_s1_pct, "Dist_R1_Pct": dist_r1_pct, "SMA20": sma20, "SMA50": sma50, "SMA200": sma200,
        "Trend": trend, "Vol_Latest": vol_latest, "Vol_Avg20": vol_avg_20, "Vol_Ratio": vol_ratio, "ATR": atr, "ATR_Pct": atr_pct
    }

@st.cache_data(ttl=900, show_spinner=False)
def get_macro_data():
    out = {"usd_try": None, "usd_try_change_1m": None, "dev_risk": False, "xu030_price": None, "xu030_sr": None, "xu100_price": None, "xu100_sr": None, "xu100_trend_positive": False}
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
        m30 = get_history("XU030.IS", "6mo")
        if len(m30) >= 5:
            out["xu030_price"] = safe_float(m30["Close"].iloc[-1])
            out["xu030_sr"] = calculate_sr_levels(m30)
    except: pass

    try:
        m100 = get_history("XU100.IS", "6mo")
        if len(m100) >= 5:
            out["xu100_price"] = safe_float(m100["Close"].iloc[-1])
            sr = calculate_sr_levels(m100)
            out["xu100_sr"] = sr
            if sr and sr["Trend"] in ["Sterk opwaarts", "Herstellend / licht opwaarts"]: out["xu100_trend_positive"] = True
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
                if len(c) >= 2 and safe_float(q_inc.loc[rk[0], c[1]]):
                    q_data["qoq_rev_growth"] = ((r0 / safe_float(q_inc.loc[rk[0], c[1]])) - 1.0) * 100.0
            if nk:
                n0 = safe_float(q_inc.loc[nk[0], c[0]])
                q_data["q_net_full"] = n0
                if len(c) >= 2 and safe_float(q_inc.loc[nk[0], c[1]]):
                    q_data["qoq_net_growth"] = ((n0 - safe_float(q_inc.loc[nk[0], c[1]])) / abs(safe_float(q_inc.loc[nk[0], c[1]]))) * 100.0

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

def classify_headline(t):
    t_low = t.lower()
    p_hits = sum(1 for w in POSITIVE_KEYWORDS if w in t_low)
    n_hits = sum(1 for w in NEGATIVE_KEYWORDS if w in t_low)
    if p_hits > 0 and n_hits == 0: return "Positief"
    if n_hits > 0 and p_hits == 0: return "Negatief"
    return "Onduidelijk / Te controleren"

@st.cache_data(ttl=900, show_spinner=False)
def get_stock_news(ticker, company_name):
    query = urllib.parse.quote(f"{ticker.replace('.IS', '')} OR \"{company_name[:15] if company_name else ticker.replace('.IS', '')}\" KAP hisse bilanço")
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


# ==============================================================================
# 4. DE 8 AUTONOME AI-AGENTS (MET RISK/REWARD & ELASTIEK-PENALTY LOGICA)
# ==============================================================================

def agent_1_multi_timeframe_quant(ticker, hist_daily, sr_info):
    """
    AGENT 1: Technische Quant, SMA20/50, RSI, MACD en Momentum Analyse.
    INCLUSIEF: Golden Bounce en Elastiek-penalty (Mean Reversion).
    """
    close = hist_daily["Close"].astype(float)
    price = safe_float(close.iloc[-1])
    sma20 = sr_info["SMA20"]
    sma50 = sr_info["SMA50"]
    rsi = safe_float(calculate_rsi(close, 14).iloc[-1])
    vol_ratio = sr_info["Vol_Ratio"]

    dist_s1 = sr_info["Dist_S1_Pct"] / 100.0 if sr_info["S1"] else 0.0
    dist_r1 = sr_info["Dist_R1_Pct"] / 100.0 if sr_info["R1"] else 0.0
    dist_sma20 = (price - sma20) / sma20 if sma20 else 0.0

    points = 0.0
    reasons = []

    # Mean Reversion / Elastiek-effect
    if dist_sma20 > 0.15:
        points -= 1.5
        reasons.append(f"Elastiek-penalty: Koers is {dist_sma20*100:.1f}% te ver verwijderd van SMA20 (Hoge Mean Reversion risico)")
    elif sma20 and price > sma20:
        points += 1.5
        reasons.append(f"Koers noteert veilig boven SMA20 ({format_full_number(sma20, 2)})")

    if sma50 and price > sma50:
        points += 1.5
        reasons.append(f"Koers noteert boven SMA50 ({format_full_number(sma50, 2)})")

    # Zwevend aandeel vs. Golden Bounce
    if dist_s1 > 0.12:
        points -= 1.0
        reasons.append(f"Zwevend aandeel: Koers noteert {dist_s1*100:.1f}% boven steun S1 (hoog terugvalrisico)")
    elif 0 <= dist_s1 <= 0.035 and dist_r1 > 0.06:
        if vol_ratio and vol_ratio >= 1.0:
            points += 2.5
            reasons.append("Golden Bounce: Opvering vanaf steun S1 mét stijgend volume én veel ruimte tot weerstand (+2.5 pt)")
        else:
            points += 1.0
            reasons.append("Steun-bounce zonder volumebevestiging (zwakker koopsignaal)")

    if rsi is not None:
        if 45.0 <= rsi <= 65.0:
            points += 2.0
            reasons.append(f"RSI ({format_full_number(rsi, 1, '')}) in gezonde opwaartse zone")
        elif 30.0 <= rsi < 45.0:
            points += 1.0
            reasons.append(f"RSI ({format_full_number(rsi, 1, '')}) in lage herstelzone")
        elif rsi < 30.0:
            points += 0.5
            reasons.append(f"RSI ({format_full_number(rsi, 1, '')}) oversold — wacht op bodemvorming")
        else:
            reasons.append(f"RSI ({format_full_number(rsi, 1, '')}) oververhit — kans op winstnemingen")

    tech_score = round(min(10.0, max(1.0, points)), 1)
    return {"score": tech_score, "rsi": rsi, "reasons": reasons}

def agent_2_fundamental_quarterly_valuation(info, q_metrics):
    pe = safe_float(info.get("trailingPE"))
    pb = safe_float(info.get("priceToBook"))
    margin = safe_float(info.get("profitMargins"))
    rev_growth = safe_float(info.get("revenueGrowth"))
    market_cap = safe_float(info.get("marketCap"))

    points = 0.0
    max_pts = 0.0
    reasons = []

    if pe and pe > 0:
        max_pts += 2.5
        if pe < 8.5: points += 2.5; reasons.append(f"Zeer aantrekkelijke P/E (FK) van {format_full_ratio(pe, 2)}")
        elif pe <= 15.0: points += 1.5; reasons.append(f"Gezonde P/E (FK) van {format_full_ratio(pe, 2)}")
        else: reasons.append(f"Hoge P/E (FK) waardering van {format_full_ratio(pe, 2)}")

    if pb and pb > 0:
        max_pts += 2.0
        if pb < 1.5: points += 2.0; reasons.append(f"Lage P/B (PD/DD) van {format_full_ratio(pb, 2)}")
        elif pb <= 2.5: points += 1.0; reasons.append(f"Redelijke P/B (PD/DD) van {format_full_ratio(pb, 2)}")
        else: reasons.append(f"Stevige P/B (PD/DD) van {format_full_ratio(pb, 2)}")

    if margin is not None:
        max_pts += 2.0
        if margin >= 0.12: points += 2.0; reasons.append(f"Sterke winstmarge van {format_full_percentage(margin*100, 2)}")
        elif margin > 0: points += 1.0; reasons.append(f"Positieve winstmarge van {format_full_percentage(margin*100, 2)}")
        else: reasons.append("Negatieve winstmarge (verlieslatend)")

    fund_score = round((points / max_pts) * 10.0, 1) if max_pts > 0 else None
    return {"score": fund_score, "pe": pe, "pb": pb, "margin_pct": margin * 100.0 if margin else None, "rev_growth_pct": rev_growth * 100.0 if rev_growth else None, "market_cap_full": market_cap, "reasons": reasons}

def agent_3_kap_and_news_intelligence(ticker, company):
    pos_news, neg_news, unc_news = get_stock_news(ticker, company)
    if len(pos_news) > len(neg_news):
        adj, sent, rsn = min(0.8, 0.35 * (len(pos_news) - len(neg_news))), "Positief (KAP/Nieuws)", f"{len(pos_news)} positieve KAP/nieuws-signalen tegenover {len(neg_news)} negatieve."
    elif len(neg_news) > len(pos_news):
        adj, sent, rsn = max(-1.2, -0.45 * (len(neg_news) - len(pos_news))), "Negatief / Waarschuwing", f"Opgelet: {len(neg_news)} negatieve nieuws-signalen gedetecteerd."
    else:
        adj, sent, rsn = 0.0, "Neutraal / Onbeslist", f"Geen overwegend positieve of negatieve uitslag ({len(unc_news)} overige berichten)."
    return {"pos_news": pos_news, "neg_news": neg_news, "unc_news": unc_news, "adjustment": round(adj, 2), "sentiment": sent, "reason": rsn}

def agent_4_macro_fx_devaluation_buffer(ticker, sector, macro_info):
    dev_risk = macro_info.get("dev_risk", False)
    is_exp = ticker in HARD_CURRENCY_EXPORTERS
    adj, rsn = 0.0, []
    if is_exp:
        if dev_risk: adj += 0.8; rsn.append("Sterke USD/EUR devaluatie-buffer actief: internationaal verdienmodel beschermt marges")
        else: adj += 0.4; rsn.append("Structurele harde-valuta inkomsten en exportpositie")
    else:
        if dev_risk and sector in ["Vastgoed (GYO)", "Telecom, Data & FinTech"]: adj -= 0.4; rsn.append("Binnenlands lira-verdienmodel is gevoeliger voor valuta- en renteschokken")
        else: rsn.append("Binnenlands marktprofiel; volgt lokale Turkse conjunctuur")
    return {"adjustment": round(adj, 2), "reason": "; ".join(rsn)}

def agent_5_debt_liquidity_interest_stress(info, q_metrics):
    dte = safe_float(info.get("debtToEquity"))
    net_debt = (q_metrics.get("total_debt_full") - q_metrics.get("total_cash_full")) if (q_metrics.get("total_debt_full") is not None and q_metrics.get("total_cash_full") is not None) else None
    adj, rsn = 0.0, []
    if net_debt is not None and net_debt <= 0: adj += 0.7; rsn.append(f"Netto kaspositie ({format_full_number(abs(net_debt), 0, '₺')} netto kas)")
    if dte is not None:
        if dte < 45.0: adj += 0.5; rsn.append(f"Lage schuldenratio (D/E: {format_full_percentage(dte, 2)}) — bestand tegen hoge Turkse rente")
        elif dte > 110.0: adj -= 0.8; rsn.append(f"Hoge schuldenlast (D/E: {format_full_percentage(dte, 2)}) — kwetsbaar voor hoge rentekosten")
    return {"adjustment": round(adj, 2), "reason": "; ".join(rsn) if rsn else "Geen schuldgegevens gerapporteerd"}

def agent_6_insider_buyback_dividend_structure(info, pos_news):
    adj, rsn = 0.0, []
    div_yield = safe_float(info.get("dividendYield"))
    if div_yield and div_yield > 0:
        dy_pct = div_yield * 100.0 if div_yield < 1.0 else div_yield
        if dy_pct >= 3.0: adj += 0.3; rsn.append(f"Aantrekkelijk dividendrendement (Temettü): {format_full_percentage(dy_pct, 2)}")
    if any("geri alım" in n["titel"].lower() or "inkoop" in n["titel"].lower() for n in pos_news):
        adj += 0.4; rsn.append("Actief aandeleninkoopprogramma (Geri Alım) gedetecteerd")
    return {"adjustment": round(adj, 2), "Reason": "; ".join(rsn) if rsn else "Standaard BIST 30 eigendomsstructuur"}

def agent_7_independent_risk_and_factcheck_auditor(tech_res, fund_res, news_res, debt_res, sr_info, price):
    t_score, f_score = tech_res["score"], fund_res["score"]
    dist_s1 = sr_info["Dist_S1_Pct"] / 100.0 if sr_info["S1"] else 0.0
    neg_count = len(news_res["neg_news"])

    if f_score is not None: data_quality, quality_adj = "Volledig", 0.2
    else: data_quality, quality_adj = "Beperkt (Geen fundamentele data)", -0.4

    if dist_s1 > 0.12:
        setup_type, risk_level = "Opgelet: Zwevend Aandeel (Te ver van S1)", "Hoog (Wacht op consolidatie of mean reversion)"
    elif f_score and f_score >= 6.2 and tech_res["rsi"] <= 48.0 and neg_count == 0:
        setup_type, risk_level = "Koopwaardige Herstelkans (Lage RSI, Sterk Fundament)", "Gemiddeld (Wacht op steunbevestiging)"
    elif (f_score and f_score < 4.2) or neg_count > 1 or debt_res["adjustment"] <= -0.7:
        setup_type, risk_level = "Opgelet: Terecht Gedaald / Value Trap", "Hoog (Vermijd waardevalkuil)"
    elif t_score >= 7.0 and (f_score is None or f_score >= 5.8):
        setup_type, risk_level = "Sterke Kwaliteitstrend & Positief Momentum", "Laag tot Gemiddeld (Trendvolgend)"
    else:
        setup_type, risk_level = "Neutraal / Volgen op BIST 30 Watchlist", "Gemiddeld"

    return {"setup_type": setup_type, "risk_level": risk_level, "data_quality": data_quality, "quality_adj": quality_adj, "reason": f"Classificatie: {setup_type} | Risicoprofiel: {risk_level}"}

def agent_8_execution_portfolio_telegram_dispatcher(ticker, company, price, sr_info, overall_score, setup_type):
    atr = sr_info["ATR"] if sr_info else (price * 0.03)
    atr_stop = max(0.01, price - (1.5 * atr))
    atr_target = price + (2.2 * atr)
    risk_per_share = max(0.01, price - atr_stop)
    reward_per_share = max(0.01, atr_target - price)
    rr_ratio = reward_per_share / risk_per_share if risk_per_share > 0 else 1.0

    alert_msg = None
    # 1:2 R/R THRESHOLD LOGIC IN AGENT 8
    if overall_score >= 7.2:
        if rr_ratio >= 2.0:
            alert_msg = (
                f"🚨 [BIST 30 TOP SIGNAL] {company} ({ticker}) | "
                f"Score: {format_full_number(overall_score, 1, '')}/10 | "
                f"R/R: {format_full_ratio(rr_ratio, 2)} | "
                f"Setup: {setup_type} | "
                f"Koers: {format_full_number(price, 2)} | "
                f"S1: {format_full_number(sr_info['S1'], 2)} | "
                f"ATR-Stop: {format_full_number(atr_stop, 2)} | "
                f"ATR-Doel: {format_full_number(atr_target, 2)}"
            )
        else:
            # Score is high enough, but R/R is too tight. Suppress the alert.
            pass

    return {"atr_stop": atr_stop, "atr_target": atr_target, "rr_ratio": rr_ratio, "alert_msg": alert_msg}

def analyze_stock_enterprise(ticker, macro_info):
    hist = get_history(ticker, "1y")
    if hist.empty or len(hist) < 30: return None
    close = hist["Close"].astype(float)
    price = safe_float(close.iloc[-1])
    if not price: return None

    info = yf.Ticker(ticker).info or {}
    company = str(info.get("longName") or info.get("shortName") or ticker)
    sector = SECTOR_MAP.get(ticker, "BIST 30 Kernsector")

    sr_info = calculate_sr_levels(hist)
    q_metrics = get_quarterly_and_balance_metrics(ticker)

    a1 = agent_1_multi_timeframe_quant(ticker, hist, sr_info)
    a2 = agent_2_fundamental_quarterly_valuation(info, q_metrics)
    a3 = agent_3_kap_and_news_intelligence(ticker, company)
    a4 = agent_4_macro_fx_devaluation_buffer(ticker, sector, macro_info)
    a5 = agent_5_debt_liquidity_interest_stress(info, q_metrics)
    a6 = agent_6_insider_buyback_dividend_structure(info, a3["pos_news"])
    a7 = agent_7_independent_risk_and_factcheck_auditor(a1, a2, a3, a5, sr_info, price)

    base_score = (0.48 * a1["score"]) + (0.52 * a2["score"]) if a2["score"] is not None else a1["score"] * 0.85
    total_adjustments = a3["adjustment"] + a4["adjustment"] + a5["adjustment"] + a6["adjustment"] + a7["quality_adj"]
    overall_score = round(min(10.0, max(1.0, base_score + total_adjustments)), 1)

    a8 = agent_8_execution_portfolio_telegram_dispatcher(ticker, company, price, sr_info, overall_score, a7["setup_type"])
    analyst_target = safe_float(info.get("targetMeanPrice"))
    target_upside = ((analyst_target / price) - 1.0) * 100.0 if (analyst_target and price > 0) else None

    return {
        "Bedrijf": company, "Ticker": ticker, "Sector": sector,
        "_price_num": price, "_total_score_num": overall_score, "_tech_score_num": a1["score"],
        "_fund_score_num": a2["score"] if a2["score"] is not None else -1.0,
        "_atr_stop_num": a8["atr_stop"], "_atr_target_num": a8["atr_target"],
        "Type Setup": a7["setup_type"],
        "Totaalscore": format_full_number(overall_score, 1, ""),
        "Technische score": format_full_number(a1["score"], 1, ""),
        "Fundamentele score": format_full_number(a2["score"], 1, "") if a2["score"] is not None else "Niet beschikbaar",
        "Koers (Volledig)": format_full_number(price, 2, "₺"),
        "P/E (FK)": format_full_ratio(a2["pe"], 2), "P/B (PD/DD)": format_full_ratio(a2["pb"], 2),
        "RSI (14)": format_full_number(a1["rsi"], 1, ""), "Trend": sr_info["Trend"] if sr_info else "Onbekend",
        "Volume Ratio": format_full_ratio(sr_info["Vol_Ratio"], 2) if (sr_info and sr_info["Vol_Ratio"]) else "Niet beschikbaar",
        "Steun S1": format_full_number(sr_info["S1"], 2, "₺") if sr_info else "Niet beschikbaar",
        "Weerstand R1": format_full_number(sr_info["R1"], 2, "₺") if sr_info else "Niet beschikbaar",
        "ATR-Stop (Indicatief)": format_full_number(a8["atr_stop"], 2, "₺"),
        "ATR-Doel (Indicatief)": format_full_number(a8["atr_target"], 2, "₺"),
        "Risk/Reward Ratio": format_full_ratio(a8["rr_ratio"], 2),
        "Analisten Koersdoel": format_full_number(analyst_target, 2, "₺"),
        "Koersdoelruimte": format_full_percentage(target_upside, 2, True),
        "Nieuws Sentiment": a3["sentiment"],
        "Nieuws Balans": f"Positief: {len(a3['pos_news'])} | Negatief: {len(a3['neg_news'])}",
        "Datadekking": a7["data_quality"], "Risiconiveau": a7["risk_level"],
        "Agent1_Redenen": "; ".join(a1["reasons"]), "Agent2_Redenen": "; ".join(a2["reasons"]) if a2["reasons"] else "Geen fundamentele ratio's beschikbaar",
        "Agent3_Redenen": a3["reason"], "Agent4_Redenen": a4["reason"], "Agent5_Redenen": a5["reason"],
        "Agent6_Redenen": a6["Reason"], "Agent7_Redenen": a7["reason"],
        "Alert_Bericht": a8["alert_msg"]
    }

# ==============================================================================
# 6. STREAMLIT MULTI-TAB ENTERPRISE UI
# ==============================================================================

st.title("🏛️ BIST 30 Scanner Ultimate 5.8 — 8-Agent Enterprise Command Center")
st.caption("Inclusief Asymmetrische Risk/Reward (min. 1:2 R/R), Golden Bounce volume-bevestiging en Elastiek-penalty (Mean Reversion).")

with st.sidebar:
    st.header("⚙️ BIST 30 Scan Instellingen")
    universe = st.multiselect(f"BIST 30 Aandelen ({len(WATCHLIST)}):", options=WATCHLIST, default=WATCHLIST)
    if st.button("🚀 Start Volledige 8-Agent Scan", type="primary", use_container_width=True):
        if not universe:
            st.warning("Selecteer minimaal één BIST 30-aandeel.")
        else:
            scan_rows = []
            prog = st.progress(0, text="Initialiseren van de 8 autonome AI-agents...")
            macro = get_macro_data()
            for idx, ticker in enumerate(universe):
                prog.progress((idx + 1) / len(universe), text=f"8 Agents analyseren {ticker}...")
                item_res = analyze_stock_enterprise(ticker, macro)
                if item_res: scan_rows.append(item_res)
            prog.empty()
            if scan_rows:
                df_all = pd.DataFrame(scan_rows).sort_values(by="_total_score_num", ascending=False).reset_index(drop=True)
                st.session_state["bist_30_results"] = df_all
                st.success(f"Scan voltooid: {len(df_all)} BIST 30-aandelen succesvol geanalyseerd.")

if "bist_30_results" in st.session_state:
    df_res = st.session_state["bist_30_results"]
    st.markdown("### 🥇 Bruikbaarder Top 10 Selectie (Volledig Uitgeschreven Cijfers)")
    top10_cols = ["Bedrijf", "Ticker", "Sector", "Type Setup", "Totaalscore", "Risk/Reward Ratio", "Koers (Volledig)", "P/E (FK)", "Steun S1", "Weerstand R1", "Nieuws Balans"]
    st.dataframe(df_res.head(10)[top10_cols], use_container_width=True, hide_index=True)

    st.subheader("🤖 Diepte-Analyse per Aandeel — Volledige Output van Agent 1 t/m Agent 8")
    for _, row in df_res.iterrows():
        with st.expander(f"{row['Bedrijf']} ({row['Ticker']}) — Score: {row['Totaalscore']}/10 — {row['Type Setup']} — Koers: {row['Koers (Volledig)']}"):
            if row["Alert_Bericht"]: st.success(row["Alert_Bericht"])
            
            c1, c2, c3, c4 = st.columns(4)
            with c1: render_full_card("Totaalscore & Setup", f"{row['Totaalscore']} / 10", row["Type Setup"], "#1f77b4")
            with c2: render_full_card("Risk/Reward Ratio", row["Risk/Reward Ratio"], f"RSI(14): {row['RSI (14)']} · Trend: {row['Trend']}", "#2ca02c")
            with c3: render_full_card("Steun S1 / Weerstand R1", f"{row['Steun S1']} / {row['Weerstand R1']}", f"ATR Stop: {row['ATR-Stop (Indicatief)']}", "#ff7f0e")
            with c4: render_full_card("Waardering P/E & P/B", f"P/E: {row['P/E (FK)']} · P/B: {row['P/B (PD/DD)']}", f"Analist Doel: {row['Analisten Koersdoel']}", "#9467bd")

            st.markdown("#### 4. Volledige Diagnose van alle 8 Autonome AI-Agents")
            st.write(f"- **Agent 1 (Quant, Elastiek & Bounce):** {row['Agent1_Redenen']}")
            st.write(f"- **Agent 2 (Fundamenteel & Kwartaal):** {row['Agent2_Redenen']}")
            st.write(f"- **Agent 3 (KAP & Nieuws):** {row['Agent3_Redenen']}")
            st.write(f"- **Agent 4 (Macro & USD/TRY):** {row['Agent4_Redenen']}")
            st.write(f"- **Agent 5 (Schuld & Liquiditeit):** {row['Agent5_Redenen']}")
            st.write(f"- **Agent 6 (Inkoop & Dividend):** {row['Agent6_Redenen']}")
            st.write(f"- **Agent 7 (Auditor & Zwevend Aandeel Check):** {row['Agent7_Redenen']}")
            st.write(f"- **Agent 8 (R/R Executie & Analisten):** R/R Ratio bedraagt {row['Risk/Reward Ratio']}. Analisten voorzien nog {row['Koersdoelruimte']} opwaarts potentieel.")
# ==============================================================================
# 4. DE 8 VOLLEDIG ZELFSTANDIGE AUTONOME AI-AGENTS (BIST 30 ENTERPRISE 5.8)
# ==============================================================================

def agent_1_multi_timeframe_quant(ticker, hist_daily, sr_info):
    """
    AGENT 1: Technische Quant, SMA20/50, RSI, MACD en Momentum Analyse.
    INCLUSIEF: Golden Bounce en Elastiek-penalty (Mean Reversion).
    """
    close = hist_daily["Close"].astype(float)
    price = safe_float(close.iloc[-1])
    sma20 = sr_info["SMA20"]
    sma50 = sr_info["SMA50"]
    rsi = safe_float(calculate_rsi(close, 14).iloc[-1])
    vol_ratio = sr_info["Vol_Ratio"]

    dist_s1 = sr_info["Dist_S1_Pct"] / 100.0 if sr_info["S1"] else 0.0
    dist_r1 = sr_info["Dist_R1_Pct"] / 100.0 if sr_info["R1"] else 0.0
    dist_sma20 = abs((price - sma20) / sma20) if sma20 else 0.0

    points = 0.0
    reasons = []

    # Mean Reversion / Elastiek-effect
    if dist_sma20 > 0.15:
        points -= 1.5
        reasons.append(f"Elastiek-penalty: Koers is {dist_sma20*100:.1f}% te ver verwijderd van SMA20 (Hoge Mean Reversion risico)")
    elif sma20 and price > sma20:
        points += 1.5
        reasons.append(f"Koers noteert veilig boven SMA20 ({format_full_number(sma20, 2)})")

    if sma50 and price > sma50:
        points += 1.5
        reasons.append(f"Koers noteert boven SMA50 ({format_full_number(sma50, 2)})")

    # Zwevend aandeel vs. Golden Bounce
    if dist_s1 > 0.12:
        points -= 1.0
        reasons.append(f"Zwevend aandeel: Koers noteert {dist_s1*100:.1f}% boven steun S1 (hoog terugvalrisico)")
    elif 0 <= dist_s1 <= 0.035 and dist_r1 > 0.06:
        if vol_ratio and vol_ratio >= 1.0:
            points += 2.5
            reasons.append("Golden Bounce: Opvering vanaf steun S1 mét stijgend volume én veel ruimte tot weerstand (+2.5 pt)")
        else:
            points += 1.0
            reasons.append("Steun-bounce zonder volumebevestiging (zwakker koopsignaal)")

    if rsi is not None:
        if 45.0 <= rsi <= 65.0:
            points += 2.0
            reasons.append(f"RSI ({format_full_number(rsi, 1, '')}) in gezonde opwaartse zone")
        elif 30.0 <= rsi < 45.0:
            points += 1.0
            reasons.append(f"RSI ({format_full_number(rsi, 1, '')}) in lage herstelzone")
        elif rsi < 30.0:
            points += 0.5
            reasons.append(f"RSI ({format_full_number(rsi, 1, '')}) oversold — wacht op bodemvorming")
        else:
            reasons.append(f"RSI ({format_full_number(rsi, 1, '')}) oververhit — kans op winstnemingen")

    tech_score = round(min(10.0, max(1.0, points)), 1)
    return {"score": tech_score, "rsi": rsi, "reasons": reasons}

def agent_2_fundamental_quarterly_valuation(info, q_metrics):
    pe = safe_float(info.get("trailingPE"))
    pb = safe_float(info.get("priceToBook"))
    margin = safe_float(info.get("profitMargins"))
    rev_growth = safe_float(info.get("revenueGrowth"))
    market_cap = safe_float(info.get("marketCap"))

    points = 0.0
    max_pts = 0.0
    reasons = []

    if pe and pe > 0:
        max_pts += 2.5
        if pe < 8.5: points += 2.5; reasons.append(f"Zeer aantrekkelijke P/E (FK) van {format_full_ratio(pe, 2)}")
        elif pe <= 15.0: points += 1.5; reasons.append(f"Gezonde P/E (FK) van {format_full_ratio(pe, 2)}")
        else: reasons.append(f"Hoge P/E (FK) waardering van {format_full_ratio(pe, 2)}")

    if pb and pb > 0:
        max_pts += 2.0
        if pb < 1.5: points += 2.0; reasons.append(f"Lage P/B (PD/DD) van {format_full_ratio(pb, 2)}")
        elif pb <= 2.5: points += 1.0; reasons.append(f"Redelijke P/B (PD/DD) van {format_full_ratio(pb, 2)}")
        else: reasons.append(f"Stevige P/B (PD/DD) van {format_full_ratio(pb, 2)}")

    if margin is not None:
        max_pts += 2.0
        if margin >= 0.12: points += 2.0; reasons.append(f"Sterke winstmarge van {format_full_percentage(margin*100, 2)}")
        elif margin > 0: points += 1.0; reasons.append(f"Positieve winstmarge van {format_full_percentage(margin*100, 2)}")
        else: reasons.append("Negatieve winstmarge (verlieslatend)")

    fund_score = round((points / max_pts) * 10.0, 1) if max_pts > 0 else None
    return {"score": fund_score, "pe": pe, "pb": pb, "margin_pct": margin * 100.0 if margin else None, "rev_growth_pct": rev_growth * 100.0 if rev_growth else None, "market_cap_full": market_cap, "reasons": reasons}

def agent_3_kap_and_news_intelligence(ticker, company, fund_res, q_metrics, macro_info, api_key=None, use_ai=False):
    pos_news, neg_news, unc_news = get_stock_news(ticker, company)
    headlines_tuple = tuple([n["titel"] for n in (pos_news + neg_news + unc_news)])

    ai_data = None
    if use_ai and api_key:
        fund_summary = {"PE": fund_res.get("pe"), "PB": fund_res.get("pb"), "Winstmarge_pct": fund_res.get("margin_pct"), "Omzetgroei_pct": fund_res.get("rev_growth_pct")}
        ai_data = call_gemini_kap_agent(ticker, company, fund_summary, q_metrics, headlines_tuple, macro_info.get("usd_try"), api_key)

    if ai_data and safe_float(ai_data.get("score_adjustment")) is not None:
        adj = float(np.clip(safe_float(ai_data.get("score_adjustment")), -1.5, 1.5))
        sent = str(ai_data.get("sentiment_label", "Neutraal (AI)"))
        rsn = f"Gemini AI ({sent}): {ai_data.get('kap_duiding', '')}"
    else:
        if len(pos_news) > len(neg_news):
            adj, sent, rsn = min(0.8, 0.35 * (len(pos_news) - len(neg_news))), "Positief (KAP/Nieuws)", f"{len(pos_news)} positieve KAP-signalen tegenover {len(neg_news)} negatieve."
        elif len(neg_news) > len(pos_news):
            adj, sent, rsn = max(-1.2, -0.45 * (len(neg_news) - len(pos_news))), "Negatief / Waarschuwing", f"Opgelet: {len(neg_news)} negatieve nieuws-signalen gedetecteerd."
        else:
            adj, sent, rsn = 0.0, "Neutraal / Onbeslist", f"Geen overwegend positieve of negatieve uitslag ({len(unc_news)} overige berichten)."
    return {"pos_news": pos_news, "neg_news": neg_news, "unc_news": unc_news, "adjustment": round(adj, 2), "sentiment": sent, "ai_report": ai_data, "reason": rsn}

def agent_4_macro_fx_devaluation_buffer(ticker, sector, macro_info):
    dev_risk = macro_info.get("dev_risk", False)
    is_exp = ticker in HARD_CURRENCY_EXPORTERS
    adj, rsn = 0.0, []
    if is_exp:
        if dev_risk: adj += 0.8; rsn.append("Sterke USD/EUR devaluatie-buffer actief: internationaal verdienmodel beschermt marges")
        else: adj += 0.4; rsn.append("Structurele harde-valuta inkomsten en exportpositie")
    else:
        if dev_risk and sector in ["Vastgoed (GYO)", "Telecom, Data & FinTech"]: adj -= 0.4; rsn.append("Binnenlands lira-verdienmodel is gevoeliger voor valuta- en renteschokken")
        else: rsn.append("Binnenlands marktprofiel; volgt lokale Turkse conjunctuur")
    return {"adjustment": round(adj, 2), "reason": "; ".join(rsn)}

def agent_5_debt_liquidity_interest_stress(info, q_metrics):
    dte = safe_float(info.get("debtToEquity"))
    net_debt = (q_metrics.get("total_debt_full") - q_metrics.get("total_cash_full")) if (q_metrics.get("total_debt_full") is not None and q_metrics.get("total_cash_full") is not None) else None
    adj, rsn = 0.0, []
    if net_debt is not None and net_debt <= 0: adj += 0.7; rsn.append(f"Netto kaspositie ({format_full_number(abs(net_debt), 0, '₺')} netto kas)")
    if dte is not None:
        if dte < 45.0: adj += 0.5; rsn.append(f"Lage schuldenratio (D/E: {format_full_percentage(dte, 2)}) — bestand tegen hoge Turkse rente")
        elif dte > 110.0: adj -= 0.8; rsn.append(f"Hoge schuldenlast (D/E: {format_full_percentage(dte, 2)}) — kwetsbaar voor hoge rentekosten")
    return {"adjustment": round(adj, 2), "reason": "; ".join(rsn) if rsn else "Geen schuldgegevens gerapporteerd"}

def agent_6_insider_buyback_dividend_structure(info, pos_news):
    adj, rsn = 0.0, []
    div_yield = safe_float(info.get("dividendYield"))
    if div_yield and div_yield > 0:
        dy_pct = div_yield * 100.0 if div_yield < 1.0 else div_yield
        if dy_pct >= 3.0: adj += 0.3; rsn.append(f"Aantrekkelijk dividendrendement (Temettü): {format_full_percentage(dy_pct, 2)}")
    if any("geri alım" in n["titel"].lower() or "inkoop" in n["titel"].lower() for n in pos_news):
        adj += 0.4; rsn.append("Actief aandeleninkoopprogramma (Geri Alım) gedetecteerd")
    return {"adjustment": round(adj, 2), "Reason": "; ".join(rsn) if rsn else "Standaard BIST 30 eigendomsstructuur"}

def agent_7_independent_risk_and_factcheck_auditor(tech_res, fund_res, news_res, debt_res, sr_info, price):
    t_score, f_score = tech_res["score"], fund_res["score"]
    dist_s1 = sr_info["Dist_S1_Pct"] / 100.0 if sr_info["S1"] else 0.0
    neg_count = len(news_res["neg_news"])

    if f_score is not None: data_quality, quality_adj = "Volledig", 0.2
    else: data_quality, quality_adj = "Beperkt (Geen fundamentele data)", -0.4

    if dist_s1 > 0.12:
        setup_type, risk_level = "Opgelet: Zwevend Aandeel (Te ver van S1)", "Hoog (Wacht op consolidatie of mean reversion)"
    elif f_score and f_score >= 6.2 and tech_res["rsi"] <= 48.0 and neg_count == 0:
        setup_type, risk_level = "Koopwaardige Herstelkans (Lage RSI, Sterk Fundament)", "Gemiddeld (Wacht op steunbevestiging)"
    elif (f_score and f_score < 4.2) or neg_count > 1 or debt_res["adjustment"] <= -0.7:
        setup_type, risk_level = "Opgelet: Terecht Gedaald / Value Trap", "Hoog (Vermijd waardevalkuil)"
    elif t_score >= 7.0 and (f_score is None or f_score >= 5.8):
        setup_type, risk_level = "Sterke Kwaliteitstrend & Positief Momentum", "Laag tot Gemiddeld (Trendvolgend)"
    else:
        setup_type, risk_level = "Neutraal / Volgen op BIST 30 Watchlist", "Gemiddeld"

    return {"setup_type": setup_type, "risk_level": risk_level, "data_quality": data_quality, "quality_adj": quality_adj, "reason": f"Classificatie: {setup_type} | Risicoprofiel: {risk_level}"}

def agent_8_execution_portfolio_telegram_dispatcher(ticker, company, price, sr_info, overall_score, setup_type):
    atr = sr_info["ATR"] if sr_info else (price * 0.03)
    atr_stop = max(0.01, price - (1.5 * atr))
    atr_target = price + (2.2 * atr)
    risk_per_share = max(0.01, price - atr_stop)
    reward_per_share = max(0.01, atr_target - price)
    rr_ratio = reward_per_share / risk_per_share if risk_per_share > 0 else 1.0

    alert_msg = None
    if overall_score >= 7.2:
        if rr_ratio >= 2.0:
            alert_msg = (
                f"🚨 [BIST 30 TOP SIGNAL] {company} ({ticker}) | "
                f"Score: {format_full_number(overall_score, 1, '')}/10 | "
                f"R/R: {format_full_ratio(rr_ratio, 2)} | "
                f"Setup: {setup_type} | "
                f"Koers: {format_full_number(price, 2)} | "
                f"S1: {format_full_number(sr_info['S1'], 2)} | "
                f"ATR-Stop: {format_full_number(atr_stop, 2)} | "
                f"ATR-Doel: {format_full_number(atr_target, 2)}"
            )
    return {"atr_stop": atr_stop, "atr_target": atr_target, "rr_ratio": rr_ratio, "alert_msg": alert_msg}

def analyze_stock_enterprise(ticker, macro_info, api_key=None, use_ai=False):
    hist = get_history(ticker, "1y")
    if hist.empty or len(hist) < 30: return None
    close = hist["Close"].astype(float)
    price = safe_float(close.iloc[-1])
    if not price: return None

    info = yf.Ticker(ticker).info or {}
    company = str(info.get("longName") or info.get("shortName") or ticker)
    sector = SECTOR_MAP.get(ticker, "BIST 30 Kernsector")

    sr_info = calculate_sr_levels(hist)
    q_metrics = get_quarterly_and_balance_metrics(ticker)

    a1 = agent_1_multi_timeframe_quant(ticker, hist, sr_info)
    a2 = agent_2_fundamental_quarterly_valuation(info, q_metrics)
    a3 = agent_3_kap_and_news_intelligence(ticker, company, a2, q_metrics, macro_info, api_key, use_ai)
    a4 = agent_4_macro_fx_devaluation_buffer(ticker, sector, macro_info)
    a5 = agent_5_debt_liquidity_interest_stress(info, q_metrics)
    a6 = agent_6_insider_buyback_dividend_structure(info, a3["pos_news"])
    a7 = agent_7_independent_risk_and_factcheck_auditor(a1, a2, a3, a5, sr_info, price)

    base_score = (0.48 * a1["score"]) + (0.52 * a2["score"]) if a2["score"] is not None else a1["score"] * 0.85
    total_adjustments = a3["adjustment"] + a4["adjustment"] + a5["adjustment"] + a6["adjustment"] + a7["quality_adj"]
    overall_score = round(min(10.0, max(1.0, base_score + total_adjustments)), 1)

    a8 = agent_8_execution_portfolio_telegram_dispatcher(ticker, company, price, sr_info, overall_score, a7["setup_type"])
    analyst_target = safe_float(info.get("targetMeanPrice"))
    target_upside = ((analyst_target / price) - 1.0) * 100.0 if (analyst_target and price > 0) else None

    return {
        "Bedrijf": company, "Ticker": ticker, "Sector": sector, "Profiel": BIST30_PROFILES.get(ticker, ""),
        "_price_num": price, "_total_score_num": overall_score, "_tech_score_num": a1["score"],
        "_fund_score_num": a2["score"] if a2["score"] is not None else -1.0,
        "_atr_stop_num": a8["atr_stop"], "_atr_target_num": a8["atr_target"],
        "Type Setup": a7["setup_type"],
        "Totaalscore": format_full_number(overall_score, 1, ""),
        "Technische score": format_full_number(a1["score"], 1, ""),
        "Fundamentele score": format_full_number(a2["score"], 1, "") if a2["score"] is not None else "Niet beschikbaar",
        "Koers (Volledig)": format_full_number(price, 2, "₺"),
        "P/E (FK)": format_full_ratio(a2["pe"], 2), "P/B (PD/DD)": format_full_ratio(a2["pb"], 2),
        "Winstmarge": format_full_percentage(a2["margin_pct"], 2), "Omzetgroei (j-o-j)": format_full_percentage(a2["rev_growth_pct"], 2, True),
        "Marktkapitalisatie (Volledig)": format_full_number(a2["market_cap_full"], 0, "₺"),
        "Laatste Kwartaal": q_metrics["last_quarter_date"],
        "Kwartaalomzet (Volledig)": format_full_number(q_metrics["q_rev_full"], 0, "₺"),
        "Kwartaal Nettowinst (Volledig)": format_full_number(q_metrics["q_net_full"], 0, "₺"),
        "QoQ Omzetgroei": format_full_percentage(q_metrics["qoq_rev_growth"], 2, True),
        "QoQ Winstgroei": format_full_percentage(q_metrics["qoq_net_growth"], 2, True),
        "Totale Schuld (Volledig)": format_full_number(a5["total_debt_full"], 0, "₺"),
        "Totale Kaspositie (Volledig)": format_full_number(a5["total_cash_full"], 0, "₺"),
        "Netto Schuld (Volledig)": format_full_number(a5["net_debt_full"], 0, "₺"),
        "RSI (14)": format_full_number(a1["rsi"], 1, ""), "Trend": sr_info["Trend"] if sr_info else "Onbekend",
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
        "Analisten Koersdoel": format_full_number(analyst_target, 2, "₺"),
        "Koersdoelruimte": format_full_percentage(target_upside, 2, True),
        "Nieuws Sentiment": a3["sentiment"],
        "Nieuws Balans": f"Positief: {len(a3['pos_news'])} | Negatief: {len(a3['neg_news'])} | Te controleren: {len(a3['unc_news'])}",
        "Datadekking": a7["data_quality"], "Risiconiveau": a7["risk_level"],
        "SR_Relevantie": sr_info["Relevantie"] if sr_info else "Niet beschikbaar",
        "Agent1_Redenen": "; ".join(a1["reasons"]), "Agent2_Redenen": "; ".join(a2["reasons"]) if a2["reasons"] else "Geen fundamentele ratio's beschikbaar",
        "Agent3_Redenen": a3["reason"], "Agent4_Redenen": a4["reason"], "Agent5_Redenen": a5["reason"],
        "Agent6_Redenen": a6["Reason"], "Agent7_Redenen": a7["reason"],
        "AI_Rapport": a3["ai_report"], "Positief_Nieuws": a3["pos_news"], "Negatief_Nieuws": a3["neg_news"], "Onduidelijk_Nieuws": a3["unc_news"],
        "Alert_Bericht": a8["alert_msg"]
    }

@st.cache_data(ttl=900, show_spinner=False)
def run_historical_backtest(ticker, holding_days=10):
    hist = get_history(ticker, "1y")
    if hist.empty or len(hist) < 60: return None
    close = hist["Close"].astype(float)
    sma50 = close.rolling(50).mean()
    rsi = calculate_rsi(close, 14)

    trades = []
    i = 50
    while i < len(close) - holding_days:
        c_price, c_sma50, c_rsi, prev_rsi = safe_float(close.iloc[i]), safe_float(sma50.iloc[i]), safe_float(rsi.iloc[i]), safe_float(rsi.iloc[i - 1])
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

    if not trades: return {"trades_df": pd.DataFrame(), "total_trades": 0, "win_rate": 0.0, "avg_return": 0.0}
    t_df = pd.DataFrame(trades)
    win_rate = (sum(1 for r in trades if r["_ret_num"] > 0) / len(trades)) * 100.0
    return {"trades_df": t_df.drop(columns=["_ret_num"]), "total_trades": len(trades), "win_rate": win_rate, "avg_return": float(np.mean([r["_ret_num"] for r in trades]))}


# ==============================================================================
# 6. STREAMLIT MULTI-TAB ENTERPRISE UI (VOLLEDIGE 6 TABS)
# ==============================================================================

st.title("🏛️ BIST 30 Scanner Ultimate 5.8 — 8-Agent Enterprise Command Center")
st.caption("Inclusief Asymmetrische Risk/Reward (min. 1:2 R/R), Golden Bounce volume-bevestiging en Elastiek-penalty (Mean Reversion).")

with st.sidebar:
    st.header("⚙️ BIST 30 Scan Instellingen")
    universe = st.multiselect(f"BIST 30 Aandelenuniversum ({len(WATCHLIST)}):", options=WATCHLIST, default=WATCHLIST)
    sort_choice = st.selectbox("Rangschikken op:", ["Totaalscore (Hoog naar Laag)", "Fundamentele score (Hoog naar Laag)", "Technische score (Hoog naar Laag)"])
    
    st.divider()
    st.header("🤖 Gemini AI-Agent (Optioneel)")
    gemini_api_key = st.text_input("Google Gemini API Key:", type="password")
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
    "📊 1. Macro, BIST 30 / 100", 
    "🏆 2. Volledige Scan & Top 10", 
    "📐 3. Steun & Weerstand Matrix", 
    "🤖 4. Diepte-Analyse (8 Agents)", 
    "📰 5. KAP & Marktnieuws", 
    "💼 6. Portefeuille & Telegram"
])

# --- TAB 1: MACRO ---
with tab1:
    st.subheader("Actueel Macro-, Valuta-, BIST 30 & BIST 100 Overzicht")
    mc1, mc2, mc3, mc4 = st.columns(4)
    with mc1: render_full_card("USD / TRY Wisselkoers", format_full_number(macro["usd_try"], 4, "₺"), f"1m verandering: {format_full_percentage(macro['usd_try_change_1m'], 2, True)}", "#d62728" if macro["dev_risk"] else "#2ca02c")
    with mc2: render_full_card("EUR / TRY", format_full_number(macro.get("eur_try"), 4, "₺"), "Valutabuffer", "#1f77b4")
    with mc3: render_full_card("BIST 30 (XU030)", format_full_number(macro["xu030_price"], 2, ""), "Hoofdfondsen", "#2ca02c")
    with mc4: render_full_card("BIST 100 (XU100)", format_full_number(macro["xu100_price"], 2, ""), "Brede markt", "#9467bd")

    idx_col1, idx_col2 = st.columns(2)
    with idx_col1:
        st.markdown("#### BIST 30 Index (XU030.IS) Steun/Weerstand")
        if macro["xu030_sr"]:
            st.table(pd.DataFrame([{"Niveau": k, "Waarde": format_full_number(v, 2, "")} for k, v in macro["xu030_sr"].items() if k in ["R2", "R1", "Pivot", "S1", "S2"]]))
    with idx_col2:
        st.markdown("#### BIST 100 Index (XU100.IS) Steun/Weerstand")
        if macro["xu100_sr"]:
            st.table(pd.DataFrame([{"Niveau": k, "Waarde": format_full_number(v, 2, "")} for k, v in macro["xu100_sr"].items() if k in ["R2", "R1", "Pivot", "S1", "S2"]]))

# --- TAB 2: SCAN & TOP 10 ---
with tab2:
    st.subheader(f"🏆 Volledige BIST 30 Screening & Top 10")
    if st.button("🚀 Start Volledige 8-Agent Scan", type="primary", use_container_width=True):
        if not universe: st.warning("Selecteer aandelen.")
        else:
            scan_rows = []
            prog = st.progress(0, text="Initialiseren...")
            for idx, ticker in enumerate(universe):
                prog.progress((idx + 1) / len(universe), text=f"8 Agents analyseren {ticker}...")
                res = analyze_stock_enterprise(ticker, macro, api_key=gemini_api_key, use_ai=use_gemini_ai)
                if res: scan_rows.append(res)
            prog.empty()
            if scan_rows:
                df_all = pd.DataFrame(scan_rows).sort_values(by="_total_score_num", ascending=False).reset_index(drop=True)
                st.session_state["bist_30_results"] = df_all
                st.success("Scan voltooid.")

    if "bist_30_results" in st.session_state:
        df_res = st.session_state["bist_30_results"]
        st.markdown("### 🥇 Top 10 Selectie")
        st.dataframe(df_res.head(10)[["Bedrijf", "Ticker", "Type Setup", "Totaalscore", "Risk/Reward Ratio", "Koers (Volledig)", "P/E (FK)", "Steun S1", "Weerstand R1"]], use_container_width=True, hide_index=True)
        st.markdown("### 📋 Volledige Ranglijst")
        st.dataframe(df_res[["Bedrijf", "Ticker", "Totaalscore", "Koers (Volledig)", "P/E (FK)", "P/B (PD/DD)", "Winstmarge", "Kwartaalomzet (Volledig)"]], use_container_width=True, hide_index=True)

# --- TAB 3: MATRIX ---
with tab3:
    st.subheader("📐 Volledige Steun- en Weerstandsmatrix (S1–S3 & R1–R3)")
    if "bist_30_results" in st.session_state:
        st.dataframe(st.session_state["bist_30_results"][["Bedrijf", "Ticker", "Koers (Volledig)", "Trend", "Steun S2", "Steun S1", "Pivot Punt", "Weerstand R1", "Weerstand R2", "Afstand tot S1", "Afstand tot R1"]], use_container_width=True, hide_index=True)

# --- TAB 4: DIEPTE ANALYSE (EXPANDERS) ---
with tab4:
    st.subheader("🤖 Diepte-Analyse per Aandeel — 8 Agents")
    if "bist_30_results" in st.session_state:
        df_res = st.session_state["bist_30_results"]
        for _, row in df_res.iterrows():
            with st.expander(f"{row['Bedrijf']} ({row['Ticker']}) — Score: {row['Totaalscore']}/10"):
                if row["Alert_Bericht"]: st.success(row["Alert_Bericht"])
                
                c1, c2, c3, c4 = st.columns(4)
                with c1: render_full_card("Totaalscore", row['Totaalscore'], row["Type Setup"], "#1f77b4")
                with c2: render_full_card("Risk/Reward Ratio", row["Risk/Reward Ratio"], f"Trend: {row['Trend']}", "#2ca02c")
                with c3: render_full_card("Steun S1 / Weerstand R1", f"{row['Steun S1']} / {row['Weerstand R1']}", f"ATR Stop: {row['ATR-Stop (Indicatief)']}", "#ff7f0e")
                with c4: render_full_card("Waardering P/E", row['P/E (FK)'], f"Marge: {row['Winstmarge']}", "#9467bd")

                st.markdown("#### Diagnose 8 Autonome AI-Agents")
                st.write(f"- **Agent 1 (Quant, Elastiek & Bounce):** {row['Agent1_Redenen']}")
                st.write(f"- **Agent 2 (Fundamenteel & Kwartaal):** {row['Agent2_Redenen']}")
                st.write(f"- **Agent 3 (KAP & Nieuws):** {row['Agent3_Redenen']}")
                st.write(f"- **Agent 4 (Macro & USD/TRY):** {row['Agent4_Redenen']}")
                st.write(f"- **Agent 5 (Schuld & Liquiditeit):** {row['Agent5_Redenen']}")
                st.write(f"- **Agent 6 (Inkoop & Dividend):** {row['Agent6_Redenen']}")
                st.write(f"- **Agent 7 (Auditor):** {row['Agent7_Redenen']}")
                st.write(f"- **Agent 8 (R/R Executie):** R/R Ratio bedraagt {row['Risk/Reward Ratio']}.")

# --- TAB 5: NIEUWS ---
with tab5:
    st.subheader("📰 Algemene BIST 30 KAP & SPK Nieuwsmonitor")
    news_df = get_news()
    if not news_df.empty:
        g1, g2, g3 = st.columns(3)
        with g1:
            st.markdown("### 🟢 Positief")
            for _, item in news_df[news_df["Signaal"] == "Positief"].iterrows(): st.markdown(f"- [{item['Titel']}]({item['Link']})")
        with g2:
            st.markdown("### 🔴 Negatief")
            for _, item in news_df[news_df["Signaal"] == "Negatief"].iterrows(): st.markdown(f"- [{item['Titel']}]({item['Link']})")
        with g3:
            st.markdown("### ⚪ Te controleren")
            for _, item in news_df[news_df["Signaal"] == "Onduidelijk / Te controleren"].iterrows(): st.markdown(f"- [{item['Titel']}]({item['Link']})")

# --- TAB 6: PORTEFEUILLE & BACKTEST ---
with tab6:
    st.subheader("💼 Portefeuille Simulator & Telegram")
    p1, p2 = st.columns(2)
    with p1: total_capital = st.number_input("Totaal Kapitaal (TRY):", value=250000.0)
    with p2: risk_pct = st.slider("Max verliesrisico per positie (%):", 0.5, 5.0, 1.5)

    if "bist_30_results" in st.session_state:
        df_res = st.session_state["bist_30_results"]
        if st.button("📨 Verstuur Top Alerts naar Telegram"):
            alerts = [r["Alert_Bericht"] for _, r in df_res.iterrows() if r["Alert_Bericht"]]
            if alerts:
                ok, msg = send_telegram_alert(tg_bot_token, tg_chat_id, "\n\n".join(alerts[:10]))
                if ok: st.success(msg)
                else: st.error(msg)
            else: st.info("Geen aandelen voldoen aan de R/R drempel van 2.0 voor een alert.")
            
    st.divider()
    st.subheader("📈 Historische Backtest")
    b1, b2 = st.columns(2)
    with b1: bt_ticker = st.selectbox("Selecteer aandeel:", WATCHLIST)
    with b2: bt_days = st.slider("Houdperiode (dagen):", 5, 30, 10)
    bt_res = run_historical_backtest(bt_ticker, bt_days)
    if bt_res and bt_res["total_trades"] > 0:
        c1, c2, c3 = st.columns(3)
        with c1: render_full_card("Aantal Trades", format_full_integer(bt_res["total_trades"]), "", "#1f77b4")
        with c2: render_full_card("Win-Rate (%)", format_full_percentage(bt_res["win_rate"], 2), "", "#2ca02c")
        with c3: render_full_card("Gemiddeld Rendement", format_full_percentage(bt_res["avg_return"], 2, True), "", "#ff7f0e")
        st.dataframe(bt_res["trades_df"], use_container_width=True, hide_index=True)
