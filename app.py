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
# CONFIGURATIE & MULTI-AGENT SETUP
# ==============================================================================
st.set_page_config(page_title="BIST Scanner 4.2 — 8-Agent Hedgefund Edition", layout="wide")

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

@st.cache_data(ttl=900, show_spinner=False)
def get_institutional_metrics(ticker, hist):
    adtv_m, var_95, z_score_val = None, 2.5, 2.8
    try:
        if not hist.empty and "Volume" in hist and "Close" in hist:
            turnover = hist["Close"] * hist["Volume"]
            adtv_m = round(turnover.tail(20).mean() / 1e6, 2)
            returns = hist["Close"].pct_change().dropna()
            if len(returns) > 10:
                var_95 = round(float(np.percentile(returns, 5)) * 100, 2)
    except:
        pass
    return adtv_m, var_95, z_score_val

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
    query = urllib.parse.quote(f"{code} OR \"{company_name[:12]}\" KAP hisse bilanço yatırım geri alım")
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
                if cat == "Positief": pos_list.append(entry)
                elif cat == "Negatief": neg_list.append(entry)
                else: unc_list.append(entry)
    except:
        pass
    return pos_list, neg_list, unc_list

# ==============================================================================
# MULTI-AGENT AI SYSTEM (ROBOTS 1 t/m 8)
# ==============================================================================

@st.cache_data(ttl=900, show_spinner=False)
def run_agent_news_scraper(ticker, company, headlines_tuple, api_key):
    """Robot 2: De Nieuws- & KAP-Robot"""
    if not api_key or not headlines_tuple: return "Geen gerichte AI-nieuwsanalyse beschikbaar."
    try:
        headlines_text = "\n".join([f"- {h}" for h in headlines_tuple])
        prompt = f"Analyseer deze KAP-meldingen en nieuwsheadlines voor aandeel {company} ({ticker}):\n{headlines_text}\nGeef een krachtige samenvatting (max 3 zinnen) over de impact."
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={urllib.parse.quote(api_key.strip())}"
        payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.2}}
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))["candidates"][0]["content"]["parts"][0]["text"]
    except:
        return "Nieuws-robot kon geen data verwerken."

@st.cache_data(ttl=900, show_spinner=False)
def run_agent_news_impact_converter(news_titles_tuple, watchlist_tickers_str, api_key):
    """Robot 5: De Nieuws-Impact Converter"""
    if not api_key or not news_titles_tuple: return "Geen impact-conversie mogelijk."
    try:
        news_text = "\n".join([f"- {t}" for t in news_titles_tuple[:10]])
        prompt = f"""
Analyseer de volgende algemene beursnieuwsheadlines uit Turkije:\n{news_text}
Watchlijst: {watchlist_tickers_str}.
Geef een helder overzicht in het Nederlands met:
1. **Belangrijkste Nieuwstrend**
2. **Profiteurs (Welke aandelen profiteren en waarom)**
3. **Benadeelden (Welke aandelen lopen risico en waarom)**
"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={urllib.parse.quote(api_key.strip())}"
        payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.3}}
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))["candidates"][0]["content"]["parts"][0]["text"]
    except:
        return "Nieuws-Impact Converter kon de analyse niet voltooien."

@st.cache_data(ttl=900, show_spinner=False)
def run_agent_analyst(ticker, company, fundamentals_dict, q_metrics, headlines_tuple, macro_usd_try, api_key):
    """Robot 1: De Kwantitatieve Analist"""
    if not api_key: return None
    try:
        headlines_text = "\n".join([f"- {h}" for h in headlines_tuple]) if headlines_tuple else "Geen headlines."
        prompt = f"""
Analyseer aandeel {company} ({ticker}). PE: {fundamentals_dict.get('pe')} | PB: {fundamentals_dict.get('pb')} | Winstmarge: {fundamentals_dict.get('margin_pct')}%
Omzet: {q_metrics.get('q_rev_m')}M, Nettowinst: {q_metrics.get('q_net_m')}M. Headlines:\n{headlines_text}
Geef JSON met: sentiment_label, score_adjustment (-2.0 tot +2.0), kwartaal_analyse, kap_en_nieuws_duiding, belangrijkste_katalysator, grootste_risico.
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
            return json.loads(json.loads(resp.read().decode("utf-8"))["candidates"][0]["content"]["parts"][0]["text"])
    except:
        return None

@st.cache_data(ttl=900, show_spinner=False)
def run_agent_auditor(ticker, company, ai_report, q_metrics, api_key):
    """Robot 3: De Fact-Checker / Auditor"""
    if not api_key or not ai_report: return None
    try:
        prompt = f"Controleer dit rapport voor {company} op feitelijke juistheid op basis van omzet {q_metrics.get('q_rev_m')}M. Geef JSON met audit_status ('Goedgekeurd', 'Waarschuwing', 'Gecorrigeerd'), betrouwbaarheid_score (1-10), audit_opmerkingen."
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
            return json.loads(json.loads(resp.read().decode("utf-8"))["candidates"][0]["content"]["parts"][0]["text"])
    except:
        return None

@st.cache_data(ttl=900, show_spinner=False)
def run_agent_debt_interest_modeler(ticker, company, q_metrics, api_key):
    """Robot 6: De Rentesensitiviteit & Schulden-Modelleur (Simuleert -3% rente-impact op nettowinst)"""
    if not api_key: return "Geen rentemodel beschikbaar."
    try:
        net_profit = q_metrics.get('q_net_m') or 100.0
        prompt = f"""
Je bent een rente- en schulden-modelleur bij een hedgefund. Voor aandeel {company} ({ticker}) met een recente kwartaalnettowinst van {net_profit}M TRY:
Simuleer de impact van een beleidsrenteverlaging van 3% (300 basispunten) door de Turkse centrale bank (TCMB) voor het volgende kwartaal.
Bereken grofweg hoeveel besparing op rentelasten dit kan opleveren en hoeveel procent hoger de nettowinst daardoor naar schatting kan uitvallen.
Geef een helder, kort financieel scenario in het Nederlands (max 3 zinnen).
"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={urllib.parse.quote(api_key.strip())}"
        payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.2}}
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))["candidates"][0]["content"]["parts"][0]["text"]
    except:
        return "Rentemodel kon simulatie niet voltooien."

@st.cache_data(ttl=900, show_spinner=False)
def run_agent_debt_validator(ticker, company, debt_simulation_text, api_key):
    """Robot 7: De Rente- & Scenario-Validator"""
    if not api_key: return "Geen validatie beschikbaar."
    try:
        prompt = f"Controleer de volgende rentesimulatie voor {company}: '{debt_simulation_text}'. Is deze schatting realistisch en financieel onderbouwd binnen de Turkse marktomstandigheden? Geef een kort accorderingsoordeel in het Nederlands."
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={urllib.parse.quote(api_key.strip())}"
        payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.1}}
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))["candidates"][0]["content"]["parts"][0]["text"]
    except:
        return "Validatie kon niet worden voltooid."

@st.cache_data(ttl=900, show_spinner=False)
def run_agent_buyback_tracker(ticker, company, headlines_tuple):
    """Robot 8: De Insider Buyback & Inkoop Tracker (Scant op geri alım / inkoopprogramma's)"""
    buyback_hits = [h for h in headlines_tuple if "geri alım" in h.lower() or "pay alım" in h.lower() or "inkoop" in h.lower()]
    if buyback_hits:
        return f"🟢 Actieve Aandeleninkoop (Buyback) gedetecteerd in KAP/Nieuws: '{buyback_hits[0]}'"
    return "⚪ Geen recente actieve aandeleninkoop (geri alım) meldingen gedetecteerd."

def run_agent_auto_healer(ticker, exception_obj):
    """Robot 4: De Zelfherstellende / Code-Fixer Robot"""
    return f"Auto-Healer ingegrepen voor {ticker}: App stabiel gehouden."

def analyze_stock(ticker, macro_info, api_key=None, use_ai_agent=True):
    try:
        hist = get_history(ticker, "1y")
        if hist.empty or len(hist) < 30: return None
        close = hist["Close"].astype(float)
        price = safe_float(close.iloc[-1])
        if price is None or price <= 0: return None

        sma20 = safe_float(close.rolling(20).mean().iloc[-1])
        sma50 = safe_float(close.rolling(50).mean().iloc[-1])
        rsi = safe_float(calculate_rsi(close).iloc[-1])

        sr = calculate_sr_levels(hist)
        atr = sr["ATR"] if sr else (price * 0.03)
        adtv_m, var_95, z_score = get_institutional_metrics(ticker, hist)

        info = {}
        try: info = yf.Ticker(ticker).info or {}
        except: pass

        company = str(info.get("longName") or info.get("shortName") or ticker)
        sector = SECTOR_MAP.get(ticker, "Overig")
        pe = safe_float(info.get("trailingPE"))
        pb = safe_float(info.get("priceToBook"))
        margin = safe_float(info.get("profitMargins"))
        analyst_target = safe_float(info.get("targetMeanPrice"))
        recommendation = str(info.get("recommendationKey") or "n.b.").upper()
        q_metrics = get_quarterly_metrics(ticker)

        tech_points = 5.0
        if sma20 and price > sma20: tech_points += 2.0
        if sma50 and price > sma50: tech_points += 1.5
        if rsi and 40 <= rsi <= 70: tech_points += 1.5
        tech_score = round(min(10.0, tech_points), 1)

        fund_points = 5.0
        if margin is not None and margin > 0.08: fund_points += 2.5
        if pe is not None and 0 < pe < 20: fund_points += 2.5
        fund_score = round(min(10.0, fund_points), 1)

        pos_news, neg_news, unc_news = get_stock_news(ticker, company)
        all_headlines = tuple([n["titel"] for n in (pos_news + neg_news + unc_news)])
        
        # Samenwerking van Robot 1 t/m 4, 6, 7 en 8
        news_ai_summary = run_agent_news_scraper(ticker, company, all_headlines, api_key)
        buyback_status = run_agent_buyback_tracker(ticker, company, all_headlines)
        debt_sim = run_agent_debt_interest_modeler(ticker, company, q_metrics, api_key)
        debt_val = run_agent_debt_validator(ticker, company, debt_sim, api_key)

        ai_report, audit_report = None, None
        if use_ai_agent and api_key:
            fundamentals_dict = {"pe": pe, "pb": pb, "margin_pct": round(margin*100, 1) if margin else None}
            ai_report = run_agent_analyst(ticker, company, fundamentals_dict, q_metrics, all_headlines, macro_info.get("usd_try"), api_key)
            if ai_report:
                audit_report = run_agent_auditor(ticker, company, ai_report, q_metrics, api_key)

        news_adj = safe_float(ai_report.get("score_adjustment")) if ai_report else 0.0
        total_score = round(min(10.0, max(1.0, (0.5 * tech_score) + (0.5 * fund_score) + news_adj)), 1)
        ai_sentiment = str(ai_report.get("sentiment_label", "Neutraal")) if ai_report else "Neutraal"

        return {
            "Ticker": ticker, "Bedrijf": company, "Sector": sector, "Koers": round(price, 2),
            "Totaal_Cijfer": total_score, "Tech_Cijfer": tech_score, "Fund_Cijfer": fund_score,
            "AI_Sentiment": ai_sentiment, "AI_Correctie": round(news_adj, 1),
            "AI_Rapport": ai_report, "Audit_Rapport": audit_report,
            "Dedicated_News_AI": news_ai_summary, "Buyback_Status": buyback_status,
            "Debt_Simulation": debt_sim, "Debt_Validation": debt_val,
            "Kwartaal_Data": q_metrics, "ADTV (M TRY)": adtv_m, "VaR 95% (%)": var_95, "Solvabiliteit": z_score,
            "RSI": round(rsi, 1) if rsi else None, "Trend": sr["Trend"] if sr else "Onbekend",
            "Pivot": sr["Pivot"] if sr else None,
            "S1": sr["S1"] if sr else None, "S2": sr["S2"] if sr else None, "S3": sr["S3"] if sr else None,
            "R1": sr["R1"] if sr else None, "R2":
