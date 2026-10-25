import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime

# ==========================================
# BIST SCANNER ULTIMATE 5.x — FULL EDITION (~900 LINES)
# ==========================================

st.set_page_config(
    page_title="BIST Scanner Ultimate 5.x Command Center",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Uitgebreide watchlist voor Borsa Istanbul (BIST 30 / BIST 100 kern)
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

# --- HELPER FUNCTIES ---

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
            rel_parts.append(f"Hoog volume ({vol_ratio:.2f}x gem. — sterke bevestiging)")
        elif vol_ratio <= 0.7:
            rel_parts.append(f"Laag volume ({vol_ratio:.2f}x gem. — zwakke overtuiging)")
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
    return pd.DataFrame(items).drop_duplicates(subset=["Titel"]).head(30)

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

def analyze_stock(ticker, macro_info):
    hist = get_history(ticker, "1y")
    if hist.empty or len(hist) < 30:
        return None

    close = hist["Close"].astype(float)
    price = safe_float(close.iloc[-1])
    if price is None or price <= 0:
        return None

    sma20 = safe_float(close.rolling(20).mean().iloc[-1])
    sma50 = safe_float(close.rolling(50).mean().iloc[-1])
    rsi_series = calculate_rsi(close)
    rsi = safe_float(rsi_series.iloc[-1])

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    macd_value = safe_float(macd.iloc[-1])
    macd_signal = safe_float(signal.iloc[-1])

    sr = calculate_sr_levels(hist)
    atr = sr["ATR"] if sr else (price * 0.03)
    vol_ratio = sr["Vol_Ratio"] if sr else None

    ret_1m = safe_float((price / close.iloc[-22] - 1) * 100) if len(close) >= 22 else None
    ret_3m = safe_float((price / close.iloc[-64] - 1) * 100) if len(close) >= 64 else None

    info = {}
    try:
        info = yf.Ticker(ticker).info or {}
    except Exception:
        info = {}

    company = str(info.get("longName") or info.get("shortName") or ticker)
    pe = safe_float(info.get("trailingPE"))
    pb = safe_float(info.get("priceToBook"))
    margin = safe_float(info.get("profitMargins"))
    revenue_growth = safe_float(info.get("revenueGrowth"))
    analyst_target = safe_float(info.get("targetMeanPrice"))
    analyst_count = int(info.get("numberOfAnalystOpinions") or 0)
    recommendation_raw = str(info.get("recommendationKey") or "n.b.").upper()
    recommendation_map = {
        "STRONG_BUY": "Sterk kopen", "BUY": "Kopen", "HOLD": "Houden",
        "UNDERPERFORM": "Onderpresteren", "SELL": "Verkopen"
    }
    recommendation = recommendation_map.get(recommendation_raw, "Niet beschikbaar")

    # Uitgebreide technische score (0-10)
    tech_points = 0.0
    tech_reasons = []
    if sma20 is not None:
        if price > sma20:
            tech_points += 2.0
            tech_reasons.append("Koers boven SMA20")
        else:
            tech_reasons.append("Koers onder SMA20")
    if sma50 is not None:
        if price > sma50:
            tech_points += 2.0
            tech_reasons.append("Koers boven SMA50")
        else:
            tech_reasons.append("Koers onder SMA50")
    if rsi is not None:
        if 45 <= rsi <= 65:
            tech_points += 2.0
            tech_reasons.append("RSI in gezonde zone")
        elif 30 <= rsi < 45:
            tech_points += 1.5
            tech_reasons.append("RSI laag; herstelkans")
        elif rsi < 30:
            tech_points += 1.0
            tech_reasons.append("RSI oversold")
        elif 65 < rsi <= 72:
            tech_points += 1.0
            tech_reasons.append("RSI sterk")
        else:
            tech_reasons.append("RSI hoog / oververhit")
    if macd_value is not None and macd_signal is not None:
        if macd_value > macd_signal:
            tech_points += 2.0
            tech_reasons.append("MACD boven signaallijn")
        else:
            tech_reasons.append("MACD onder signaallijn")
    if vol_ratio is not None and vol_ratio >= 1.3:
        tech_points += 1.0
        tech_reasons.append("Hoog handelsvolume")
    if ticker in ["THYAO.IS", "EREGL.IS", "SISE.IS", "TUPRS.IS", "FROTO.IS", "ASELS.IS"] and macro_info.get("dev_risk"):
        tech_points += 1.0
        tech_reasons.append("Sterke valutabuffer actief")
    tech_score = round(min(10.0, tech_points), 1)

    # Uitgebreide fundamentele score (0-10)
    fund_points = 0.0
    fund_max = 0.0
    fund_reasons = []
    if margin is not None:
        fund_max += 2.5
        if margin > 0.10:
            fund_points += 2.5
            fund_reasons.append("Hoge winstmarge (>10%)")
        elif margin > 0:
            fund_points += 1.2
            fund_reasons.append("Positieve winstmarge")
        else:
            fund_reasons.append("Negatieve winstmarge")
    if revenue_growth is not None:
        fund_max += 2.5
        if revenue_growth > 0.10:
            fund_points += 2.5
            fund_reasons.append("Sterke omzetgroei (>10%)")
        elif revenue_growth > 0:
            fund_points += 1.2
            fund_reasons.append("Positieve omzetgroei")
        else:
            fund_reasons.append("Krimpende omzet")
    if pe is not None and pe > 0:
        fund_max += 2.5
        if pe < 10:
            fund_points += 2.5
            fund_reasons.append("Aantrekkelijke P/E (<10)")
        elif pe < 20:
            fund_points += 1.5
            fund_reasons.append("Redelijke P/E (10-20)")
        else:
            fund_reasons.append("Hoge P/E (>20)")
    if pb is not None and pb > 0:
        fund_max += 2.5
        if pb < 1.5:
            fund_points += 2.5
            fund_reasons.append("Lage P/B (<1.5)")
        elif pb < 3.0:
            fund_points += 1.5
            fund_reasons.append("Gemiddelde P/B (1.5-3.0)")
        else:
            fund_reasons.append("Hoge P/B (>3.0)")

    fundamental_score = round((fund_points / fund_max) * 10.0, 1) if fund_max > 0 else None

    # Nieuwsanalyse integratie
    pos_news, neg_news, unc_news = get_stock_news(ticker, company)
    news_adjustment = 0.5 if len(pos_news) > len(neg_news) else (-0.7 if len(neg_news) > len(pos_news) else 0.0)

    if fundamental_score is not None:
        base_score = 0.50 * tech_score + 0.50 * fundamental_score
        data_quality = "Volledig (Techniek + Fundamentals)"
        quality_adj = 0.3
    else:
        base_score = tech_score * 0.85
        data_quality = "Beperkt (Alleen techniek)"
        quality_adj = -0.5

    bist_adj = 0.2 if macro_info.get("xu100_trend_positive") else -0.2
    overall_score = round(min(10.0, max(1.0, base_score + news_adjustment + quality_adj + bist_adj)), 1)

    if fundamental_score is not None and fundamental_score >= 6.0 and (rsi is not None and rsi < 48) and len(neg_news) == 0:
        setup_type = "Mogelijk koopwaardige herstelkans"
    elif (fundamental_score is not None and fundamental_score < 4.0) or len(neg_news) > len(pos_news):
        setup_type = "Opgelet: Zwakke fundamentals / Negatief nieuws"
    elif tech_score >= 7.0 and (fundamental_score is None or fundamental_score >= 5.5):
        setup_type = "Sterke trend & solide basis"
    else:
        setup_type = "Neutraal / Volgen"

    target_upside = ((analyst_target / price) - 1) * 100.0 if analyst_target and analyst_target > 0 else None

    return {
        "Bedrijf": company,
        "Ticker": ticker,
        "Koers (TRY)": round(price, 2),
        "Type Setup": setup_type,
        "Totaalscore": overall_score,
        "Technische score": tech_score,
        "Fundamentele score": fundamental_score,
        "P/E (FK)": round(pe, 2) if pe is not None and pe > 0 else None,
        "P/B (PD/DD)": round(pb, 2) if pb is not None and pb > 0 else None,
        "Winstmarge %": round(margin * 100, 2) if margin is not None else None,
        "Omzetgroei %": round(revenue_growth * 100, 2) if revenue_growth is not None else None,
        "Rendement 1m %": round(ret_1m, 2) if ret_1m is not None else None,
        "Rendement 3m %": round(ret_3m, 2) if ret_3m is not None else None,
        "RSI": round(rsi, 1) if rsi is not None else None,
        "MACD": round(macd_value, 3) if macd_value is not None else None,
        "Volume/20d gem.": vol_ratio,
        "S3": sr["S3"] if sr else None,
        "S2": sr["S2"] if sr else None,
        "S1": sr["S1"] if sr else None,
        "R1": sr["R1"] if sr else None,
        "R2": sr["R2"] if sr else None,
        "R3": sr["R3"] if sr else None,
        "SR_Relevantie": sr["Relevantie"] if sr else "N.B.",
        "ATR-stop (indicatief)": round(max(0.0, price - atr), 2),
        "ATR-doel (indicatief)": round(price + 1.5 * atr, 2),
        "Analistenkoersdoel": round(analyst_target, 2) if analyst_target is not None else None,
        "Koersdoelruimte %": round(target_upside, 1) if target_upside is not None else None,
        "Analistenadvies": recommendation,
        "Aantal analisten": analyst_count,
        "Positief nieuws": pos_news,
        "Negatief nieuws": neg_news,
        "Onduidelijk nieuws": unc_news,
        "Nieuws samenvatting": f"+{len(pos_news)} / -{len(neg_news)} / ?{len(unc_news)}",
        "Datadekking": data_quality,
        "Technische signalen": "; ".join(tech_reasons),
        "Fundamentele signalen": "; ".join(fund_reasons) if fund_reasons else "Geen fundamentele data"
    }

# --- UITGEBREIDE UI ---

st.title("BIST Scanner Ultimate 5.x — Command Center")
st.caption("Professionele kwantitatieve screeningstool voor Borsa Istanbul: Quant, P/E & P/B waarderingen, S1-S3/R1-R3 niveaus en KAP-nieuwsanalyse.")

with st.sidebar:
    st.header("Scaninstellingen")
    universe = st.multiselect("Aandelenuniversum", WATCHLIST, default=WATCHLIST)
    sort_by = st.selectbox(
        "Rangschikken op",
        ["Totaalscore", "Fundamentele score", "Technische score", "Rendement 1m %", "Rendement 3m %"]
    )
    min_data = st.selectbox("Datadekking filter", ["Alle resultaten", "Alleen met fundamentele data"])
    st.markdown("---")
    st.subheader("Over BIST 5.x")
    st.info("Dit command center combineert technische indicatoren, fundamentele ratios en live KAP-nieuwsstromen om sneller kansen te filteren.")

macro = get_macro_data()
m1, m2, m3 = st.columns(3)
with m1:
    st.metric(
        "USD/TRY Koers",
        f"₺{macro['usd_try']:.3f}" if macro["usd_try"] is not None else "Niet beschikbaar",
        delta="Devaluatie-buffer actief" if macro["dev_risk"] else "Stabiel"
    )
with m2:
    st.metric(
        "BIST 100 — 3m Rendement",
        f"{macro['xu100_return']:+.2f}%" if macro["xu100_return"] is not None else "Niet beschikbaar"
    )
with m3:
    st.metric(
        "BIST 100 Laatste Koers",
        f"{macro['xu100_price']:,.0f}" if macro["xu100_price"] is not None else "Niet beschikbaar"
    )

# --- BIST 100 STEUN & WEERSTAND ---
st.subheader("BIST 100 (XU100) — Macro Steun & Weerstand (S1–S3 & R1–R3)")
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
    st.caption(f"**Marktcontext & Relevantie:** {bsr['Relevantie']}")
else:
    st.info("BIST 100 niveaus momenteel niet beschikbaar.")

st.divider()

# --- GEOPOLITIEKE & MACRO TOP 3 ---
st.subheader("Geopolitieke & Macro 'Top 3' Thematische Selectie")
col_t1, col_t2, col_t3 = st.columns(3)
with col_t1:
    st.info("**1. THYAO.IS & PGSUS.IS (Luchtvaart / Harde Valuta)**\n\nProfiteren direct van internationale inkomsten in USD/EUR als natuurlijke devaluatie-buffer.")
with col_t2:
    st.info("**2. TUPRS.IS & ASELS.IS (Energie & Defensie)**\n\nSterke strategische marktpositie en robuuste orderportefeuilles tijdens geopolitieke spanningen.")
with col_t3:
    st.info("**3. KCHOL.IS & BIMAS.IS (Conglomeraat & Basisconsumptie)**\n\nGediversifieerde balansen en inflatiebestendige bedrijfsmodellen voor defensieve stabiliteit.")

st.divider()

# --- NIEUWSMONITOR ---
st.subheader("KAP & Marktnieuwsmonitor (Gecategoriseerd)")
news_df = get_news()
if news_df.empty:
    st.info("Geen nieuwsitems opgehaald.")
else:
    n_col1, n_col2, n_col3 = st.columns(3)
    with n_col1:
        st.markdown("#### Positieve signalen")
        pos_df = news_df[news_df["Signaal"] == "Positief"]
        for _, item in pos_df.head(6).iterrows():
            st.markdown(f"- [{item['Titel']}]({item['Link']}) <br><small>{item['Bron']}</small>", unsafe_allow_html=True)
    with n_col2:
        st.markdown("#### Negatieve signalen")
        neg_df = news_df[news_df["Signaal"] == "Negatief"]
        for _, item in neg_df.head(6).iterrows():
            st.markdown(f"- [{item['Titel']}]({item['Link']}) <br><small>{item['Bron']}</small>", unsafe_allow_html=True)
    with n_col3:
        st.markdown("#### Te controleren / Onduidelijk")
        unc_df = news_df[news_df["Signaal"] == "Onduidelijk / Te controleren"]
        for _, item in unc_df.head(6).iterrows():
            st.markdown(f"- [{item['Titel']}]({item['Link']}) <br><small>{item['Bron']}</small>", unsafe_allow_html=True)

st.divider()

# --- SCANNER & RANGSLIJST ---
st.subheader("Aandelenranglijst & Top 10 Command Center")
if st.button("Start Volledige Ultimate 5.x Scan", type="primary", use_container_width=True):
    if not universe:
        st.warning("Selecteer minimaal één aandeel.")
    else:
        rows = []
        progress = st.progress(0, text="Bezig met geavanceerde analyse...")
        for i, ticker in enumerate(universe):
            progress.progress((i + 1) / len(universe), text=f"Analyseren: {ticker}")
            result = analyze_stock(ticker, macro)
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
                st.session_state["bist_scan_ultimate"] = results
                st.success(f"Scan voltooid: {len(results)} aandelen geanalyseerd.")

if "bist_scan_ultimate" in st.session_state:
    results = st.session_state["bist_scan_ultimate"]

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
    st.download_button("Download resultaten als CSV", data=csv, file_name="bist_scanner_ultimate_results.csv", mime="text/csv")

    st.subheader("Detailanalyse per aandeel (S1-S3, R1-R3 & KAP-nieuws)")
    for _, row in results.iterrows():
        with st.expander(f"{row['Bedrijf']} ({row['Ticker']}) — Score: {row['Totaalscore']}/10 — {row['Type Setup']}"):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Totaalscore", f"{row['Totaalscore']}/10")
            c2.metric("Technische score", f"{row['Technische score']}/10")
            c3.metric("Fundamentele score", f"{row['Fundamentele score']}/10" if pd.notna(row["Fundamentele score"]) else "N.B.")
            c4.metric("P/E · P/B", f"{row['P/E (FK)'] or 'N.B.'} · {row['P/B (PD/DD)'] or 'N.B.'}")

            st.markdown("#### Steun en Weerstand (S1–S3 & R1–R3)")
            sr_df = pd.DataFrame([
                {"Niveau": "Weerstand R3", "Prijs": f"₺{row['R3']}"},
                {"Niveau": "Weerstand R2", "Prijs": f"₺{row['R2']}"},
                {"Niveau": "Weerstand R1", "Prijs": f"₺{row['R1']}"},
                {"Niveau": "Huidige Koers", "Prijs": f"₺{row['Koers (TRY)']}"},
                {"Niveau": "Steun S1", "Prijs": f"₺{row['S1']}"},
                {"Niveau": "Steun S2", "Prijs": f"₺{row['S2']}"},
                {"Niveau": "Steun S3", "Prijs": f"₺{row['S3']}"},
            ])
            st.table(sr_df)
            st.write(f"**Relevantie:** {row['SR_Relevantie']}")

            st.markdown("#### KAP & Bedrijfsnieuws")
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

            st.markdown("#### Onderbouwing")
            st.write(f"**Techniek:** {row['Technische signalen']}")
            st.write(f"**Fundamentals:** {row['Fundamentele signalen']} (Marge: {row['Winstmarge %']}% · Omzetgroei: {row['Omzetgroei %']}%)")
            st.write(f"**Analisten:** {row['Analistenadvies']} (Doel: ₺{row['Analistenkoersdoel']})")
