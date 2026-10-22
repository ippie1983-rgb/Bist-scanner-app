import os
import json
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

# BIST Scanner 3.3.1 — Quant, Portfolio Optimalisatie, Backtest, Telegram & AI Agent
st.set_page_config(page_title="BIST Scanner 3.3.1 + AI Agent & Backtest", layout="wide")

WATCHLIST = [
    "GARAN.IS", "AKBNK.IS", "YKBNK.IS", "ISCTR.IS", "HALKB.IS", "VAKBN.IS",
    "EREGL.IS", "KRDMD.IS", "THYAO.IS", "PGSUS.IS", "TAVHL.IS",
    "TUPRS.IS", "PETKM.IS", "SISE.IS", "KCHOL.IS", "SAHOL.IS", "BIMAS.IS",
    "MGROS.IS", "TCELL.IS", "TTKOM.IS", "ASELS.IS", "FROTO.IS", "TOASO.IS",
    "ENKAI.IS", "ARCLK.IS", "TTRAK.IS", "AEFES.IS", "ULKER.IS", "DOAS.IS",
    "EKGYO.IS"
]

NEWS_URLS = [
    ("Google Nieuws — Turkije economie", "https://news.google.com/rss/search?q=Turkiye+ekonomi+Borsa+Istanbul&hl=tr&gl=TR&ceid=TR:tr"),
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

def safe_float(value):
    try:
        value = float(value)
        return value if np.isfinite(value) else None
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

@st.cache_data(ttl=900, show_spinner=False)
def get_quarterly_metrics(ticker):
    q_data = {
        "last_quarter_date": None, "q_rev_m": None, "q_net_m": None,
        "qoq_rev_growth": None, "qoq_net_growth": None
    }
    try:
        t_obj = yf.Ticker(ticker)
        q_inc = t_obj.quarterly_income_stmt
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
                    if r0 is not None and r1 and r1 > 0:
                        q_data["qoq_rev_growth"] = round(((r0 / r1) - 1) * 100, 1)

            if net_keys:
                n0 = safe_float(q_inc.loc[net_keys[0], cols[0]])
                if n0 is not None: q_data["q_net_m"] = round(n0 / 1e6, 1)
                if len(cols) >= 2:
                    n1 = safe_float(q_inc.loc[net_keys[0], cols[1]])
                    if n0 is not None and n1 and abs(n1) > 0:
                        q_data["qoq_net_growth"] = round(((n0 - n1) / abs(n1)) * 100, 1)
    except Exception:
        pass
    return q_data

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

def calculate_stochastic_rsi(close, period=14):
    rsi = calculate_rsi(close, period)
    lowest_rsi = rsi.rolling(period).min()
    highest_rsi = rsi.rolling(period).max()
    stoch_rsi = (rsi - lowest_rsi) / (highest_rsi - lowest_rsi).replace(0, np.nan)
    return (stoch_rsi * 100).fillna(50)

def calculate_bollinger_bands(close, period=20, num_std=2):
    sma = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = sma + (std * num_std)
    lower = sma - (std * num_std)
    return sma, upper, lower

def calculate_sr_levels(hist):
    if hist is None or hist.empty or len(hist) < 5:
        return None
    close = hist["Close"].astype(float)
    high = hist["High"].astype(float)
    low = hist["Low"].astype(float)
    volume = hist["Volume"].astype(float) if "Volume" in hist else pd.Series(dtype=float)
    price = safe_float(close.iloc[-1])
    if price is None: return None

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

    return {
        "Pivot": round(pivot, 2), "R1": round(r1, 2), "R2": round(r2, 2), "R3": round(r3, 2),
        "S1": round(s1, 2), "S2": round(s2, 2), "S3": round(s3, 2), "Trend": trend,
        "Vol_Ratio": round(vol_ratio, 2) if vol_ratio is not None else None,
        "ATR": round(atr, 2), "ATR_Pct": round(atr_pct, 2)
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
    except Exception: pass
    try:
        market = get_history("XU100.IS", "6mo")
        if len(market) >= 2:
            close_m = market["Close"]
            lookback_idx = max(0, len(close_m) - 64)
            output["xu100_return"] = float((close_m.iloc[-1] / close_m.iloc[lookback_idx] - 1) * 100)
            output["xu100_price"] = float(close_m.iloc[-1])
            output["xu100_sr"] = calculate_sr_levels(market)
    except Exception: pass
    return output

def classify_headline(title):
    t_low = title.lower()
    pos_hits = sum(1 for w in POSITIVE_KEYWORDS if w in t_low)
    neg_hits = sum(1 for w in NEGATIVE_KEYWORDS if w in t_low)
    if pos_hits > 0 and neg_hits == 0: return "Positief"
    if neg_hits > 0 and pos_hits == 0: return "Negatief"
    return "Onduidelijk / Te controleren"

@st.cache_data(ttl=900, show_spinner=False)
def get_news():
    items = []
    for source, url in NEWS_URLS:
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=7) as response:
                root = ET.fromstring(response.read())
            for item in root.findall(".//item")[:8]:
                title = item.findtext("title")
                link = item.findtext("link")
                pub_date = item.findtext("pubDate")
                if title:
                    items.append({"Bron": source, "Signaal": classify_headline(title), "Titel": title, "Datum": pub_date or "", "Link": link or ""})
        except Exception: continue
    if not items: return pd.DataFrame(columns=["Bron", "Signaal", "Titel", "Datum", "Link"])
    return pd.DataFrame(items).drop_duplicates(subset=["Titel"]).head(24)

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
    except Exception: pass
    return pos_list, neg_list, unc_list

def send_telegram_alert(token, chat_id, message):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return True
    except Exception:
        return False

@st.cache_data(ttl=900, show_spinner=False)
def run_financial_news_agent(ticker, company, fundamentals_dict, q_metrics, headlines_tuple, macro_usd_try, api_key):
    if not api_key: return None
    try:
        headlines_text = "\n".join([f"- {h}" for h in headlines_tuple]) if headlines_tuple else "Geen."
        prompt = f"""
Analyseer aandeel {company} ({ticker}) op basis van kwartaalcijfers en KAP-nieuws.
USD/TRY: {macro_usd_try} | PE: {fundamentals_dict.get('pe')} | PB: {fundamentals_dict.get('pb')} | Winstmarge: {fundamentals_dict.get('margin_pct')}%
Laatste kwartaal Omzet: ₺{q_metrics.get('q_rev_m')}M | Nettowinst: ₺{q_metrics.get('q_net_m')}M
Headlines:\n{headlines_text}
Geef JSON terug met: sentiment_label, score_adjustment (-2.0 tot 2.0), kwartaal_analyse, kap_en_nieuws_duiding, belangrijkste_katalysator, grootste_risico.
"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={urllib.parse.quote(api_key.strip())}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2, "responseMimeType": "application/json",
                "responseSchema": {
                    "type": "OBJECT",
                    "properties": {
                        "sentiment_label": {"type": "STRING"}, "score_adjustment": {"type": "NUMBER"},
                        "kwartaal_analyse": {"type": "STRING"}, "kap_en_nieuws_duiding": {"type": "STRING"},
                        "belangrijkste_katalysator": {"type": "STRING"}, "grootste_risico": {"type": "STRING"}
                    },
                    "required": ["sentiment_label", "score_adjustment", "kwartaal_analyse", "kap_en_nieuws_duiding", "belangrijkste_katalysator", "grootste_risico"]
                }
            }
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(json.loads(resp.read().decode("utf-8"))["candidates"][0]["content"]["parts"][0]["text"])
    except Exception: return None

@st.cache_data(ttl=900, show_spinner=False)
def run_macro_summary_agent(news_df, api_key):
    if not api_key or news_df.empty: return None
    try:
        headlines = "\n".join([f"- [{row['Signaal']}] {row['Titel']}" for _, row in news_df.head(15).iterrows()])
        prompt = f"Analyseer het Turkse macro- en SPK-nieuws:\n{headlines}\nGeef een krachtig marktoordeel in het Nederlands (max 3 alinea's)."
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={urllib.parse.quote(api_key.strip())}"
        payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.3}}
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))["candidates"][0]["content"]["parts"][0]["text"]
    except Exception: return None

def run_backtest(hist_df):
    if hist_df is None or len(hist_df) < 50: return 0.0, 0.0
    df = hist_df.copy()
    df["SMA20"] = df["Close"].rolling(20).mean()
    df["Signal"] = np.where(df["Close"] > df["SMA20"], 1, 0)
    df["Market_Return"] = df["Close"].pct_change()
    df["Strategy_Return"] = df["Signal"].shift(1) * df["Market_Return"]
    
    bh_ret = float((df["Close"].iloc[-1] / df["Close"].iloc[0] - 1) * 100)
    strat_ret = float((np.prod(1 + df["Strategy_Return"].dropna()) - 1) * 100)
    return round(bh_ret, 1), round(strat_ret, 1)

def analyze_stock(ticker, macro_info, api_key=None, use_ai_agent=True):
    hist = get_history(ticker, "1y")
    if hist.empty or len(hist) < 30: return None
    close = hist["Close"].astype(float)
    price = safe_float(close.iloc[-1])
    if price is None or price <= 0: return None

    sma20 = safe_float(close.rolling(20).mean().iloc[-1])
    sma50 = safe_float(close.rolling(50).mean().iloc[-1])
    rsi = safe_float(calculate_rsi(close).iloc[-1])
    stoch_rsi = safe_float(calculate_stochastic_rsi(close).iloc[-1])
    _, b_upper, b_lower = calculate_bollinger_bands(close)
    b_up_val, b_low_val = safe_float(b_upper.iloc[-1]), safe_float(b_lower.iloc[-1])

    ema12, ema26 = close.ewm(span=12, adjust=False).mean(), close.ewm(span=26, adjust=False).mean()
    macd_val, macd_sig = safe_float((ema12 - ema26).iloc[-1]), safe_float(((ema12 - ema26).ewm(span=9).mean()).iloc[-1])

    sr = calculate_sr_levels(hist)
    atr = sr["ATR"] if sr else (price * 0.03)
    vol_ratio = sr["Vol_Ratio"] if sr else None
    ret_1m = safe_float((price / close.iloc[-22] - 1) * 100) if len(close) >= 22 else None

    info = {}
    try: info = yf.Ticker(ticker).info or {}
    except Exception: pass

    company = str(info.get("longName") or info.get("shortName") or ticker)
    pe, pb = safe_float(info.get("trailingPE")), safe_float(info.get("priceToBook"))
    margin, rev_growth = safe_float(info.get("profitMargins")), safe_float(info.get("revenueGrowth"))
    recommendation = {"STRONG_BUY": "Sterk kopen", "BUY": "Kopen", "HOLD": "Houden", "UNDERPERFORM": "Onderpresteren", "SELL": "Verkopen"}.get(str(info.get("recommendationKey") or "").upper(), "Niet beschikbaar")
    q_metrics = get_quarterly_metrics(ticker)

    tech_points, tech_reasons = 0.0, []
    if sma20 and price > sma20: tech_points += 1.5; tech_reasons.append("Koers boven SMA20")
    if sma50 and price > sma50: tech_points += 1.5; tech_reasons.append("Koers boven SMA50")
    if rsi and 45 <= rsi <= 65: tech_points += 2.0; tech_reasons.append("RSI in gezonde zone")
    if stoch_rsi and stoch_rsi < 20: tech_points += 1.0; tech_reasons.append(f"Stoch RSI oversold ({stoch_rsi:.1f})")
    if b_low_val and price <= b_low_val * 1.01: tech_points += 1.0; tech_reasons.append("Nabij onderste Bollinger Band")
    if macd_val and macd_sig and macd_val > macd_sig: tech_points += 2.0; tech_reasons.append("MACD boven signaallijn")
    if vol_ratio and vol_ratio >= 1.3: tech_points += 1.0; tech_reasons.append("Hoog volume")
    tech_score = round(min(10.0, tech_points), 1)

    fund_points, fund_max = 0.0, 0.0
    fund_reasons = []
    if margin is not None:
        fund_max += 2.5
        if margin > 0.10: fund_points += 2.5; fund_reasons.append(f"Sterke winstmarge ({margin*100:.1f}%)")
        elif margin > 0: fund_points += 1.2
    if rev_growth is not None:
        fund_max += 2.5
        if rev_growth > 0.10: fund_points += 2.5; fund_reasons.append(f"Sterke omzetgroei ({rev_growth*100:.1f}%)")
        elif rev_growth > 0: fund_points += 1.2
    if pe and pe > 0:
        fund_max += 2.5
        if pe < 10: fund_points += 2.5; fund_reasons.append(f"Lage K/W ({pe:.1f}x)")
        elif pe <= 18: fund_points += 1.5
        else: fund_points += 0.5
    if pb and pb > 0:
        fund_max += 2.5
        if pb < 1.5: fund_points += 2.5; fund_reasons.append(f"Aantrekkelijke K/B ({pb:.2f}x)")
        elif pb <= 3.0: fund_points += 1.5
        else: fund_points += 0.5
    fund_score = round((fund_points / fund_max) * 10.0, 1) if fund_max > 0 else 5.0

    pos_news, neg_news, unc_news = get_stock_news(ticker, company)
    all_headlines = tuple([n["titel"] for n in (pos_news + neg_news + unc_news)])
    ai_report = None
    if use_ai_agent and api_key:
        ai_report = run_financial_news_agent(ticker, company, {"pe": pe, "pb": pb, "margin_pct": margin*100 if margin else None, "rev_growth_pct": rev_growth*100 if rev_growth else None}, q_metrics, all_headlines, macro_info.get("usd_try"), api_key)

    news_adj = float(np.clip(safe_float(ai_report.get("score_adjustment")) if ai_report else (0.5 if len(pos_news) > len(neg_news) else (-1.0 if len(neg_news) > len(pos_news) else 0.0)), -2.0, 2.0))
    ai_sentiment = str(ai_report.get("sentiment_label", "Neutraal")) if ai_report else ("Positief" if news_adj > 0 else "Neutraal")

    total_score = round(min(10.0, max(1.0, (0.6 * tech_score) + (0.4 * fund_score) + news_adj)), 1)
    bh_ret, strat_ret = run_backtest(hist)

    return {
        "Ticker": ticker, "Bedrijf": company, "Koers": round(price, 2),
        "Totaal_Cijfer": total_score, "Tech_Cijfer": tech_score, "Fund_Cijfer": fund_score,
        "AI_Sentiment": ai_sentiment, "AI_Correctie": round(news_adj, 1), "AI_Rapport": ai_report,
        "Kwartaal_Data": q_metrics, "RSI": round(rsi, 1) if rsi else None,
        "Trend": sr["Trend"] if sr else "Onbekend", "ATR": round(atr, 2),
        "Pivot": sr["Pivot"] if sr else None, "R1": sr["R1"] if sr else None, "S1": sr["S1"] if sr else None,
        "Stop_Loss": round(max(0.01, price - (1.5 * atr)), 2), "Doel_ATR": round(price + (2.5 * atr), 2),
        "Ret_1M (%)": round(ret_1m, 1) if ret_1m is not None else None, "K/W (PE)": round(pe, 1) if pe else None,
        "Analist_Advies": recommendation, "Tech_Redenen": tech_reasons, "Fund_Redenen": fund_reasons,
        "BH_Return (%)": bh_ret, "Strategy_Return (%)": strat_ret, "Hist_Data": hist,
        "Pos_Nieuws": pos_news, "Neg_Nieuws": neg_news, "Unc_Nieuws": unc_news
    }

# ==============================================================================
# STREAMLIT DASHBOARD UI
# ==============================================================================
st.title("📊 BIST Scanner 3.3.1 — Quant, Portfolio Optimalisatie & Telegram Alerts")
st.markdown("Geavanceerde BIST 100 scanner met AI-agents, portefeuille-optimalisatie op basis van Sharpe ratio, backtesting en Telegram meldingen.")

with st.sidebar:
    st.header("🤖 AI & Telegram Instellingen")
    default_key = os.environ.get("GEMINI_API_KEY", "")
    if not default_key:
        try: default_key = st.secrets.get("GEMINI_API_KEY", "")
        except Exception: default_key = ""

    gemini_api_key = st.text_input("Gemini API Key:", value=default_key, type="password")
    use_ai_agent = st.toggle("Activeer AI-Agents", value=True)

    st.markdown("---")
    telegram_token = st.text_input("Telegram Bot Token:", type="password")
    telegram_chat_id = st.text_input("Telegram Chat ID:")

    st.divider()
    st.header("⚙️ Scanner Instellingen")
    selected_tickers = st.multiselect("Selecteer BIST-aandelen:", options=WATCHLIST, default=WATCHLIST[:10])
    min_score = st.slider("Minimale Totaalscore filter:", 1.0, 10.0, 5.0, 0.5)
    if st.button("🔄 Cache wissen & Verversen"):
        st.cache_data.clear()
        st.rerun()

with st.spinner("Macro-indicatoren laden..."):
    macro = get_macro_data()

col1, col2, col3, col4 = st.columns(4)
col1.metric("💱 USD/TRY", f"₺{macro['usd_try']:.2f}" if macro["usd_try"] else "N/B", "Devaluatie-buffer" if macro["dev_risk"] else "Stabiel")
col2.metric("📈 BIST 100", f"{macro['xu100_price']:,.0f}" if macro["xu100_price"] else "N/B", f"{macro['xu100_return']:.1f}% (3m)" if macro["xu100_return"] is not None else None)
col3.metric("🧭 XU100 Trend", macro["xu100_sr"]["Trend"] if macro["xu100_sr"] else "N/B")
col4.metric("🛡️ XU100 S1 / R1", f"{macro['xu100_sr']['S1']:,.0f} / {macro['xu100_sr']['R1']:,.0f}" if macro["xu100_sr"] else "N/B")

st.divider()

results = []
if selected_tickers:
    progress_bar = st.progress(0, text="Aandelen analyseren...")
    for idx, t in enumerate(selected_tickers):
        res = analyze_stock(t, macro, api_key=gemini_api_key, use_ai_agent=use_ai_agent)
        if res and res["Totaal_Cijfer"] >= min_score:
            results.append(res)
        progress_bar.progress((idx + 1) / len(selected_tickers), text=f"Geanalyseerd: {t} ({idx+1}/{len(selected_tickers)})")
    progress_bar.empty()

if not results:
    st.warning("Geen aandelen gevonden die voldoen aan de criteria.")
else:
    results = sorted(results, key=lambda x: x["Totaal_Cijfer"], reverse=True)
    
    for r in results:
        hist = r["Hist_Data"]
        if hist is not None and len(hist) > 20:
            daily_ret = hist["Close"].pct_change().dropna()
            ann_ret = (1 + daily_ret.mean()) ** 252 - 1
            ann_vol = daily_ret.std() * np.sqrt(252)
            r["Sharpe"] = (ann_ret / ann_vol) if ann_vol > 0 else 0.0
        else:
            r["Sharpe"] = 0.0

    pos_sharpes = [max(0.01, r["Sharpe"]) for r in results]
    tot_sharpe = sum(pos_sharpes)
    for r, s in zip(results, pos_sharpes):
        r["Optimale Weging (%)"] = round((s / tot_sharpe) * 100, 1) if tot_sharpe > 0 else round(100 / len(results), 1)

    df_overview = pd.DataFrame(results)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏆 Quant & Optimalisatie", "📐 Steun & Weerstand",
        "🤖 AI & Grafiek", "📈 Strategie Backtest", "📰 Nieuws & Telegram"
    ])

    with tab1:
        st.subheader("Portefeuille Ranglijst & Sharpe-Optimalisatie")
        display_cols = ["Ticker", "Bedrijf", "Koers", "Totaal_Cijfer", "Optimale Weging (%)", "AI_Sentiment", "RSI", "Trend", "K/W (PE)"]
        st.dataframe(df_overview[display_cols], use_container_width=True, hide_index=True)

    with tab2:
        st.subheader("Pivot Points & Daytrading Niveaus")
        sr_cols = ["Ticker", "Koers", "Trend", "S1", "Pivot", "R1", "Stop_Loss", "Doel_ATR"]
        st.dataframe(df_overview[sr_cols], use_container_width=True, hide_index=True)

    with tab3:
        st.subheader("Gedetailleerde Inspectie & Koersgrafiek")
        chosen = st.selectbox("Kies aandeel:", [r["Ticker"] for r in results])
        stock_detail = next(r for r in results if r["Ticker"] == chosen)

        c1, c2, c3 = st.columns(3)
        c1.metric(f"{stock_detail['Bedrijf']} ({stock_detail['Ticker']})", f"₺{stock_detail['Koers']}", f"Cijfer: {stock_detail['Totaal_Cijfer']}/10")
        c2.metric("Steun S1 / Weerstand R1", f"₺{stock_detail['S1']} / ₺{stock_detail['R1']}", f"Pivot: ₺{stock_detail['Pivot']}")
        c3.metric("Stop-Loss / Doel", f"₺{stock_detail['Stop_Loss']} / ₺{stock_detail['Doel_ATR']}", f"Optimale weging: {stock_detail['Optimale Weging (%)']}%")

        hist_df = stock_detail.get("Hist_Data")
        if hist_df is not None and not hist_df.empty:
            chart_data = hist_df[["Close"]].copy()
            chart_data["SMA20"] = hist_df["Close"].rolling(20).mean()
            chart_data["SMA50"] = hist_df["Close"].rolling(50).mean()
            chart_data["S1"] = stock_detail["S1"]
            chart_data["R1"] = stock_detail["R1"]
            st.line_chart(chart_data[["Close", "SMA20", "SMA50", "S1", "R1"]])

        ai_rep = stock_detail.get("AI_Rapport")
        if ai_rep:
            st.success(f"**AI Sentiment:** {ai_rep.get('sentiment_label')} | **Kwartaal:** {ai_rep.get('kwartaal_analyse')}\n\n**KAP:** {ai_rep.get('kap_en_nieuws_duiding')}")

    with tab4:
        st.subheader("📈 Strategie Backtest (1 Jaar)")
        bt_cols = ["Ticker", "Bedrijf", "Koers", "Totaal_Cijfer", "Strategy_Return (%)", "BH_Return (%)"]
        st.dataframe(df_overview[bt_cols], use_container_width=True, hide_index=True)

    with tab5:
        st.subheader("Algemene Macro Nieuwsfeed & Telegram Meldingen")
        news_df = get_news()
        if use_ai_agent and gemini_api_key and not news_df.empty:
            with st.spinner("AI macro-samenvatting laden..."):
                macro_summary = run_macro_summary_agent(news_df, gemini_api_key)
                if macro_summary: st.info(f"### 🤖 AI Macro & SPK Marktoordeel\n\n{macro_summary}")

        st.markdown("---")
        st.subheader("📲 Stuur Top-signalen naar Telegram")
        if st.button("🚀 Verstuur Top 3 Aandelen naar Telegram"):
            if not telegram_token or not telegram_chat_id:
                st.error("Vul eerst je Telegram Bot Token en Chat ID in de zijbalk in.")
            else:
                top3 = results[:3]
                msg = "🚨 *BIST Scanner 3.3.1 — Top Signalen* 🚨\n\n"
                for r in top3:
                    msg += f"🔹 *{r['Bedrijf']}* ({r['Ticker']})\n"
                    msg += f"• Cijfer: {r['Totaal_Cijfer']}/10 | Koers: ₺{r['Koers']}\n"
                    msg += f"• Advies: {r['Analist_Advies']} | Optimale Weging: {r['Optimale Weging (%)']}%\n\n"
                success = send_telegram_alert(telegram_token, telegram_chat_id, msg)
                if success: st.success("Telegram melding succesvol verzonden!")
                else: st.error("Kon bericht niet verzenden. Controleer je Token en Chat ID.")

        if not news_df.empty:
            st.dataframe(news_df, use_container_width=True, hide_index=True)
