import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import urllib.parse
import urllib.request
import json
from datetime import datetime, timedelta

# ==============================================================================
# BIST 30 PURE QUANT ULTIMATE 5.8 — 8-AGENT ENTERPRISE COMMAND CENTER
# INCLUSIEF: JIP EN JANNEKE UITLEG, HOVER-TOOLTIPS & API-BEVEILIGING
# ==============================================================================

st.set_page_config(
    page_title="BIST 30 Pure Quant Scanner 5.8",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS OVERRIDE: VOORKOM AFKAPPEN VAN GETALLEN ---
st.markdown(
    """
    <style>
    [data-testid="stMetricValue"] {
        font-size: 1.35rem !important; white-space: normal !important;
        overflow: visible !important; text-overflow: clip !important;
        word-break: break-word !important; line-height: 1.25 !important;
    }
    .full-num-card {
        background-color: rgba(240, 242, 246, 0.65); border-left: 4px solid #1f77b4;
        padding: 12px 14px; border-radius: 6px; margin-bottom: 10px;
    }
    .full-num-title { font-size: 0.82rem; color: #555; font-weight: 600; margin-bottom: 4px; }
    .full-num-val { font-size: 1.20rem; font-weight: 700; color: #111; word-break: break-all; }
    .full-num-sub { font-size: 0.78rem; color: #333; margin-top: 4px; }
    </style>
    """,
    unsafe_allow_html=True
)

# ==============================================================================
# 1. BIST 30 UNIVERSUM & BEDRIJFSPROFIELEN
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
    "ARCLK.IS": "Consumentenelektronica", "ASELS.IS": "Defensie & Hoogtechnologie",
    "ASTOR.IS": "Energietechniek", "BIMAS.IS": "Supermarkten & Defensieve Retail",
    "DOAS.IS": "Automotive Distributie", "EKGYO.IS": "Vastgoed (GYO)",
    "ENKAI.IS": "Bouw, Energie & Valutareserves", "EREGL.IS": "Staal & Zware Industrie",
    "FROTO.IS": "Automotive & Export", "GARAN.IS": "Banken & Financieel",
    "HEKTS.IS": "Agrochemie & Landbouw", "ISCTR.IS": "Banken & Financieel",
    "KCHOL.IS": "Conglomeraat & Holding", "KONTR.IS": "Technologie & Energieopslag",
    "KOZAL.IS": "Goud & Edelmetalen", "KRDMD.IS": "Staal & Spoorwegindustrie",
    "MGROS.IS": "Supermarkten", "PETKM.IS": "Petrochemie & Basisindustrie",
    "PGSUS.IS": "Luchtvaart", "SAHOL.IS": "Conglomeraat & Holding",
    "SASA.IS": "Polyester & Petrochemie", "SISE.IS": "Glas, Chemie & Export",
    "TAVHL.IS": "Luchthavenexploitatie", "TCELL.IS": "Telecom & FinTech",
    "THYAO.IS": "Luchtvaart & Vracht", "TOASO.IS": "Automotive Productie",
    "TUPRS.IS": "Energie & Raffinage", "YKBNK.IS": "Banken & Financieel"
}

HARD_CURRENCY_EXPORTERS = {
    "ARCLK.IS", "ASELS.IS", "ASTOR.IS", "ENKAI.IS", "EREGL.IS",
    "FROTO.IS", "KCHOL.IS", "KONTR.IS", "KOZAL.IS", "PGSUS.IS",
    "SISE.IS", "TAVHL.IS", "THYAO.IS", "TOASO.IS", "TUPRS.IS"
}

# ==============================================================================
# 2. STRICTE FORMATTERINGSHULPFUNCTIES & TOOLTIPS
# ==============================================================================

def safe_float(value):
    try:
        if value is None: return None
        val = float(value)
        return val if np.isfinite(val) else None
    except (TypeError, ValueError): return None

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

def render_full_card(title, value_str, subtitle_str="", border_color="#1f77b4", tooltip=""):
    """Rendert een datakaartje. Als 'tooltip' is meegegeven, zie je dit als je er met de muis overheen gaat."""
    st.markdown(
        f"""<div class="full-num-card" style="border-left-color: {border_color};" title="{tooltip}">
            <div class="full-num-title">{title}</div>
            <div class="full-num-val">{value_str}</div>
            <div class="full-num-sub">{subtitle_str}</div>
        </div>""", unsafe_allow_html=True
    )

# ==============================================================================
# 3. KWANTITATIEVE ALGORITMES & DATA OPHAALFUNCTIES
# ==============================================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_history(ticker, period="1y"):
    df = yf.Ticker(ticker).history(period=period, auto_adjust=True)
    return df.dropna(subset=["Close", "High", "Low", "Volume"]) if not df.empty else pd.DataFrame()

def calculate_rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1.0/period, min_periods=period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1.0/period, min_periods=period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100.0 - (100.0 / (1.0 + rs))).fillna(50.0)

def calculate_macd(close):
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    return macd_line, signal_line

def calculate_obv(close, volume):
    obv = np.where(close > close.shift(1), volume, np.where(close < close.shift(1), -volume, 0)).cumsum()
    return pd.Series(obv, index=close.index)

def calculate_sr_levels_and_atr(hist):
    close, high, low, vol = hist["Close"].astype(float), hist["High"].astype(float), hist["Low"].astype(float), hist["Volume"].astype(float)
    price = safe_float(close.iloc[-1])
    if not price: return None

    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    atr = safe_float(tr.rolling(14).mean().iloc[-1]) or (price * 0.03)

    window = hist.tail(20)
    h, l = safe_float(window["High"].max()) or price, safe_float(window["Low"].min()) or price
    c = safe_float(close.iloc[-2]) if len(close) >= 2 else price
    pivot = (h + l + c) / 3.0
    rng = h - l

    r1, r2, r3 = pivot + (0.382 * rng), pivot + (0.618 * rng), pivot + (1.000 * rng)
    s1, s2, s3 = max(0.01, pivot - (0.382 * rng)), max(0.01, pivot - (0.618 * rng)), max(0.01, pivot - (1.000 * rng))

    vol_avg_20 = safe_float(vol.tail(20).mean())
    vol_latest = safe_float(vol.iloc[-1])
    vol_ratio = (vol_latest / vol_avg_20) if (vol_avg_20 and vol_avg_20 > 0 and vol_latest) else 1.0

    dist_s1_pct = ((price - s1) / s1) * 100.0 if s1 > 0 else 0.0
    dist_r1_pct = ((r1 - price) / price) * 100.0 if price > 0 else 0.0

    return {
        "Price": price, "Pivot": pivot, "R1": r1, "R2": r2, "R3": r3, "S1": s1, "S2": s2, "S3": s3,
        "Dist_S1_Pct": dist_s1_pct, "Dist_R1_Pct": dist_r1_pct, "Vol_Avg20": vol_avg_20, 
        "Vol_Latest": vol_latest, "Vol_Ratio": vol_ratio, "ATR": atr
    }

@st.cache_data(ttl=900, show_spinner=False)
def get_macro_data():
    out = {"usd_try": None, "dev_risk": False, "xu030_price": None, "xu030_ret_1m": None, "xu030_sr": None, "vix": None}
    try:
        fx = get_history("USDTRY=X", "1mo")
        if not fx.empty:
            v = safe_float(fx["Close"].iloc[-1])
            out["usd_try"] = v
            if v and v > 42.0: out["dev_risk"] = True
    except: pass
    try:
        m30 = get_history("XU030.IS", "6mo")
        if len(m30) >= 22:
            out["xu030_price"] = safe_float(m30["Close"].iloc[-1])
            out["xu030_ret_1m"] = ((out["xu030_price"] / safe_float(m30["Close"].iloc[-22])) - 1) * 100.0
            out["xu030_sr"] = calculate_sr_levels_and_atr(m30)
    except: pass
    try:
        vix = get_history("^VIX", "1mo")
        if not vix.empty: out["vix"] = safe_float(vix["Close"].iloc[-1])
    except: pass
    return out

@st.cache_data(ttl=900, show_spinner=False)
def get_quarterly_and_balance_metrics(ticker):
    q_data = {"q_rev_full": None, "q_net_full": None, "qoq_rev_growth": None, "qoq_net_growth": None, "total_debt_full": None, "total_cash_full": None, "net_debt_full": None}
    try:
        t_obj = yf.Ticker(ticker)
        q_inc = t_obj.quarterly_income_stmt
        if q_inc is not None and not q_inc.empty:
            c = q_inc.columns
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


# ==============================================================================
# 4. DE 8 PURE QUANTITATIEVE AGENTS
# ==============================================================================

def agent_1_multi_timeframe_quant(ticker, hist, sr_info):
    close = hist["Close"]
    price = sr_info["Price"]
    sma20, sma50 = safe_float(close.rolling(20).mean().iloc[-1]), safe_float(close.rolling(50).mean().iloc[-1])
    rsi = safe_float(calculate_rsi(close).iloc[-1])
    macd, signal = calculate_macd(close)
    macd_val, macd_sig = safe_float(macd.iloc[-1]), safe_float(signal.iloc[-1])
    
    pts = 0.0
    rsn = []
    
    dist_sma20 = abs(price - sma20) / sma20 if sma20 else 0.0
    if dist_sma20 > 0.15:
        pts -= 1.5; rsn.append(f"⚠️ Elastiek-penalty: Koers is {format_full_percentage(dist_sma20*100, 1)} verwijderd van SMA20.")
    elif sma20 and price > sma20:
        pts += 1.5; rsn.append(f"Trend positief boven SMA20 ({format_full_number(sma20)}).")
        
    if sma50 and price > sma50: pts += 1.5; rsn.append(f"Middellange trend positief (>SMA50).")
    
    if sr_info["Dist_S1_Pct"] > 12.0:
        pts -= 1.0; rsn.append(f"⚠️ Zwevend aandeel: {format_full_percentage(sr_info['Dist_S1_Pct'], 1)} boven steun S1.")
    elif 0 <= sr_info["Dist_S1_Pct"] <= 3.5 and sr_info["Dist_R1_Pct"] > 6.0:
        if sr_info["Vol_Ratio"] >= 1.0:
            pts += 2.5; rsn.append("🚀 Golden Bounce: Opvering vanaf S1 met volumebevestiging.")
        else:
            pts += 1.0; rsn.append("Steun-bounce maar zonder stijgend volume (dead cat risico).")

    if rsi:
        if 45 <= rsi <= 65: pts += 2.0; rsn.append(f"Gezond momentum (RSI {format_full_number(rsi, 1, '')}).")
        elif rsi < 30: pts += 0.5; rsn.append("RSI oversold, wacht op bodem.")
        
    if macd_val and macd_sig and macd_val > macd_sig:
        pts += 1.0; rsn.append("MACD positief (koopsignaal actief).")
        
    return {"score": round(max(1.0, min(10.0, pts)), 1), "rsi": rsi, "sma20": sma20, "sma50": sma50, "reasons": rsn}

def agent_2_fundamental_quarterly_valuation(info, q_metrics):
    pe = safe_float(info.get("trailingPE"))
    pb = safe_float(info.get("priceToBook"))
    margin = safe_float(info.get("profitMargins"))
    rg = safe_float(info.get("revenueGrowth"))
    
    pts, max_pts, rsn = 0.0, 0.0, []
    
    if pe and pe > 0:
        max_pts += 2.5
        if pe < 8.5: pts += 2.5; rsn.append(f"Lage P/E ({format_full_ratio(pe)}).")
        elif pe <= 15: pts += 1.5; rsn.append(f"Gezonde P/E ({format_full_ratio(pe)}).")
        else: rsn.append(f"Hoge P/E ({format_full_ratio(pe)}).")
        
    if pb and pb > 0:
        max_pts += 2.0
        if pb < 1.5: pts += 2.0; rsn.append(f"Lage P/B ({format_full_ratio(pb)}).")
        elif pb <= 2.5: pts += 1.0; rsn.append(f"Redelijke P/B ({format_full_ratio(pb)}).")
        else: rsn.append(f"Stevige P/B ({format_full_ratio(pb)}).")
        
    if margin is not None:
        max_pts += 2.0
        if margin >= 0.12: pts += 2.0; rsn.append(f"Sterke winstmarge ({format_full_percentage(margin*100)}).")
        elif margin > 0: pts += 1.0; rsn.append("Positieve winstmarge.")
        else: rsn.append("Negatieve winstmarge.")
        
    score = round((pts / max_pts) * 10.0, 1) if max_pts > 0 else None
    return {"score": score, "pe": pe, "pb": pb, "margin": margin*100 if margin else None, "rev_growth": rg*100 if rg else None, "reasons": rsn}

def agent_3_orderflow_and_alpha(ticker, hist, macro_info):
    close, vol = hist["Close"], hist["Volume"]
    obv = calculate_obv(close, vol)
    obv_sma = obv.rolling(20).mean().iloc[-1]
    obv_current = obv.iloc[-1]
    
    ret_1m = ((close.iloc[-1] / close.iloc[-22]) - 1) * 100 if len(close) >= 22 else 0
    alpha = ret_1m - (macro_info["xu030_ret_1m"] or 0.0)
    
    adj, rsn = 0.0, []
    if obv_current > obv_sma:
        adj += 0.5; rsn.append("Institutionele accumulatie: OBV stijgt harder dan gemiddeld (Smart Money koopt).")
    else:
        adj -= 0.5; rsn.append("Distributiefase: OBV daalt (Smart Money verkoopt in de stijging).")
        
    if alpha > 3.0:
        adj += 0.5; rsn.append(f"Outperformance: Verslaat de BIST 30 index met {format_full_percentage(alpha, 1)} (Positieve Alpha).")
    elif alpha < -3.0:
        adj -= 0.5; rsn.append(f"Onderprestatie: Loopt {format_full_percentage(abs(alpha), 1)} achter op de BIST 30.")
        
    return {"adjustment": adj, "alpha": alpha, "reasons": rsn}

def agent_4_macro_fx_devaluation_buffer(ticker, sector, macro_info):
    dev_risk = macro_info.get("dev_risk", False)
    is_exp = ticker in HARD_CURRENCY_EXPORTERS
    adj, rsn = 0.0, []
    if is_exp:
        if dev_risk: adj += 0.8; rsn.append("Sterke USD/EUR devaluatie-buffer actief: beschermt marges.")
        else: adj += 0.4; rsn.append("Structurele harde-valuta inkomsten en exportpositie.")
    else:
        if dev_risk: adj -= 0.4; rsn.append("Binnenlands lira-verdienmodel is kwetsbaar voor valutaschokken.")
        else: rsn.append("Binnenlands marktprofiel.")
    return {"adjustment": adj, "reasons": rsn}

def agent_5_debt_liquidity_interest_stress(info, q_metrics):
    dte = safe_float(info.get("debtToEquity"))
    net_debt = q_metrics["net_debt_full"]
    adj, rsn = 0.0, []
    if net_debt is not None and net_debt <= 0:
        adj += 0.7; rsn.append(f"Netto kaspositie ({format_full_number(abs(net_debt), 0, '₺')} kas over).")
    if dte is not None:
        if dte < 45.0: adj += 0.5; rsn.append(f"Lage schuldenratio (D/E: {format_full_percentage(dte)}).")
        elif dte > 110.0: adj -= 0.8; rsn.append(f"Hoge schuldenlast (D/E: {format_full_percentage(dte)}) — kwetsbaar voor TCMB rentes.")
    return {"adjustment": adj, "reasons": rsn if rsn else ["Geen schulddata gerapporteerd."]}

def agent_6_insider_buyback_dividend_structure(info):
    div = safe_float(info.get("dividendYield"))
    ff = safe_float(info.get("floatShares"))
    out = safe_float(info.get("sharesOutstanding"))
    adj, rsn = 0.0, []
    if div and div > 0:
        dy = div*100 if div < 1.0 else div
        if dy >= 3.0: adj += 0.3; rsn.append(f"Aantrekkelijk dividendrendement: {format_full_percentage(dy)}.")
    if ff and out and out > 0:
        ff_pct = (ff/out)*100
        if 15 <= ff_pct <= 45: adj += 0.2; rsn.append(f"Gezonde free-float structuur ({format_full_percentage(ff_pct)}).")
    return {"adjustment": adj, "reasons": rsn if rsn else ["Standaard BIST 30 structuur."]}

def agent_7_independent_risk_and_factcheck_auditor(a1, a2, a5, sr_info):
    t_score, f_score = a1["score"], a2["score"]
    dist_s1 = sr_info["Dist_S1_Pct"]
    
    if f_score is not None: data_quality, q_adj = "Volledig (Tech + Fundament)", 0.2
    else: data_quality, q_adj = "Beperkt (Geen P/E data)", -0.4
    
    if dist_s1 > 12.0: setup, risk = "Opgelet: Zwevend Aandeel (Te ver van S1)", "Hoog (Wacht op mean reversion)"
    elif f_score and f_score >= 6.2 and a1["rsi"] <= 48.0: setup, risk = "Koopwaardige Herstelkans (Lage RSI, Sterk Fundament)", "Gemiddeld (S1 Bodem)"
    elif (f_score and f_score < 4.2) or a5["adjustment"] <= -0.7: setup, risk = "Opgelet: Terecht Gedaald / Value Trap", "Hoog (Vermijd)"
    elif t_score >= 7.0: setup, risk = "Sterke Kwaliteitstrend & Momentum", "Laag tot Gemiddeld"
    else: setup, risk = "Neutraal / Volgen op Watchlist", "Gemiddeld"
    
    return {"setup": setup, "risk": risk, "quality": data_quality, "adjustment": q_adj, "reason": f"Classificatie: {setup} | Risicoprofiel: {risk}"}

def agent_8_execution_portfolio_telegram_dispatcher(ticker, company, price, sr_info, total_score, setup):
    atr = sr_info["ATR"]
    atr_stop = max(0.01, price - (1.5 * atr))
    atr_target = price + (2.5 * atr)
    risk = price - atr_stop
    reward = atr_target - price
    rr = reward / risk if risk > 0 else 0.0
    
    alert = ""
    if total_score >= 7.2:
        if rr >= 2.0:
            alert = f"✅ BIST 30 TOP SIGNAL: {ticker} (Score: {format_full_number(total_score, 1, '')}/10) | Setup: {setup} | R/R: {format_full_ratio(rr)} | Instap: {format_full_number(price)} | S1: {format_full_number(sr_info['S1'])} | Stop: {format_full_number(atr_stop)} | Doel: {format_full_number(atr_target)}"
        else:
            alert = f"❌ SIGNAL BLOCKED: {ticker} scoort hoog ({format_full_number(total_score, 1, '')}/10), maar Risk/Reward is te laag ({format_full_ratio(rr)}). Minimaal 2.0x vereist."
            
    return {"atr_stop": atr_stop, "atr_target": atr_target, "rr": rr, "alert": alert}

# ==============================================================================
# 5. HOOFD ANALYSE ENGINE & HISTORISCHE BACKTESTER
# ==============================================================================

def analyze_stock_pure_quant(ticker, macro):
    hist = get_history(ticker, "1y")
    if hist.empty or len(hist) < 30: return None
    price = safe_float(hist["Close"].iloc[-1])
    if not price: return None
    
    try:
        info = yf.Ticker(ticker).info or {}
    except Exception:
        info = {}
        
    company = info.get("longName") or info.get("shortName") or ticker
    sector = SECTOR_MAP.get(ticker, "BIST 30")
    
    sr = calculate_sr_levels_and_atr(hist)
    qm = get_quarterly_and_balance_metrics(ticker)
    
    a1 = agent_1_multi_timeframe_quant(ticker, hist, sr)
    a2 = agent_2_fundamental_quarterly_valuation(info, qm)
    a3 = agent_3_orderflow_and_alpha(ticker, hist, macro)
    a4 = agent_4_macro_fx_devaluation_buffer(ticker, sector, macro)
    a5 = agent_5_debt_liquidity_interest_stress(info, qm)
    a6 = agent_6_insider_buyback_dividend_structure(info)
    a7 = agent_7_independent_risk_and_factcheck_auditor(a1, a2, a5, sr)
    
    b_score = (0.48 * a1["score"]) + (0.52 * a2["score"]) if a2["score"] is not None else a1["score"] * 0.85
    tot_adj = a3["adjustment"] + a4["adjustment"] + a5["adjustment"] + a6["adjustment"] + a7["adjustment"]
    overall_score = round(min(10.0, max(1.0, b_score + tot_adj)), 1)
    
    a8 = agent_8_execution_portfolio_telegram_dispatcher(ticker, company, price, sr, overall_score, a7["setup"])
    
    return {
        "Bedrijf": company, "Ticker": ticker, "Sector": sector,
        "_price": price, "_score": overall_score, "_rr": a8["rr"], "_atr_stop": a8["atr_stop"], "_atr_target": a8["atr_target"],
        "Totaalscore": format_full_number(overall_score, 1, ""),
        "Type Setup": a7["setup"], "Risk/Reward": format_full_ratio(a8["rr"]),
        "Koers": format_full_number(price, 2, "₺"), "P/E": format_full_ratio(a2["pe"]),
        "Alpha vs Index": format_full_percentage(a3["alpha"], 2, True),
        "Steun S1": format_full_number(sr["S1"], 2, "₺"), "Weerstand R1": format_full_number(sr["R1"], 2, "₺"),
        "A1_Tech": "; ".join(a1["reasons"]), "A2_Fund": "; ".join(a2["reasons"]) if a2["reasons"] else "Geen fundament.",
        "A3_Orderflow": "; ".join(a3["reasons"]), "A4_Macro": "; ".join(a4["reasons"]),
        "A5_Debt": "; ".join(a5["reasons"]), "A6_Struct": "; ".join(a6["reasons"]),
        "A7_Audit": a7["reason"], "Alert": a8["alert"]
    }

@st.cache_data(ttl=900, show_spinner=False)
def run_historical_backtest(ticker, hold_days=10):
    hist = get_history(ticker, "2y")
    if hist.empty or len(hist) < 60: return None
    close, vol = hist["Close"], hist["Volume"]
    sma20 = close.rolling(20).mean()
    rsi = calculate_rsi(close)
    obv = calculate_obv(close, vol)
    obv_sma = obv.rolling(20).mean()
    
    trades = []
    i = 50
    while i < len(close) - hold_days:
        cp, csma, crsi, prsi = safe_float(close.iloc[i]), safe_float(sma20.iloc[i]), safe_float(rsi.iloc[i]), safe_float(rsi.iloc[i-1])
        cobv, csmaobv = safe_float(obv.iloc[i]), safe_float(obv_sma.iloc[i])
        
        if cp and csma and crsi and prsi and cobv and csmaobv:
            if cp > csma and 35 <= crsi <= 60 and crsi > prsi and cobv > csmaobv:
                exp = safe_float(close.iloc[i+hold_days])
                if exp:
                    ret = ((exp / cp) - 1) * 100
                    trades.append({
                        "In": str(close.index[i])[:10], "Koers In": format_full_number(cp),
                        "Uit": str(close.index[i+hold_days])[:10], "Koers Uit": format_full_number(exp),
                        "Rendement": format_full_percentage(ret, 2, True), "_ret": ret
                    })
                    i += hold_days
                    continue
        i += 1
        
    if not trades: return {"total": 0, "win_rate": 0, "avg_ret": 0, "df": pd.DataFrame()}
    wr = (sum(1 for r in trades if r["_ret"] > 0) / len(trades)) * 100
    avg = float(np.mean([r["_ret"] for r in trades]))
    return {"total": len(trades), "win_rate": wr, "avg_ret": avg, "df": pd.DataFrame(trades).drop(columns=["_ret"])}

def send_telegram_alert(token, chat_id, text):
    if not token or not chat_id: return False, "Vul token en chat ID in."
    try:
        url = f"https://api.telegram.org/bot{token.strip()}/sendMessage"
        data = urllib.parse.urlencode({"chat_id": chat_id.strip(), "text": text}).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=5) as r:
            if json.loads(r.read().decode("utf-8")).get("ok"): return True, "Verzonden!"
    except Exception as e: return False, f"Fout: {e}"

# ==============================================================================
# 6. STREAMLIT MULTI-TAB ENTERPRISE UI
# ==============================================================================

st.title("🏛️ BIST 30 Pure Quant Scanner 5.8 (Institutioneel)")
st.caption("Focus op Harde Data: Orderflow (OBV), Alpha, Elastiek-Penalty & Harde 1:2 Risk/Reward Dispatcher.")

with st.sidebar:
    st.header("⚙️ Instellingen")
    
    # 📚 Uitleg Begrippen in de zijbalk (Jip en Janneke)
    with st.expander("📚 Uitleg Begrippen (Jip en Janneke)", expanded=False):
        st.markdown("""
        **Alpha:** Meet de 'overwinning' van jouw aandeel ten opzichte van de hele markt. Als de beurs met 5% stijgt en jouw aandeel met 8%, is je Alpha +3%.
        
        **OBV:** De speurneus voor het 'grote geld' (banken/fondsen). Meet of ze stiekem grote hoeveelheden aandelen inslaan voordat de koers stijgt.
        
        **Elastiek-Penalty:** Een aandeel beweegt als een elastiekje. Is de prijs ineens extreem ver gestegen? Dan staat het elastiekje strak en klapt het hard terug. De scanner blokkeert dit.
        
        **Golden Bounce:** De perfecte stuitering op de steunlijn (de vloer) mét hoog volume. Het veiligste moment om te kopen.
        
        **Risk/Reward:** Riskeer 1 Lira om er 2 te winnen (1:2). De scanner blokkeert slechte kansen automatisch.
        
        **P/E (F/K):** Het prijskaartje. Hoeveel jaar duurt het om je inleg terug te verdienen? Hoe lager, hoe goedkoper.
        
        **ATR:** De zenuwachtigheidsmeter. Hoeveel schommelt de koers normaal per dag? Hiermee bepalen we de perfecte Stop-Loss.
        
        **Steun / Weerstand:** De onzichtbare vloer waar kopers klaarstaan (steun) en het plafond waar beleggers winst pakken (weerstand).
        """)
        
    if st.button("🚀 Start BIST 30 Quant Scan", type="primary", use_container_width=True):
        rows = []
        mac = get_macro_data()
        prog = st.progress(0, "Initialiseren...")
        for idx, t in enumerate(WATCHLIST):
            prog.progress((idx+1)/len(WATCHLIST), f"Agenten analyseren {t}...")
            r = analyze_stock_pure_quant(t, mac)
            if r: rows.append(r)
        prog.empty()
        if rows:
            df_all = pd.DataFrame(rows).sort_values("_score", ascending=False).reset_index(drop=True)
            st.session_state["pure_res"] = df_all
            st.success("Scan voltooid!")
            
    st.divider()
    st.header("📲 Telegram Bot")
    tg_token = st.text_input("Bot Token:", type="password")
    tg_chat = st.text_input("Chat ID:")

if "pure_res" in st.session_state:
    df_res = st.session_state["pure_res"]
    
    t1, t2, t3, t4 = st.tabs(["🏆 Quant Top 10 & Scan", "🤖 Diepte-Diagnostiek (8 Agents)", "💼 Portefeuille & Telegram", "📈 Historische Backtest"])
    
    with t1:
        st.subheader("🥇 Top 10 BIST 30 Aandelen")
        st.dataframe(df_res.head(10)[["Bedrijf", "Ticker", "Totaalscore", "Risk/Reward", "Type Setup", "Koers", "Alpha vs Index", "P/E"]], use_container_width=True, hide_index=True)
        st.subheader("📋 Volledige Ranglijst")
        st.dataframe(df_res[["Bedrijf", "Ticker", "Totaalscore", "Koers", "Steun S1", "Weerstand R1", "Risk/Reward", "P/E"]], use_container_width=True, hide_index=True)
        
    with t2:
        st.subheader("🤖 Diagnostiek van de 8 Agents")
        sel_t = st.selectbox("Kies aandeel:", df_res["Ticker"].tolist())
        for _, r in df_res.iterrows():
            with st.expander(f"{r['Bedrijf']} ({r['Ticker']}) — Score: {r['Totaalscore']}/10", expanded=(r["Ticker"] == sel_t)):
                if "✅" in r["Alert"]: st.success(r["Alert"])
                elif "❌" in r["Alert"]: st.error(r["Alert"])
                else: st.info("Geen Telegram-signaal (score te laag).")
                
                c1, c2, c3, c4 = st.columns(4)
                
                # Hier zitten de zwevende tooltips (hover text) op de blokken
                with c1: render_full_card("Totaalscore", r["Totaalscore"], r["Type Setup"], "#1f77b4", tooltip="Cijfer van 1 tot 10 gebaseerd op de checklisten van alle 8 de AI-agents.")
                with c2: render_full_card("Risk / Reward", r["Risk/Reward"], "Min. 2.0x voor signaal", "#2ca02c", tooltip="Risico/Rendement verhouding. Hoeveel Lira potentiële winst staat er tegenover elke Lira risico?")
                with c3: render_full_card("S1 / R1 Niveaus", f"{r['Steun S1']} / {r['Weerstand R1']}", "Fibonacci Pivots", "#ff7f0e", tooltip="De vloer (Steun S1) en het plafond (Weerstand R1) van het aandeel.")
                with c4: render_full_card("Alpha vs BIST 30", r["Alpha vs Index"], "Relatieve Sterkte", "#9467bd", tooltip="Hoeveel procent het aandeel harder (of zachter) stijgt dan het marktgemiddelde.")
                
                st.write(f"- **Agent 1 (Techniek, Elastiek, Bounce):** {r['A1_Tech']}")
                st.write(f"- **Agent 2 (Fundament & Marges):** {r['A2_Fund']}")
                st.write(f"- **Agent 3 (Institutionele Orderflow & Alpha):** {r['A3_Orderflow']}")
                st.write(f"- **Agent 4 (Macro & FX Buffer):** {r['A4_Macro']}")
                st.write(f"- **Agent 5 (Schuld & Rente-stress):** {r['A5_Debt']}")
                st.write(f"- **Agent 6 (Structuur & Dividend):** {r['A6_Struct']}")
                st.write(f"- **Agent 7 (Risico Auditor):** {r['A7_Audit']}")
                st.write(f"- **Agent 8 (Executie):** Stop: {format_full_number(r['_atr_stop'])} | Doel: {format_full_number(r['_atr_target'])}.")

    with t3:
        st.subheader("💼 Portefeuille Simulator")
        p1, p2 = st.columns(2)
        # Hier zitten de tooltips op de invulvelden (vraagtekens)
        with p1: cap = st.number_input("Totaal Kapitaal (TRY):", value=250000.0, help="Vul hier het totale bedrag in dat je beschikbaar hebt voor de beurs.")
        with p2: max_r = st.slider("Max verliesrisico per positie (%):", 0.5, 5.0, 1.5, help="Hoeveel procent van je totale geld mag je maximaal verliezen als het aandeel wegzakt en je nooduitgang (Stop-Loss) wordt geraakt?")
        
        sim = []
        for _, r in df_res.head(10).iterrows():
            p, s, t = r["_price"], r["_atr_stop"], r["_atr_target"]
            risk_sh = max(0.01, p - s)
            shares = int((cap * (max_r/100)) // risk_sh)
            sim.append({"Ticker": r["Ticker"], "Aandelen": format_full_integer(shares), "Waarde (TRY)": format_full_number(shares * p), "Max Verlies (TRY)": format_full_number(shares * risk_sh), "Winst (TRY)": format_full_number(shares * (t - p))})
        st.dataframe(pd.DataFrame(sim), use_container_width=True, hide_index=True)
        
        st.divider()
        if st.button("📨 Verstuur Top Alerts naar Telegram (Agent 8)"):
            alerts = [r["Alert"] for _, r in df_res.iterrows() if "✅" in r["Alert"]]
            if alerts:
                ok, m = send_telegram_alert(tg_token, tg_chat, "\n\n".join(alerts[:5]))
                if ok: st.success(m)
                else: st.error(m)
            else: st.info("Geen aandelen voldoen aan de harde 1:2 R/R drempel.")
            
    with t4:
        st.subheader("📈 Historische Strategie Backtester (OBV + RSI Bounce)")
        b1, b2 = st.columns(2)
        with b1: bt_sym = st.selectbox("Aandeel:", WATCHLIST)
        with b2: bt_days = st.slider("Houdperiode (dagen):", 5, 30, 10, help="Hoeveel dagen de scanner doet alsof hij het aandeel vasthoudt na een aankoop.")
        bt = run_historical_backtest(bt_sym, bt_days)
        if bt and bt["total"] > 0:
            c1, c2, c3 = st.columns(3)
            with c1: render_full_card("Aantal Trades", format_full_integer(bt["total"]), "Afgelopen 24 mnd", "#1f77b4", tooltip="Hoe vaak de scanner dit aandeel succesvol had kunnen kopen.")
            with c2: render_full_card("Win-Rate", format_full_percentage(bt["win_rate"], 1), "", "#2ca02c", tooltip="In hoeveel procent van de gevallen maakte je daadwerkelijk winst na aankoop?")
            with c3: render_full_card("Gem. Rendement", format_full_percentage(bt["avg_ret"], 2, True), "Per trade", "#ff7f0e", tooltip="De gemiddelde winst die je per aan/verkoop behaalde.")
            st.dataframe(bt["df"], use_container_width=True, hide_index=True)
        else: st.info("Geen signalen gevonden voor deze periode.")
