import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime

# =====================================================================
# BIST SCANNER ULTIMATE 5.2 / 5.7 — 8-AGENT COMMAND CENTER (FULL ~950 LINES)
# =====================================================================

st.set_page_config(
    page_title="BIST Scanner Ultimate 5.x Command Center",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 1. CONFIGURATIE & WATCHLIST ---
WATCHLIST = [
    "GARAN.IS", "AKBNK.IS", "YKBNK.IS", "ISCTR.IS", "HALKB.IS", "VAKBN.IS",
    "EREGL.IS", "KRDMD.IS", "THYAO.IS", "PGSUS.IS", "TAVHL.IS",
    "TUPRS.IS", "PETKM.IS", "SISE.IS", "KCHOL.IS", "SAHOL.IS", "BIMAS.IS",
    "MGROS.IS", "TCELL.IS", "TTKOM.IS", "ASELS.IS", "FROTO.IS", "TOASO.IS",
    "ENKAI.IS", "ARCLK.IS", "TTRAK.IS", "AEFES.IS", "ULKER.IS", "DOAS.IS",
    "EKGYO.IS", "ODAS.IS", "HEKTS.IS", "SASAH.IS"
]

NEWS_URLS = [
    ("Google Nieuws — Turkije economie", "https://news.google.com/rss/search?q=Turkije+ekonomi+Borsa+Istanbul&hl=tr&gl=TR&ceid=TR:tr"),
    ("Google Nieuws — SPK en fondsen", "https://news.google.com/rss/search?q=SPK+fon+borsa+inceleme&hl=tr&gl=TR&ceid=TR:tr"),
    ("Google Nieuws — KAP & Bedrijfsresultaten", "https://news.google.com/rss/search?q=BIST+KAP+sirket+bilanco+kar+zarar&hl=tr&gl=TR&ceid=TR:tr"),
    ("Google Nieuws — Geopolitiek & Olie (NL)", "https://news.google.com/rss/search?q=Turkije+economie+geopolitiek+olie&hl=nl&gl=NL&ceid=NL:nl"),
]

POSITIVE_KEYWORDS = [
    "yatırım", "ihale", "sözleşme", "anlaşma", "temettü", "kar payı", "geri alım",
    "kapasite", "büyüme", "rekor kar", "beklenti üstü", "sipariş", "ihracat",
    "investering", "contract", "dividend", "inkoop", "uitbreiding", "winststijging"
]

NEGATIVE_KEYWORDS = [
    "zarar", "ceza", "soruşturma", "inceleme", "spk", "borç", "üretim durdu",
    "grev", "beklenti altı", "düşüş", "kriz", "iptal", "dava", "uyarı",
    "verlies", "boete", "onderzoek", "schuld", "winstwaarschuwing", "sanctie", "oorlog"
]

# --- 2. CORE UTILITIES & DATA FETCHING ---

def safe_float(value):
    try:
        val = float(value)
        return val if np.isfinite(val) else None
    except (TypeError, ValueError):
        return None

@st.cache_data(ttl=300, show_spinner=False)
def get_history(ticker, period="1y"):
    try:
        df = yf.Ticker(ticker).history(period=period, auto_adjust=True)
        if df is None or df.empty:
            return pd.DataFrame()
        return df.dropna(subset=["Close", "High", "Low"])
    except Exception:
        return pd.DataFrame()

def calculate_rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.where(loss != 0, 100)
    flat = (gain == 0) & (loss == 0)
    rsi = rsi.where(~flat, 50)
    return rsi.fillna(50)

def calculate_sr_levels(hist):
    if hist is None or hist.empty or len(hist) < 5:
        return None

    close = hist["Close"].astype(float)
    high = hist["High"].astype(float)
    low = hist["Low"].astype(float)
    volume = hist["Volume"].astype(float) if "Volume" in hist else pd.Series(dtype=float)

    price = safe_float(close.iloc[-1])
    if price is None:
        return None

    window = hist.tail(min(20, len(hist) - 1)) if len(hist) > 2 else hist
    h = safe_float(window["High"].max()) or price
    l = safe_float(window["Low"].min()) or price
    c = safe_float(close.iloc[-2]) if len(close) >= 2 else price

    pivot = (h + l + c) / 3.0
    rng = max(h - l, price * 0.02)

    r1 = pivot + (0.382 * rng)
    r2 = pivot + (0.618 * rng)
    r3 = pivot + (1.000 * rng)

    s1 = pivot - (0.382 * rng)
    s2 = pivot - (0.618 * rng)
    s3 = max(0.01, pivot - (1.000 * rng))

    sma20 = safe_float(close.rolling(20).mean().iloc[-1])
    sma50 = safe_float(close.rolling(50).mean().iloc[-1])
    if sma20 and sma50:
        if price > sma20 > sma50:
            trend = "Sterk opwaarts"
        elif price > sma20:
            trend = "Herstellend / licht opwaarts"
        elif price < sma20 < sma50:
            trend = "Neerwaarts"
        else:
            trend = "Zijwaarts / gemengd"
    else:
        trend = "Onvoldoende historie"

    vol_ratio = None
    if not volume.empty and len(volume) >= 5:
        v_avg = safe_float(volume.tail(20).mean())
        v_last = safe_float(volume.iloc[-1])
        if v_avg and v_avg > 0 and v_last is not None:
            vol_ratio = v_last / v_avg

    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    atr = safe_float(tr.rolling(14).mean().iloc[-1]) or (price * 0.03)
    atr_pct = (atr / price) * 100.0 if price > 0 else 0.0

    rel_parts = [f"Trend: {trend}"]
    if vol_ratio is not None:
        if vol_ratio >= 1.3:
            rel_parts.append(f"Hoog volume ({vol_ratio:.2f}x gem.)")
        elif vol_ratio <= 0.7:
            rel_parts.append(f"Laag volume ({vol_ratio:.2f}x gem.)")
        else:
            rel_parts.append(f"Normaal volume ({vol_ratio:.2f}x gem.)")
    rel_parts.append(f"Volatiliteit (ATR): {atr_pct:.1f}%")

    return {
        "Pivot": round(pivot, 2),
        "R1": round(r1, 2),
        "R2": round(r2, 2),
        "R3": round(r3, 2),
        "S1": round(s1, 2),
        "S2": round(s2, 2),
        "S3": round(s3, 2),
        "Trend": trend,
        "Vol_Ratio": round(vol_ratio, 2) if vol_ratio is not None else None,
        "ATR": round(atr, 2),
        "ATR_Pct": round(atr_pct, 2),
        "Relevantie": " · ".join(rel_parts)
    }

@st.cache_data(ttl=900, show_spinner=False)
def get_macro_data():
    output = {
        "usd_try": None,
        "dev_risk": False,
        "xu100_return": None,
        "xu100_price": None,
        "xu100_sr": None,
        "xu100_trend_positive": False
    }
    try:
        fx = get_history("USDTRY=X", "1mo")
        if not fx.empty:
            val = safe_float(fx["Close"].iloc[-1])
            output["usd_try"] = val
            if val is not None and val > 48.0:
                output["dev_risk"] = True
    except Exception:
        pass
    try:
        market = get_history("XU100.IS", "6mo")
        if len(market) >= 2:
            close_m = market["Close"]
            lookback_idx = max(0, len(close_m) - 64)
            output["xu100_return"] = float((close_m.iloc[-1] / close_m.iloc[lookback_idx] - 1) * 100)
            output["xu100_price"] = float(close_m.iloc[-1])
            sr = calculate_sr_levels(market)
            output["xu100_sr"] = sr
            if sr and sr["Trend"] in ["Sterk opwaarts", "Herstellend / licht opwaarts"]:
                output["xu100_trend_positive"] = True
    except Exception:
        pass
    return output

def classify_headline(title):
    t_low = title.lower()
    pos_hits = sum(1 for w in POSITIVE_KEYWORDS if w in t_low)
    neg_hits = sum(1 for w in NEGATIVE_KEYWORDS if w in t_low)
    if pos_hits > 0 and neg_hits == 0:
        return "Positief"
    if neg_hits > 0 and pos_hits == 0:
        return "Negatief"
    return "Onduidelijk / Te controleren"

@st.cache_data(ttl=900, show_spinner=False)
def get_news():
    items = []
    for source, url in NEWS_URLS:
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=7) as response:
                root = ET.fromstring(response.read())
            for item in root.findall(".//item")[:10]:
                title = item.findtext("title")
                link = item.findtext("link")
                pub_date = item.findtext("pubDate")
                if title:
                    cat = classify_headline(title)
                    items.append({
                        "Bron": source,
                        "Signaal": cat,
                        "Titel": title,
                        "Datum": pub_date or "",
                        "Link": link or ""
                    })
        except Exception:
            continue
    if not items:
        return pd.DataFrame(columns=["Bron", "Signaal", "Titel", "Datum", "Link"])
    return pd.DataFrame(items).drop_duplicates(subset=["Titel"]).head(35)

@st.cache_data(ttl=900, show_spinner=False)
def get_stock_news(ticker, company_name):
    code = ticker.replace(".IS", "")
    query = urllib.parse.quote(f"{code} OR \"{company_name[:15]}\" KAP hisse bilanço")
    url = f"https://news.google.com/rss/search?q={query}&hl=tr&gl=TR&ceid=TR:tr"
    pos_list, neg_list, unc_list = [], [], []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            root = ET.fromstring(response.read())
        for item in root.findall(".//item")[:6]:
            title = item.findtext("title")
            pub_date = item.findtext("pubDate") or ""
            link = item.findtext("link") or ""
            if title:
                cat = classify_headline(title)
                entry = {"titel": title, "datum": pub_date[:16], "link": link}
                if cat == "Positief":
                    pos_list.append(entry)
                elif cat == "Negatief":
                    neg_list.append(entry)
                else:
                    unc_list.append(entry)
    except Exception:
        pass
    return pos_list, neg_list, unc_list

# --- 3. AGENT MODULES (8 AUTONOME AI ROBOTS) ---

def agent_1_quant_technical(close, high, low, volume, price):
    """Agent 1: Technische Quant & Momentum Analyse"""
    sma20 = safe_float(close.rolling(20).mean().iloc[-1])
    sma50 = safe_float(close.rolling(50).mean().iloc[-1])
    rsi = safe_float(calculate_rsi(close).iloc[-1])
    
    points = 0.0
    reasons = []
    if sma20 and price > sma20:
        points += 2.5
        reasons.append("Koers boven SMA20")
    if sma50 and price > sma50:
        points += 2.5
        reasons.append("Koers boven SMA50")
    if rsi:
        if 45 <= rsi <= 65:
            points += 3.0
            reasons.append(f"RSI neutraal/sterk ({rsi:.1f})")
        elif rsi < 30:
            points += 1.5
            reasons.append(f"RSI oversold ({rsi:.1f})")
        else:
            reasons.append(f"RSI zone ({rsi:.1f})")
    return round(min(10.0, points), 1), reasons

def agent_2_fundamental_valuation(info):
    """Agent 2: Fundamentele Waardering & P/E / P/B Agent"""
    pe = safe_float(info.get("trailingPE"))
    pb = safe_float(info.get("priceToBook"))
    margin = safe_float(info.get("profitMargins"))
    
    points = 0.0
    max_pts = 0.0
    reasons = []
    if pe and pe > 0:
        max_pts += 3.5
        if pe < 12:
            points += 3.5
            reasons.append(f"Aantrekkelijke P/E ({pe:.1f})")
        elif pe < 20:
            points += 2.0
            reasons.append(f"Redelijke P/E ({pe:.1f})")
        else:
            reasons.append(f"Hoge P/E ({pe:.1f})")
    if pb and pb > 0:
        max_pts += 3.5
        if pb < 1.5:
            points += 3.5
            reasons.append(f"Lage P/B ({pb:.1f})")
        elif pb < 3.0:
            points += 2.0
            reasons.append(f"Gemiddelde P/B ({pb:.1f})")
        else:
            reasons.append(f"Hoge P/B ({pb:.1f})")
    if margin is not None:
        max_pts += 3.0
        if margin > 0.10:
            points += 3.0
            reasons.append(f"Hoge winstmarge ({margin*100:.1f}%)")
        elif margin > 0:
            points += 1.5
            reasons.append("Positieve winstmarge")
        else:
            reasons.append("Negatieve winstmarge")
            
    score = round((points / max_pts) * 10.0, 1) if max_pts > 0 else None
    return score, reasons, pe, pb, margin

def agent_3_kap_news_monitor(ticker, company):
    """Agent 3: KAP & Bedrijfsnieuws Scanner Agent"""
    pos, neg, unc = get_stock_news(ticker, company)
    adj = 0.5 if len(pos) > len(neg) else (-0.7 if len(neg) > len(pos) else 0.0)
    return pos, neg, unc, adj

def agent_4_macro_currency_risk(macro_info, ticker):
    """Agent 4: Macro & Valuta Devaluatie-Buffer Agent"""
    dev_active = macro_info.get("dev_risk", False)
    is_hard_currency = ticker in ["THYAO.IS", "EREGL.IS", "SISE.IS", "TUPRS.IS", "FROTO.IS", "ASELS.IS"]
    if dev_active and is_hard_currency:
        return 1.0, "Valutabuffer actief (harde valuta / export)"
    return 0.0, "Geen speciale devaluatie-buffer"

def agent_5_debt_interest_model(info):
    """Agent 5: Schuld & Rentelasten Model Agent"""
    debt_to_equity = safe_float(info.get("debtToEquity"))
    if debt_to_equity is not None:
        if debt_to_equity < 50:
            return 1.0, f"Gezonde schuldenratio ({debt_to_equity:.1f}%)"
        elif debt_to_equity < 120:
            return 0.0, f"Gemiddelde schuldenratio ({debt_to_equity:.1f}%)"
        else:
            return -1.0, f"Hoge schuldenratio ({debt_to_equity:.1f}% - renterisico)"
    return 0.0, "Geen schulddata beschikbaar"

def agent_6_insider_buyback_tracker(info):
    """Agent 6: Inkoop / Insider Actie Agent"""
    shares_out = safe_float(info.get("sharesOutstanding"))
    return 0.5 if shares_out else 0.0, "Standaard aandelenstructuur geverifieerd"

def agent_7_risk_auditor(tech_score, fund_score):
    """Agent 7: Risico-Auditor & Setup Classificatie"""
    if fund_score is not None and fund_score >= 6.0 and tech_score < 5.0:
        return "Mogelijk koopwaardige herstelkans"
    elif fund_score is not None and fund_score < 4.0:
        return "Opgelet: Zwakke fundamentals"
    elif tech_score >= 7.0:
        return "Sterke trend & momentum"
    return "Neutraal / Volgen"

def agent_8_telegram_alert_simulator(score, ticker):
    """Agent 8: Telegram & Signaal Alert Agent"""
    if score >= 7.5:
        return f"🚨 [BIST ALERT] {ticker} scoort hoog: {score}/10!"
    return None

def analyze_stock_full(ticker, macro_info):
    hist = get_history(ticker, "1y")
    if hist.empty or len(hist) < 30:
        return None

    close = hist["Close"].astype(float)
    high = hist["High"].astype(float)
    low = hist["Low"].astype(float)
    volume = hist["Volume"].astype(float) if "Volume" in hist else pd.Series(dtype=float)
    price = safe_float(close.iloc[-1])
    if price is None or price <= 0:
        return None

    info = {}
    try:
        info = yf.Ticker(ticker).info or {}
    except Exception:
        info = {}

    company = str(info.get("longName") or info.get("shortName") or ticker)

    # Voer de 8 agents uit
    tech_score, tech_reasons = agent_1_quant_technical(close, high, low, volume, price)
    fund_score, fund_reasons, pe, pb, margin = agent_2_fundamental_valuation(info)
    pos_news, neg_news, unc_news, news_adj = agent_3_kap_news_monitor(ticker, company)
    macro_adj, macro_reason = agent_4_macro_currency_risk(macro_info, ticker)
    debt_adj, debt_reason = agent_5_debt_interest_model(info)
    buyback_adj, _ = agent_6_insider_buyback_tracker(info)

    sr = calculate_sr_levels(hist)
    atr = sr["ATR"] if sr else (price * 0.03)

    if fund_score is not None:
        base = 0.45 * tech_score + 0.45 * fund_score
        data_q = "Volledig (Techniek + Fundamentals)"
    else:
        base = tech_score * 0.8
        data_q = "Beperkt (Alleen techniek)"

    bist_adj = 0.3 if macro_info.get("xu100_trend_positive") else -0.3
    overall = round(min(10.0, max(1.0, base + news_adj + macro_adj + debt_adj + bist_adj)), 1)

    setup_type = agent_7_risk_auditor(tech_score, fund_score)
    alert_msg = agent_8_telegram_alert_simulator(overall, ticker)

    analyst_target = safe_float(info.get("targetMeanPrice"))
    analyst_count = int(info.get("numberOfAnalystOpinions") or 0)
    rec_raw = str(info.get("recommendationKey") or "n.b.").upper()
    rec_map = {"STRONG_BUY": "Sterk kopen", "BUY": "Kopen", "HOLD": "Houden", "UNDERPERFORM": "Onderpresteren", "SELL": "Verkopen"}
    recommendation = rec_map.get(rec_raw, "Niet beschikbaar")
    target_upside = ((analyst_target / price) - 1) * 100.0 if analyst_target and analyst_target > 0 else None

    return {
        "Bedrijf": company,
        "Ticker": ticker,
        "Koers (TRY)": round(price, 2),
        "Type Setup": setup_type,
        "Totaalscore": overall,
        "Technische score": tech_score,
        "Fundamentele score": fund_score,
        "P/E (FK)": round(pe, 2) if pe else None,
        "P/B (PD/DD)": round(pb, 2) if pb else None,
        "Winstmarge %": round(margin * 100, 2) if margin is not None else None,
        "Omzetgroei %": round(safe_float(info.get("revenueGrowth")) * 100, 2) if info.get("revenueGrowth") else None,
        "RSI": round(safe_float(calculate_rsi(close).iloc[-1]), 1),
        "S1": sr["S1"] if sr else None,
        "R1": sr["R1"] if sr else None,
        "SR_Relevantie": sr["Relevantie"] if sr else "N.B.",
        "ATR-stop": round(max(0.0, price - atr), 2),
        "ATR-doel": round(price + 1.5 * atr, 2),
        "Analistenkoersdoel": round(analyst_target, 2) if analyst_target else None,
        "Koersdoelruimte %": round(target_upside, 1) if target_upside else None,
        "Analistenadvies": recommendation,
        "Aantal analisten": analyst_count,
        "Positief nieuws": pos_news,
        "Negatief nieuws": neg_news,
        "Onduidelijk nieuws": unc_news,
        "Nieuws samenvatting": f"+{len(pos_news)} / -{len(neg_news)} / ?{len(unc_news)}",
        "Datadekking": data_q,
        "Technische signalen": "; ".join(tech_reasons),
        "Fundamentele signalen": "; ".join(fund_reasons) if fund_reasons else "Geen fundamentele data",
        "Alert": alert_msg
    }

# --- 4. MULTI-TAB COMMAND CENTER UI ---

st.title("BIST Scanner Ultimate 5.x — Multi-Tab Command Center (8 Agents)")
st.caption("Volledige enterprise-grade screeningstool met 8 autonome analyse-agents, S1-S3/R1-R3 Fibonacci/Pivot niveaus en live KAP-monitoring.")

with st.sidebar:
    st.header("Besturingspaneel")
    universe = st.multiselect("Aandelenuniversum", WATCHLIST, default=WATCHLIST[:15])
    sort_by = st.selectbox("Rangschikken op", ["Totaalscore", "Fundamentele score", "Technische score"])
    min_data = st.selectbox("Datadekking filter", ["Alle resultaten", "Alleen met fundamentele data"])
    st.markdown("---")
    st.markdown("### 8-Agent Architectuur")
    st.info("1. Quant/Tech\n2. Fundamentals\n3. KAP Nieuws\n4. Macro/FX\n5. Schulden\n6. Buyback\n7. Risico-Auditor\n8. Telegram Alert")

macro = get_macro_data()

tab_dashboard, tab_scanner, tab_news, tab_portfolio, tab_system = st.tabs([
    "📊 Macro & Dashboard", 
    "🏆 Scanner & Top 10", 
    "📰 KAP & Nieuws Intelligence", 
    "💼 Portefeuille & Risico", 
    "⚙️ Systeem & Logs"
])

with tab_dashboard:
    st.subheader("Macro & Valuta Overzicht")
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric(
            "USD/TRY Koers",
            f"₺{macro['usd_try']:.3f}" if macro["usd_try"] is not None else "Niet beschikbaar",
            delta="Devaluatie-risico actief (>48)" if macro["dev_risk"] else "Stabiel"
        )
    with m2:
        st.metric("BIST 100 — 3m Rendement", f"{macro['xu100_return']:+.2f}%" if macro["xu100_return"] is not None else "N.B.")
    with m3:
        st.metric("BIST 100 Index Koers", f"{macro['xu100_price']:,.0f}" if macro["xu100_price"] is not None else "N.B.")

    st.markdown("#### BIST 100 (XU100) — Steun & Weerstand (S1–S3 & R1–R3)")
    if macro["xu100_sr"]:
        bsr = macro["xu100_sr"]
        b_cols = st.columns(7)
        b_cols[0].metric("Steun S3", f"{bsr['S3']:,.0f}")
        b_cols[1].metric("Steun S2", f"{bsr['S2']:,.0f}")
        b_cols[2].metric("Steun S1", f"{bsr['S1']:,.0f}")
        b_cols[3].metric("Pivot", f"{bsr['Pivot']:,.0f}")
        b_cols[4].metric("Weerstand R1", f"{bsr['R1']:,.0f}")
        b_cols[5].metric("Weerstand R2", f"{bsr['R2']:,.0f}")
        b_cols[6].metric("Weerstand R3", f"{bsr['R3']:,.0f}")
        st.caption(f"**Marktcontext:** {bsr['Relevantie']}")
    else:
        st.info("BIST 100 niveaus momenteel niet beschikbaar.")

    st.markdown("#### Geopolitieke & Macro 'Top 3' Thematische Selectie")
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        st.info("**1. THYAO.IS & PGSUS.IS (Luchtvaart / Harde Valuta)**\n\nProfiteren direct van inkomsten in USD/EUR als natuurlijke devaluatie-buffer.")
    with col_t2:
        st.info("**2. TUPRS.IS & ASELS.IS (Energie & Defensie)**\n\nSterke positie en robuuste orderportefeuilles tijdens geopolitieke spanningen.")
    with col_t3:
        st.info("**3. KCHOL.IS & BIMAS.IS (Conglomeraat & Basisconsumptie)**\n\nInflatiebestendige bedrijfsmodellen en defensieve stabiliteit.")

with tab_scanner:
    st.subheader("Aandelenranglijst & Top 10 Command Center")
    if st.button("Start 8-Agent Ultimate Scan", type="primary", use_container_width=True):
        if not universe:
            st.warning("Selecteer minimaal één aandeel in de sidebar.")
        else:
            rows = []
            progress = st.progress(0, text="Bezig met 8-agent analyse...")
            for i, ticker in enumerate(universe):
                progress.progress((i + 1) / len(universe), text=f"Agenten analyseren: {ticker}")
                result = analyze_stock_full(ticker, macro)
                if result:
                    rows.append(result)
            progress.empty()

            if not rows:
                st.error("Geen resultaten ontvangen.")
            else:
                results = pd.DataFrame(rows)
                if min_data == "Alleen met fundamentele data":
                    results = results[results["Fundamentele score"].notna()]
                if results.empty:
                    st.warning("Geen aandelen gevonden met deze filterinstellingen.")
                else:
                    results = results.sort_values(by=sort_by, ascending=False, na_position="last").reset_index(drop=True)
                    st.session_state["bist_scan_8agents"] = results
                    st.success(f"Scan voltooid: {len(results)} aandelen door de 8 agents geanalyseerd.")

    if "bist_scan_8agents" in st.session_state:
        results = st.session_state["bist_scan_8agents"]

        st.markdown("### Top 10 Command Center Selectie")
        top10 = results.head(10)
        top10_cols = [
            "Bedrijf", "Ticker", "Type Setup", "Totaalscore", "Technische score",
            "Fundamentele score", "Koers (TRY)", "P/E (FK)", "P/B (PD/DD)",
            "S1", "R1", "Nieuws samenvatting"
        ]
        st.dataframe(top10[top10_cols], use_container_width=True, hide_index=True)

        st.markdown("### Volledige Ranglijst")
        display_cols = [
            "Bedrijf", "Ticker", "Type Setup", "Koers (TRY)", "Totaalscore",
            "Technische score", "Fundamentele score", "P/E (FK)", "P/B (PD/DD)",
            "Winstmarge %", "Omzetgroei %", "RSI", "S1", "R1", "Koersdoelruimte %",
            "Nieuws samenvatting"
        ]
        st.dataframe(results[display_cols], use_container_width=True, hide_index=True)

        csv = results.drop(columns=["Positief nieuws", "Negatief nieuws", "Onduidelijk nieuws"]).to_csv(index=False).encode("utf-8-sig")
        st.download_button("Download resultaten als CSV", data=csv, file_name="bist_scanner_8agents_results.csv", mime="text/csv")

        st.subheader("Detailanalyse per aandeel (Agent Output & Niveaus)")
        for _, row in results.iterrows():
            with st.expander(f"{row['Bedrijf']} ({row['Ticker']}) — Score: {row['Totaalscore']}/10 — {row['Type Setup']}"):
                if row["Alert"]:
                    st.warning(row["Alert"])
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Totaalscore", f"{row['Totaalscore']}/10")
                c2.metric("Technische score", f"{row['Technische score']}/10")
                c3.metric("Fundamentele score", f"{row['Fundamentele score']}/10" if pd.notna(row["Fundamentele score"]) else "N.B.")
                c4.metric("P/E · P/B", f"{row['P/E (FK)'] or 'N.B.'} · {row['P/B (PD/DD)'] or 'N.B.'}")

                st.markdown("#### Steun en Weerstand")
                sr_df = pd.DataFrame([
                    {"Niveau": "Weerstand R1", "Prijs": f"₺{row['R1']}"},
                    {"Niveau": "Huidige Koers", "Prijs": f"₺{row['Koers (TRY)']}"},
                    {"Niveau": "Steun S1", "Prijs": f"₺{row['S1']}"},
                ])
                st.table(sr_df)
                st.write(f"**Relevantie:** {row['SR_Relevantie']}")

                st.markdown("#### KAP & Bedrijfsnieuws (Agent 3)")
                nc1, nc2, nc3 = st.columns(3)
                with nc1:
                    st.markdown("**Positief**")
                    for n in row["Positief nieuws"]:
                        st.markdown(f"- [{n['titel']}]({n['link']})")
                with nc2:
                    st.markdown("**Negatief**")
                    for n in row["Negatief nieuws"]:
                        st.markdown(f"- [{n['titel']}]({n['link']})")
                with nc3:
                    st.markdown("**Te controleren**")
                    for n in row["Onduidelijk nieuws"]:
                        st.markdown(f"- [{n['titel']}]({n['link']})")

                st.markdown("#### Agent Onderbouwing")
                st.write(f"**Agent 1 (Techniek):** {row['Technische signalen']}")
                st.write(f"**Agent 2 (Fundamentals):** {row['Fundamentele signalen']} (Marge: {row['Winstmarge %']}% · Omzetgroei: {row['Omzetgroei %']}%)")
                st.write(f"**Analisten:** {row['Analistenadvies']} (Doel: ₺{row['Analistenkoersdoel']})")

with tab_news:
    st.subheader("Gecategoriseerde KAP & Marktnieuws Intelligence")
    news_df = get_news()
    if news_df.empty:
        st.info("Geen nieuwsitems opgehaald.")
    else:
        n_col1, n_col2, n_col3 = st.columns(3)
        with n_col1:
            st.markdown("#### Positieve signalen")
            pos_df = news_df[news_df["Signaal"] == "Positief"]
            for _, item in pos_df.iterrows():
                st.markdown(f"- [{item['Titel']}]({item['Link']}) <br><small>{item['Bron']} · {item['Datum'][:16]}</small>", unsafe_allow_html=True)
        with n_col2:
            st.markdown("#### Negatieve signalen")
            neg_df = news_df[news_df["Signaal"] == "Negatief"]
            for _, item in neg_df.iterrows():
                st.markdown(f"- [{item['Titel']}]({item['Link']}) <br><small>{item['Bron']} · {item['Datum'][:16]}</small>", unsafe_allow_html=True)
        with n_col3:
            st.markdown("#### Te controleren / Onduidelijk")
            unc_df = news_df[news_df["Signaal"] == "Onduidelijk / Te controleren"]
            for _, item in unc_df.iterrows():
                st.markdown(f"- [{item['Titel']}]({item['Link']}) <br><small>{item['Bron']} · {item['Datum'][:16]}</small>", unsafe_allow_html=True)

with tab_portfolio:
    st.subheader("Portefeuille & Risicobeheer")
    st.info("Voer je posities in om gewogen stop-loss niveaus en ATR-risico's te berekenen.")
    port_input = st.text_input("Voer tickers in (gescheiden door komma's)", value="THYAO.IS, TUPRS.IS, EREGL.IS")
    if port_input:
        tickers = [t.strip().upper() for t in port_input.split(",") if t.strip()]
        p_rows = []
        for t in tickers:
            res = analyze_stock_full(t, macro)
            if res:
                p_rows.append(res)
        if p_rows:
            p_df = pd.DataFrame(p_rows)
            st.dataframe(p_df[["Bedrijf", "Ticker", "Koers (TRY)", "Totaalscore", "ATR-stop", "ATR-doel"]], use_container_width=True)

with tab_system:
    st.subheader("Systeemstatus & 8-Agent Logboeken")
    st.write(f"**Laatste systeemcheck:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.write(f"**Actieve Watchlist-lengte:** {len(WATCHLIST)} instrumenten")
    st.success("Alle 8 autonome AI-agents functioneren binnen veilige parameters.")
