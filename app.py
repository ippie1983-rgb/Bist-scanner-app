import os
import json
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

# ==============================================================================
# CONFIGURATIE & SECTOR MAPPING
# ==============================================================================
st.set_page_config(page_title="BIST Scanner 3.6 — Pro Hedgefund Edition + Audit", layout="wide")

WATCHLIST = [
    "GARAN.IS", "AKBNK.IS", "YKBNK.IS", "ISCTR.IS", "HALKB.IS", "VAKBN.IS",
    "EREGL.IS", "KRDMD.IS", "THYAO.IS", "PGSUS.IS", "TAVHL.IS",
    "TUPRS.IS", "PETKM.IS", "SISE.IS", "KCHOL.IS", "SAHOL.IS", "BIMAS.IS",
    "MGROS.IS", "TCELL.IS", "TTKOM.IS", "ASELS.IS", "FROTO.IS", "TOASO.IS",
    "ENKAI.IS", "ARCLK.IS", "TTRAK.IS", "AEFES.IS", "ULKER.IS", "DOAS.IS", "EKGYO.IS"
]

SECTOR_MAP = {
    "GARAN.IS": "Banken", "AKBNK.IS": "Banken", "YKBNK.IS": "Banken", "ISCTR.IS": "Banken", "HALKB.IS": "Banken", "VAKBN.IS": "Banken",
    "EREGL.IS": "Staal & Metaal", "KRDMD.IS": "Staal & Metaal",
    "THYAO.IS": "Luchtvaart", "PGSUS.IS": "Luchtvaart", "TAVHL.IS": "Luchtvaart",
    "TUPRS.IS": "Energie", "PETKM.IS": "Energie",
    "SISE.IS": "Conglomeraten", "KCHOL.IS": "Conglomeraten", "SAHOL.IS": "Conglomeraten", "ENKAI.IS": "Conglomeraten",
    "BIMAS.IS": "Retail", "MGROS.IS": "Retail",
    "TCELL.IS": "Telecom", "TTKOM.IS": "Telecom",
    "ASELS.IS": "Defensie/Tech",
    "FROTO.IS": "Automotive", "TOASO.IS": "Automotive", "ARCLK.IS": "Automotive", "TTRAK.IS": "Automotive", "DOAS.IS": "Automotive",
    "AEFES.IS": "Voeding & Dranken", "ULKER.IS": "Voeding & Dranken",
    "EKGYO.IS": "Vastgoed"
}

NEWS_URLS = [
    ("Google Nieuws — Turkije economie", "https://news.google.com/rss/search?q=Turkiye+ekonomi+Borsa+Istanbul&hl=tr&gl=TR&ceid=TR:tr"),
    ("Google Nieuws — SPK en fondsen", "https://news.google.com/rss/search?q=SPK+fon+borsa+inceleme&hl=tr&gl=TR&ceid=TR:tr"),
    ("Google Nieuws — KAP & Bedrijfsresultaten", "https://news.google.com/rss/search?q=BIST+KAP+sirket+bilanco+kar+zarar&hl=tr&gl=TR&ceid=TR:tr"),
    ("Google Nieuws — Geopolitiek & Olie (NL)", "https://news.google.com/rss/search?q=Turkije+economie+geopolitiek+olie&hl=nl&gl=NL&ceid=NL:nl"),
]

POSITIVE_KEYWORDS = ["yatırım", "ihale", "sözleşme", "anlaşma", "temettü", "kar payı", "geri alım", "kapasite", "büyüme", "rekor kar", "beklenti üstü", "sipariş", "ihracat", "investering", "contract", "dividend", "inkoop", "uitbreiding", "winststijging"]
NEGATIVE_KEYWORDS = ["zarar", "ceza", "soruşturma", "inceleme", "spk", "borç", "üretim durdu", "grev", "beklenti altı", "düşüş", "kriz", "iptal", "dava", "uyarı", "verlies", "boete", "onderzoek", "schuld", "winstwaarschuwing", "sanctie", "oorlog"]

def safe_float(v):
    try:
        val = float(v)
        return val if np.isfinite(val) else None
    except:
        return None

@st.cache_data(ttl=300, show_spinner=False)
def get_history(ticker, period="1y", interval="1d"):
    try:
        df = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=True)
        if df is None or df.empty: return pd.DataFrame()
        return df.dropna(subset=["Close", "High", "Low"])
    except:
        return pd.DataFrame()

@st.cache_data(ttl=900, show_spinner=False)
def get_quarterly_metrics(ticker):
    q_data = {"last_quarter_date": None, "q_rev_m": None, "q_net_m": None, "qoq_rev_growth": None, "qoq_net_growth": None}
    try:
        q_inc = yf.Ticker(ticker).quarterly_income_stmt
        if q_inc is not None and not q_inc.empty:
            cols = q_inc.columns
            q_data["last_quarter_date"] = str(cols[0])[:10]
            rev_keys = [k for k in q_inc.index if "Total Revenue" in str(k) or "Operating Revenue" in str(k)]
            net_keys = [k for k in q_inc.index if "Net Income" in str(k)]
            if rev_keys:
                r0 = safe_float(q_inc.loc[rev_keys[0], cols[0]])
                if r0 is not None: q_data["q_rev_m"] = round(r0 / 1e6, 1)
                if len(cols) >= 2:
                    r1 = safe_float(q_inc.loc[rev_keys[0], cols[1]])
                    if r0 is not None and r1 and r1 > 0: q_data["qoq_rev_growth"] = round(((r0 / r1) - 1) * 100, 1)
            if net_keys:
                n0 = safe_float(q_inc.loc[net_keys[0], cols[0]])
                if n0 is not None:
                    q_data["q_net_m"] = round(n0 / 1e6, 1)
                if len(cols) >= 2:
                    n1 = safe_float(q_inc.loc[net_keys[0], cols[1]])
                    if n0 is not None and n1 and abs(n1) > 0:
                        q_data["qoq_net_growth"] = round(((n0 - n1) / abs(n1)) * 100, 1)
    except:
        pass
    return q_data

def calculate_rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.where(loss != 0, 100)
    flat = (gain == 0) & (loss == 0)
    rsi = rsi.where(~flat, 50)
    return rsi.fillna(50)

def calculate_sr_levels(hist):
    if hist is None or hist.empty or len(hist) < 5: return None
    close = hist["Close"].astype(float)
    high = hist["High"].astype(float)
    low = hist["Low"].astype(float)
    volume = hist["Volume"].astype(float) if "Volume" in hist else pd.Series(dtype=float)

    price = safe_float(close.iloc[-1])
    if price is None: return None

    window = hist.tail(min(20, len(hist)-1)) if len(hist) > 2 else hist
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
        if price > sma20 > sma50: trend = "Sterk opwaarts"
        elif price > sma20: trend = "Herstellend / licht opwaarts"
        elif price < sma20 < sma50: trend = "Neerwaarts"
        else: trend = "Zijwaarts / gemengd"
    else:
        trend = "Onvoldoende historie"

    vol_ratio = None
    if not volume.empty and len(volume) >= 5:
        v_avg = safe_float(volume.tail(20).mean())
        v_last = safe_float(volume.iloc[-1])
        if v_avg and v_avg > 0 and v_last is not None:
            vol_ratio = v_last / v_avg

    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    atr = safe_float(tr.rolling(14).mean().iloc[-1]) or (price * 0.03)
    atr_pct = (atr / price) * 100.0 if price > 0 else 0.0

    rel_parts = [f"Trend: {trend}"]
    if vol_ratio is not None:
        if vol_ratio >= 1.3: rel_parts.append(f"Hoog volume ({vol_ratio:.2f}x gem.)")
        elif vol_ratio <= 0.7: rel_parts.append(f"Laag volume ({vol_ratio:.2f}x gem.)")
        else: rel_parts.append(f"Normaal volume ({vol_ratio:.2f}x gem.)")
    rel_parts.append(f"ATR: {atr_pct:.1f}%")

    return {
        "Pivot": round(pivot, 2), "R1": round(r1, 2), "R2": round(r2, 2), "R3": round(r3, 2),
        "S1": round(s1, 2), "S2": round(s2, 2), "S3": round(s3, 2),
        "Trend": trend, "Vol_Ratio": round(vol_ratio, 2) if vol_ratio is not None else None,
        "ATR": round(atr, 2), "ATR_Pct": round(atr_pct, 2), "Relevantie": " · ".join(rel_parts)
    }

@st.cache_data(ttl=900, show_spinner=False)
def get_macro_data():
    output = {"usd_try": None, "dev_risk": False, "xu100_return": None, "xu100_price": None, "xu100_sr": None}
    try:
        fx = get_history("USDTRY=X", "1mo")
        if not fx.empty:
            val = safe_float(fx["Close"].iloc[-1])
            output["usd_try"] = val
            if val is not None and val > 48.0: output["dev_risk"] = True
    except:
        pass
    try:
        market = get_history("XU100.IS", "6mo")
        if len(market) >= 2:
            close_m = market["Close"]
            lookback_idx = max(0, len(close_m) - 64)
            output["xu100_return"] = float((close_m.iloc[-1] / close_m.iloc[lookback_idx] - 1) * 100)
            output["xu100_price"] = float(close_m.iloc[-1])
            output["xu100_sr"] = calculate_sr_levels(market)
    except:
        pass
    return output

def classify_headline(title):
    t_low = title.lower()
    pos_hits = sum(1 for w in POSITIVE_KEYWORDS if w in t_low)
    neg_hits = sum(1 for w in NEGATIVE_KEYWORDS if w in t_low)
    if pos_hits > 0 and neg_hits == 0: return "Positief"
    if neg_hits > 0 and pos_hits == 0: return "Negatief"
    return "Onduidelijk"

@st.cache_data(ttl=900, show_spinner=False)
def get_news():
    items = []
    for source, url in NEWS_URLS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=7) as resp:
                root = ET.fromstring(resp.read())
            for item in root.findall(".//item")[:8]:
                title = item.findtext("title")
                link = item.findtext("link")
                pub_date = item.findtext("pubDate")
                if title:
                    items.append({"Bron": source, "Signaal": classify_headline(title), "Titel": title, "Datum": pub_date or "", "Link": link or ""})
        except:
            continue
    return pd.DataFrame(items) if items else pd.DataFrame(columns=["Bron", "Signaal", "Titel", "Datum", "Link"])

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
        for item in root.findall(".//item")[:8]:
            title = item.findtext("title")
            pub_date = item.findtext("pubDate") or ""
            link = item.findtext("link") or ""
            if title:
                cat = classify_headline(title)
                entry = {"titel": title, "datum": pub_date[:16], "link": link}
                if cat == "Positief": pos_list.append(entry)
                elif cat == "Negatief": neg_list.append(entry)
                else: unc_list.append(entry)
    except:
        pass
    return pos_list, neg_list, unc_list

@st.cache_data(ttl=900, show_spinner=False)
def run_financial_news_agent(ticker, company, fundamentals_dict, q_metrics, headlines_tuple, macro_usd_try, api_key):
    if not api_key: return None
    try:
        headlines_text = "\n".join([f"- {h}" for h in headlines_tuple]) if headlines_tuple else "Geen recente headlines."
        prompt = f"""
Analyseer aandeel {company} ({ticker}) op basis van kwartaalcijfers, waardering en KAP/nieuwsberichten.
USD/TRY: {macro_usd_try}
PE: {fundamentals_dict.get('pe')} | PB: {fundamentals_dict.get('pb')} | Winstmarge: {fundamentals_dict.get('margin_pct')}%
Laatste kwartaal omzet: {q_metrics.get('q_rev_m')}M, Nettowinst: {q_metrics.get('q_net_m')}M (QoQ omzetgroei: {q_metrics.get('qoq_rev_growth')}%)
Headlines:
{headlines_text}

Geef een JSON output terug met:
- sentiment_label ("Sterk Positief", "Positief", "Neutraal", "Negatief", "Sterk Negatief")
- score_adjustment (getal tussen -2.0 en +2.0)
- kwartaal_analyse (2-3 zinnen Nederlands)
- kap_en_nieuws_duiding (2-3 zinnen Nederlands)
- belangrijkste_katalysator (1 zin)
- grootste_risico (1 zin)
"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={urllib.parse.quote(api_key.strip())}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
                "responseSchema": {
                    "type": "OBJECT",
                    "properties": {
                        "sentiment_label": {"type": "STRING"},
                        "score_adjustment": {"type": "NUMBER"},
                        "kwartaal_analyse": {"type": "STRING"},
                        "kap_en_nieuws_duiding": {"type": "STRING"},
                        "belangrijkste_katalysator": {"type": "STRING"},
                        "grootste_risico": {"type": "STRING"}
                    },
                    "required": ["sentiment_label", "score_adjustment", "kwartaal_analyse", "kap_en_nieuws_duiding", "belangrijkste_katalysator", "grootste_risico"]
                }
            }
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            return json.loads(resp_data["candidates"][0]["content"]["parts"][0]["text"])
    except:
        return None

@st.cache_data(ttl=900, show_spinner=False)
def run_audit_agent(ticker, company, ai_report, q_metrics, headlines_tuple, api_key):
    """
    Validator / Fact-Check Agent: Controleert of de AI-rapportage geen hallucinaties of 
    onverifieerbare claims bevat op basis van de werkelijke kwartaaldata en nieuwsheadlines.
    """
    if not api_key or not ai_report: return None
    try:
        headlines_text = "\n".join([f"- {h}" for h in headlines_tuple]) if headlines_tuple else "Geen headlines."
        prompt = f"""
Je bent een strenge Compliance & Risk Officer / Fact-Checker bij een hedgefund.
Controleer het volgende AI-gegenereerde rapport voor aandeel {company} ({ticker}) op feitelijke juistheid, hallucinaties en onverifieerbare beweringen.

ECHTE BRON-DATA & KWARTAALCIJFERS:
- Omzet: {q_metrics.get('q_rev_m')}M TRY | Nettowinst: {q_metrics.get('q_net_m')}M TRY
- Ruwe Headlines / KAP:
{headlines_text}

TE CONTROLEREN AI RAPPORT:
- Sentiment: {ai_report.get('sentiment_label')}
- Kwartaal Analyse: {ai_report.get('kwartaal_analyse')}
- KAP Duiding: {ai_report.get('kap_en_nieuws_duiding')}
- Katalysator: {ai_report.get('belangrijkste_katalysator')}
- Risico: {ai_report.get('grootste_risico')}

INSTRUCTIES:
Beoordeel of de claims in het AI-rapport kloppen met de bovenstaande data en of er sprake is van verzonnen informatie.
Geef JSON terug met:
- audit_status ("Goedgekeurd", "Waarschuwing", "Afgekeurd / Hallucinatie gedetecteerd")
- betrouwbaarheid_score (getal van 1 tot 10)
- audit_opmerkingen (Korte toelichting in het Nederlands of alle claims feitelijk onderbouwd zijn)
"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={urllib.parse.quote(api_key.strip())}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
                "responseSchema": {
                    "type": "OBJECT",
                    "properties": {
                        "audit_status": {"type": "STRING"},
                        "betrouwbaarheid_score": {"type": "NUMBER"},
                        "audit_opmerkingen": {"type": "STRING"}
                    },
                    "required": ["audit_status", "betrouwbaarheid_score", "audit_opmerkingen"]
                }
            }
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            return json.loads(resp_data["candidates"][0]["content"]["parts"][0]["text"])
    except:
        return None

def analyze_stock(ticker, macro_info, api_key=None, use_ai_agent=True):
    hist = get_history(ticker, "1y")
    if hist.empty or len(hist) < 30: return None
    close = hist["Close"].astype(float)
    price = safe_float(close.iloc[-1])
    if price is None or price <= 0: return None

    sma20 = safe_float(close.rolling(20).mean().iloc[-1])
    sma50 = safe_float(close.rolling(50).mean().iloc[-1])
    rsi = safe_float(calculate_rsi(close).iloc[-1])

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_val = safe_float((ema12 - ema26).iloc[-1])
    macd_sig = safe_float((ema12 - ema26).ewm(span=9, adjust=False).mean().iloc[-1])

    sr = calculate_sr_levels(hist)
    atr = sr["ATR"] if sr else (price * 0.03)
    vol_ratio = sr["Vol_Ratio"] if sr else None

    info = {}
    try: info = yf.Ticker(ticker).info or {}
    except: pass

    company = str(info.get("longName") or info.get("shortName") or ticker)
    pe = safe_float(info.get("trailingPE"))
    pb = safe_float(info.get("priceToBook"))
    margin = safe_float(info.get("profitMargins"))
    revenue_growth = safe_float(info.get("revenueGrowth"))
    analyst_target = safe_float(info.get("targetMeanPrice"))
    recommendation = str(info.get("recommendationKey") or "n.b.").upper()
    q_metrics = get_quarterly_metrics(ticker)

    # Scoring
    tech_points, tech_reasons = 0.0, []
    if sma20 and price > sma20: tech_points += 2.5; tech_reasons.append("Koers boven SMA20")
    if sma50 and price > sma50: tech_points += 2.5; tech_reasons.append("Koers boven SMA50")
    if rsi and 40 <= rsi <= 70: tech_points += 2.5; tech_reasons.append(f"RSI in gezonde zone ({rsi:.1f})")
    if macd_val and macd_sig and macd_val > macd_sig: tech_points += 2.5; tech_reasons.append("MACD bullish")
    tech_score = round(min(10.0, tech_points), 1)

    fund_points, fund_max = 0.0, 0.0
    fund_reasons = []
    if margin is not None:
        fund_max += 5.0
        if margin > 0.08: fund_points += 5.0; fund_reasons.append(f"Sterke winstmarge ({margin*100:.1f}%)")
        else: fund_points += 2.0; fund_reasons.append(f"Lage winstmarge ({margin*100:.1f}%)")
    if pe is not None and pe > 0:
        fund_max += 5.0
        if pe < 15: fund_points += 5.0; fund_reasons.append(f"Aantrekkelijke K/W ({pe:.1f}x)")
        else: fund_points += 2.0; fund_reasons.append(f"Hoge K/W ({pe:.1f}x)")
    fund_score = round((fund_points / fund_max * 10.0), 1) if fund_max > 0 else 5.0

    pos_news, neg_news, unc_news = get_stock_news(ticker, company)
    all_headlines = tuple([n["titel"] for n in (pos_news + neg_news + unc_news)])

    ai_report = None
    audit_report = None
    if use_ai_agent and api_key:
        fundamentals_dict = {"pe": pe, "pb": pb, "margin_pct": round(margin*100, 1) if margin else None}
        ai_report = run_financial_news_agent(ticker, company, fundamentals_dict, q_metrics, all_headlines, macro_info.get("usd_try"), api_key)
        if ai_report:
            audit_report = run_audit_agent(ticker, company, ai_report, q_metrics, all_headlines, api_key)

    news_adj = safe_float(ai_report.get("score_adjustment")) if ai_report else 0.0
    if not ai_report:
        if len(pos_news) > len(neg_news): news_adj = 0.5
        elif len(neg_news) > len(pos_news): news_adj = -0.5

    total_score = round(min(10.0, max(1.0, (0.5 * tech_score) + (0.5 * fund_score) + news_adj)), 1)
    ai_sentiment = str(ai_report.get("sentiment_label", "Neutraal")) if ai_report else "Neutraal"

    return {
        "Ticker": ticker, "Bedrijf": company, "Koers": round(price, 2),
        "Totaal_Cijfer": total_score, "Tech_Cijfer": tech_score, "Fund_Cijfer": fund_score,
        "AI_Sentiment": ai_sentiment, "AI_Correctie": round(news_adj, 1),
        "AI_Rapport": ai_report, "Audit_Rapport": audit_report,
        "Kwartaal_Data": q_metrics, "RSI": round(rsi, 1) if rsi else None,
        "Trend": sr["Trend"] if sr else "Onbekend", "ATR": round(atr, 2),
        "Pivot": sr["Pivot"] if sr else None, "R1": sr["R1"] if sr else None, "R2": sr["R2"] if sr else None, "R3": sr["R3"] if sr else None,
        "S1": sr["S1"] if sr else None, "S2": sr["S2"] if sr else None, "S3": sr["S3"] if sr else None,
        "Stop_Loss": round(max(0.01, price - (1.5 * atr)), 2), "Doel_ATR": round(price + (2.5 * atr), 2),
        "K/W (PE)": round(pe, 1) if pe else None, "Winstmarge (%)": round(margin * 100, 1) if margin else None,
        "Analist_Doel": round(analyst_target, 2) if analyst_target else None, "Analist_Advies": recommendation,
        "Tech_Redenen": tech_reasons, "Fund_Redenen": fund_reasons,
        "Relevantie_SR": sr["Relevantie"] if sr else "",
        "Pos_Nieuws": pos_news, "Neg_Nieuws": neg_news, "Unc_Nieuws": unc_news
    }

# ==============================================================================
# STREAMLIT DASHBOARD UI
# ==============================================================================
st.title("📊 BIST Scanner 3.6 — Pro Hedgefund Edition + AI Audit")
st.markdown("Geavanceerde BIST-scanner inclusief **KAP/Kwartaal AI-Agent** en een **AI Fact-Check & Audit Agent** ter voorkoming van hallucinaties.")

with st.sidebar:
    st.header("🤖 AI-Agent & Audit Instellingen")
    default_key = os.environ.get("GEMINI_API_KEY", "")
    if not default_key:
        try: default_key = st.secrets.get("GEMINI_API_KEY", "")
        except: default_key = ""

    gemini_api_key = st.text_input("Gemini API Key:", value=default_key, type="password")
    use_ai_agent = st.toggle("Activeer AI-Agent & Fact-Checker", value=True)

    st.divider()
    selected_tickers = st.multiselect("Selecteer BIST-aandelen:", options=WATCHLIST, default=WATCHLIST[:10])
    min_score = st.slider("Minimale Totaalscore:", 1.0, 10.0, 5.0, 0.5)
    if st.button("🔄 Cache wissen & Verversen"):
        st.cache_data.clear()
        st.rerun()

with st.spinner("Macro-indicatoren laden..."):
    macro = get_macro_data()

col1, col2, col3, col4 = st.columns(4)
col1.metric("💱 USD/TRY Koers", f"₺{macro['usd_try']:.2f}" if macro["usd_try"] else "N/B", "Devaluatie-buffer actief" if macro["dev_risk"] else "Stabiel")
col2.metric("📈 BIST 100 (XU100)", f"{macro['xu100_price']:,.0f}" if macro["xu100_price"] else "N/B", f"{macro['xu100_return']:.1f}% (3m)" if macro["xu100_return"] is not None else None)
col3.metric("🧭 BIST 100 Trend", macro["xu100_sr"]["Trend"] if macro["xu100_sr"] else "N/B")
col4.metric("🛡️ XU100 S1 / R1", f"{macro['xu100_sr']['S1']:,.0f} / {macro['xu100_sr']['R1']:,.0f}" if macro["xu100_sr"] else "N/B")

st.divider()

results = []
if selected_tickers:
    progress_bar = st.progress(0, text="Aandelen en AI-audit laden...")
    for idx, t in enumerate(selected_tickers):
        res = analyze_stock(t, macro, api_key=gemini_api_key, use_ai_agent=use_ai_agent)
        if res and res["Totaal_Cijfer"] >= min_score:
            results.append(res)
        progress_bar.progress((idx + 1) / len(selected_tickers), text=f"Geanalyseerd: {t}")
    progress_bar.empty()

if not results:
    st.warning("Geen aandelen gevonden die voldoen aan de criteria.")
else:
    results = sorted(results, key=lambda x: x["Totaal_Cijfer"], reverse=True)
    df_overview = pd.DataFrame(results)

    tab1, tab2, tab3, tab4 = st.tabs([
        "🏆 Quant Ranglijst",
        "📐 Steun & Weerstand",
        "🤖 AI-Agent & Fact-Check Audit",
        "📰 Macro & KAP Nieuwsfeed"
    ])

    with tab1:
        st.subheader("Portefeuille Ranglijst & Scores")
        display_cols = ["Ticker", "Bedrijf", "Koers", "Totaal_Cijfer", "Tech_Cijfer", "Fund_Cijfer", "AI_Sentiment", "AI_Correctie", "RSI", "Trend", "K/W (PE)"]
        st.dataframe(df_overview[display_cols], use_container_width=True, hide_index=True)

    with tab2:
        st.subheader("Pivot Points, Steun & Weerstand")
        sr_cols = ["Ticker", "Koers", "Trend", "S3", "S2", "S1", "Pivot", "R1", "R2", "R3", "Stop_Loss", "Doel_ATR"]
        st.dataframe(df_overview[sr_cols], use_container_width=True, hide_index=True)

    with tab3:
        st.subheader("Gedetailleerde AI-Agent & Fact-Check Audit")
        chosen = st.selectbox("Kies een aandeel:", [r["Ticker"] for r in results])
        stock_detail = next(r for r in results if r["Ticker"] == chosen)

        c1, c2, c3 = st.columns(3)
        c1.metric(f"{stock_detail['Bedrijf']} ({stock_detail['Ticker']})", f"₺{stock_detail['Koers']}", f"Cijfer: {stock_detail['Totaal_Cijfer']}/10")
        c2.metric("Steun S1 / Weerstand R1", f"₺{stock_detail['S1']} / ₺{stock_detail['R1']}", f"Pivot: ₺{stock_detail['Pivot']}")
        c3.metric("ATR Stop-Loss / Doel", f"₺{stock_detail['Stop_Loss']} / ₺{stock_detail['Doel_ATR']}", f"Analist Doel: ₺{stock_detail['Analist_Doel'] or 'N/B'}")

        st.markdown("### 🤖 Financiële & KAP AI-Agent Analyse")
        ai_rep = stock_detail.get("AI_Rapport")
        audit_rep = stock_detail.get("Audit_Rapport")
        q_info = stock_detail.get("Kwartaal_Data", {})

        if q_info.get("last_quarter_date"):
            qc1, qc2, qc3 = st.columns(3)
            qc1.metric("Laatste Kwartaal", q_info["last_quarter_date"])
            qc2.metric("Kwartaalomzet", f"₺{q_info['q_rev_m']:,.1f}M" if q_info.get("q_rev_m") else "N/B", f"{q_info['qoq_rev_growth']}% QoQ" if q_info.get("qoq_rev_growth") else None)
            qc3.metric("Kwartaal Nettowinst", f"₺{q_info['q_net_m']:,.1f}M" if q_info.get("q_net_m") else "N/B", f"{q_info['qoq_net_growth']}% QoQ" if q_info.get("qoq_net_growth") else None)

        if ai_rep:
            st.success(f"**AI Sentiment:** {ai_rep.get('sentiment_label')} (Score-impact: {stock_detail['AI_Correctie']:+g})\n\n**📊 Kwartaal Analyse:** {ai_rep.get('kwartaal_analyse')}\n\n**📰 KAP Duiding:** {ai_rep.get('kap_en_nieuws_duiding')}")
            k_col1, k_col2 = st.columns(2)
            k_col1.info(f"🚀 **Katalysator:** {ai_rep.get('belangrijkste_katalysator')}")
            k_col2.warning(f"⚠️ **Risico:** {ai_rep.get('grootste_risico')}")
            
            # Audit Resultaat Section
            st.markdown("---")
            st.markdown("### 🛡️ AI Fact-Check & Audit Resultaat (Validator Agent)")
            if audit_rep:
                status = audit_rep.get("audit_status", "Onbekend")
                score = audit_rep.get("betrouwbaarheid_score", 0)
                remarks = audit_rep.get("audit_opmerkingen", "Geen opmerkingen.")
                
                if "Goedgekeurd" in status:
                    st.success(f"**Audit Status:** {status} (Betrouwbaarheid: {score}/10)\n\n**Oordeel:** {remarks}")
                elif "Waarschuwing" in status:
                    st.warning(f"**Audit Status:** {status} (Betrouwbaarheid: {score}/10)\n\n**Oordeel:** {remarks}")
                else:
                    st.error(f"**Audit Status:** {status} (Betrouwbaarheid: {score}/10)\n\n**Oordeel:** {remarks}")
            else:
                st.info("Geen audit rapport beschikbaar.")
        else:
            st.info("Vul je Gemini API Key in de sidebar in voor het live AI-rapport en de fact-check audit.")

        st.markdown("**📰 Ruwe Bronberichten & KAP-headlines**")
        all_stock_news = [("🟢 Positief", n) for n in stock_detail["Pos_Nieuws"]] + [("🔴 Negatief", n) for n in stock_detail["Neg_Nieuws"]] + [("⚪ Onduidelijk", n) for n in stock_detail["Unc_Nieuws"]]
        if all_stock_news:
            for label, item in all_stock_news:
                st.markdown(f"- **{label}** ({item['datum']}): [{item['titel']}]({item['link']})")
        else:
            st.write("Geen recente nieuwsberichten gevonden.")

    with tab4:
        st.subheader("Algemene BIST, SPK & Macro Nieuwsfeed")
        news_df = get_news()
        if not news_df.empty:
            st.dataframe(news_df, use_container_width=True, hide_index=True)
        else:
            st.write("Kon momenteel geen RSS-nieuwsfeeds ophalen.")
