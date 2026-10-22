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
st.set_page_config(page_title="BIST Scanner 3.5 — Pro Hedgefund Edition", layout="wide")

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
                if n0 is not None: q_data["q_net_m"] = round(n0 / 1e6, 1)
                if len(cols) >= 2:
                    n1 = safe_float(q_inc.loc[net_keys[0], cols[1]])
                    if n0 is not None and n1 and abs(n1) > 0: q_data["qoq_net_growth"] = round(((n0 - n1) / abs(n1)) * 100, 1)
    except: pass
    return q_data

def calculate_rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100 - (100 / (1 + rs))).fillna(50)

def calculate_sr_levels(hist):
    if hist is None or hist.empty or len(hist) < 5: return None
    close, high, low = hist["Close"].astype(float), hist["High"].astype(float), hist["Low"].astype(float)
    price = safe_float(close.iloc[-1])
    if price is None: return None
    window = hist.tail(min(20, len(hist) - 1))
    h, l, c = safe_float(window["High"].max()) or price, safe_float(window["Low"].min()) or price, safe_float(close.iloc[-2]) if len(close) >= 2 else price
    pivot = (h + l + c) / 3.0
    rng = max(h - l, price * 0.02)
    return {
        "Pivot": round(pivot, 2), "R1": round(pivot + (0.382 * rng), 2),
        "S1": round(pivot - (0.382 * rng), 2), "ATR": round(float((high - low).rolling(14).mean().iloc[-1]) or (price * 0.03), 2)
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
    except: pass
    try:
        market = get_history("XU100.IS", "6mo")
        if len(market) >= 2:
            output["xu100_return"] = float((market["Close"].iloc[-1] / market["Close"].iloc[max(0, len(market)-64)] - 1) * 100)
            output["xu100_price"] = float(market["Close"].iloc[-1])
            output["xu100_sr"] = calculate_sr_levels(market)
    except: pass
    return output

def classify_headline(title):
    t_low = title.lower()
    pos = sum(1 for w in POSITIVE_KEYWORDS if w in t_low)
    neg = sum(1 for w in NEGATIVE_KEYWORDS if w in t_low)
    if pos > 0 and neg == 0: return "Positief"
    if neg > 0 and pos == 0: return "Negatief"
    return "Neutraal"

@st.cache_data(ttl=900, show_spinner=False)
def get_news():
    items = []
    for source, url in NEWS_URLS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=7) as resp:
                root = ET.fromstring(resp.read())
            for item in root.findall(".//item")[:8]:
                title, link, date = item.findtext("title"), item.findtext("link"), item.findtext("pubDate")
                if title: items.append({"Bron": source, "Signaal": classify_headline(title), "Titel": title, "Datum": date or "", "Link": link or ""})
        except: continue
    return pd.DataFrame(items).drop_duplicates(subset=["Titel"]).head(24) if items else pd.DataFrame(columns=["Bron", "Signaal", "Titel", "Datum", "Link"])

@st.cache_data(ttl=900, show_spinner=False)
def get_stock_news(ticker, company):
    url = f"https://news.google.com/rss/search?q={urllib.parse.quote(ticker.replace('.IS','') + ' ' + company[:15])}&hl=tr&gl=TR&ceid=TR:tr"
    pos, neg, unc = [], [], []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            root = ET.fromstring(resp.read())
        for item in root.findall(".//item")[:6]:
            t, d, l = item.findtext("title"), item.findtext("pubDate") or "", item.findtext("link") or ""
            if t:
                cat = classify_headline(t)
                if cat == "Positief": pos.append({"titel": t, "datum": d[:16], "link": l})
                elif cat == "Negatief": neg.append({"titel": t, "datum": d[:16], "link": l})
                else: unc.append({"titel": t, "datum": d[:16], "link": l})
    except: pass
    return pos, neg, unc

def send_telegram(token, chat_id, msg):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = json.dumps({"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=10)
        return True
    except: return False

@st.cache_data(ttl=900, show_spinner=False)
def run_ai_agent(ticker, company, fund, q_m, headlines, usd, key):
    if not key: return None
    try:
        prompt = f"Analyseer {company} ({ticker}). USD/TRY: {usd}, PE: {fund.get('pe')}, Winstmarge: {fund.get('margin_pct')}%. Q-Omzet: ₺{q_m.get('q_rev_m')}M. Nieuws:\n" + "\n".join(headlines[:5]) + "\nGeef JSON terug met: sentiment_label, score_adjustment (-2.0 tot 2.0), kwartaal_analyse, kap_en_nieuws_duiding, belangrijkste_katalysator, grootste_risico."
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={urllib.parse.quote(key.strip())}"
        payload = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json", "responseSchema": {
                "type": "OBJECT", "properties": {
                    "sentiment_label": {"type": "STRING"}, "score_adjustment": {"type": "NUMBER"},
                    "kwartaal_analyse": {"type": "STRING"}, "kap_en_nieuws_duiding": {"type": "STRING"},
                    "belangrijkste_katalysator": {"type": "STRING"}, "grootste_risico": {"type": "STRING"}
                }, "required": ["sentiment_label", "score_adjustment", "kwartaal_analyse", "kap_en_nieuws_duiding", "belangrijkste_katalysator", "grootste_risico"]
            }}
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(json.loads(resp.read().decode("utf-8"))["candidates"][0]["content"]["parts"][0]["text"])
    except: return None

def analyze_stock(ticker, macro, key, use_ai, p_short, p_long, p_rsi):
    hist = get_history(ticker, "1y", "1d")
    if hist.empty or len(hist) < max(p_long, 30): return None
    
    hist_w = get_history(ticker, period="1y", interval="1wk")
    w_trend = "Bullish 🟢" if not hist_w.empty and hist_w["Close"].iloc[-1] > hist_w["Close"].rolling(10).mean().iloc[-1] else "Bearish 🔴"
    
    close = hist["Close"].astype(float)
    price = safe_float(close.iloc[-1])
    if not price: return None

    sma_s = safe_float(close.rolling(p_short).mean().iloc[-1])
    sma_l = safe_float(close.rolling(p_long).mean().iloc[-1])
    rsi = safe_float(calculate_rsi(close, p_rsi).iloc[-1])
    sr = calculate_sr_levels(hist)
    
    info = {}
    try: info = yf.Ticker(ticker).info or {}
    except: pass
    company = str(info.get("longName") or info.get("shortName") or ticker)
    pe, pb, margin, rev_g = safe_float(info.get("trailingPE")), safe_float(info.get("priceToBook")), safe_float(info.get("profitMargins")), safe_float(info.get("revenueGrowth"))
    q_m = get_quarterly_metrics(ticker)

    tech_p = 0.0
    if sma_s and price > sma_s: tech_p += 2.0
    if sma_l and price > sma_l: tech_p += 2.0
    if rsi and 40 <= rsi <= 70: tech_p += 2.0
    if w_trend == "Bullish 🟢": tech_p += 1.0
    tech_score = round(min(10.0, tech_p + 1.5), 1)

    fund_p, fund_m = 0.0, 0.0
    if margin is not None:
        fund_m += 5.0
        fund_p += 5.0 if margin > 0.05 else 2.5
    if pe and pe > 0:
        fund_m += 5.0
        fund_p += 5.0 if pe < 15 else 2.5
    fund_score = round((fund_p / fund_m) * 10.0, 1) if fund_m > 0 else 5.0

    pos, neg, unc = get_stock_news(ticker, company)
    ai_rep = run_ai_agent(ticker, company, {"pe": pe, "margin_pct": margin*100 if margin else None}, q_m, [n["titel"] for n in pos+neg+unc], macro.get("usd_try"), key) if use_ai and key else None
    
    adj = float(np.clip(safe_float(ai_rep.get("score_adjustment")) if ai_rep else (0.5 if len(pos)>len(neg) else 0.0), -2.0, 2.0))
    total_score = round(min(10.0, max(1.0, (0.6 * tech_score) + (0.4 * fund_score) + adj)), 1)
    
    bh_ret = float((close.iloc[-1] / close.iloc[0] - 1) * 100)
    strat_ret = float((np.prod(1 + (np.where(close > close.rolling(p_short).mean(), 1, 0) * close.pct_change()).dropna()) - 1) * 100)

    stop_loss = round(max(0.01, price - (1.5 * sr["ATR"])), 2) if sr else round(price*0.97, 2)
    sector = SECTOR_MAP.get(ticker, "Overig")

    return {
        "Ticker": ticker, "Bedrijf": company, "Sector": sector, "Koers": round(price, 2), "Totaal_Cijfer": total_score,
        "AI_Sentiment": ai_rep.get("sentiment_label", "Neutraal") if ai_rep else "Neutraal", "AI_Rapport": ai_rep,
        "Kwartaal_Data": q_m, "RSI": round(rsi, 1) if rsi else None, "Wekelijkse_Trend": w_trend,
        "Pivot": sr["Pivot"] if sr else None, "R1": sr["R1"] if sr else None, "S1": sr["S1"] if sr else None,
        "Stop_Loss": stop_loss, "Doel_ATR": round(price + (2.5 * sr["ATR"]), 2) if sr else round(price*1.05, 2),
        "K/W (PE)": round(pe, 1) if pe else None, "BH_Return (%)": round(bh_ret, 1), "Strategy_Return (%)": round(strat_ret, 1),
        "Hist_Data": hist
    }

# ==============================================================================
# DASHBOARD UI
# ==============================================================================
st.title("📊 BIST Scanner 3.5 — Pro Hedgefund Edition")
st.markdown("Alles-in-één scanner met dynamische parameters, positiegrootte calculator, sector-indeling en correlatie matrix.")

with st.sidebar:
    st.header("⚙️ Instellingen & Parameters")
    key = st.text_input("Gemini API Key:", value=os.environ.get("GEMINI_API_KEY", ""), type="password")
    use_ai = st.toggle("Activeer AI", value=True)
    t_token = st.text_input("Telegram Token:", type="password")
    t_chat = st.text_input("Telegram Chat ID:")
    
    st.markdown("---")
    st.subheader("💰 Positiegrootte Calculator")
    tot_capital = st.number_input("Totaal Kapitaal (TRY/EUR):", value=100000.0, step=10000.0)
    risk_pct = st.slider("Max Risico per Trade (%):", 0.5, 3.0, 1.0, 0.5)

    st.markdown("---")
    st.subheader("🎛️ Dynamische Indicatoren")
    p_short = st.slider("SMA Korte Periode:", 5, 30, 20)
    p_long = st.slider("SMA Lange Periode:", 30, 100, 50)
    p_rsi = st.slider("RSI Periode:", 7, 21, 14)

    tickers = st.multiselect("Watchlist:", options=WATCHLIST, default=WATCHLIST[:12])
    min_sc = st.slider("Minimale Cijfer:", 1.0, 10.0, 5.0, 0.5)

macro = get_macro_data()
col1, col2, col3 = st.columns(3)
col1.metric("USD/TRY", f"₺{macro['usd_try']:.2f}" if macro['usd_try'] else "N/B")
col2.metric("BIST 100", f"{macro['xu100_price']:,.0f}" if macro['xu100_price'] else "N/B")
col3.metric("BIST 100 Trend", macro['xu100_sr']['Trend'] if macro['xu100_sr'] else "N/B")

results = [res for t in tickers if (res := analyze_stock(t, macro, key, use_ai, p_short, p_long, p_rsi)) and res["Totaal_Cijfer"] >= min_sc]

if results:
    results = sorted(results, key=lambda x: x["Totaal_Cijfer"], reverse=True)
    
    # Sharpe optimalisatie
    sharpes = [max(0.01, (hist:=r["Hist_Data"])["Close"].pct_change().std() and (hist["Close"].pct_change().mean() / hist["Close"].pct_change().std())) for r in results]
    tot_s = sum(sharpes)
    for r, s in zip(results, sharpes):
        r["Optimale Weging (%)"] = round((s / tot_s) * 100, 1)
        # Positiegrootte berekening
        risk_money = tot_capital * (risk_pct / 100)
        risk_per_share = max(0.01, r["Koers"] - r["Stop_Loss"])
        r["Aanbevolen Stuks"] = int(risk_money / risk_per_share)

    df = pd.DataFrame(results)

    st.subheader("📥 Exporteer Gegevens")
    st.download_button("📥 Download volledige ranglijst als CSV/Excel", df.to_csv(index=False).encode('utf-8'), "bist_rapport.csv", "text/csv")

    t1, t2, t3, t4, t5 = st.tabs(["🏆 Quant & Positiegrootte", "🏢 Sectoren", "🤖 AI & Grafiek", "📈 Correlatie Matrix", "📰 Nieuws & Telegram"])
    
    with t1:
        st.subheader("Portefeuille Ranglijst, Optimalisatie & Positiegrootte")
        disp_cols = ["Ticker", "Bedrijf", "Sector", "Koers", "Totaal_Cijfer", "Optimale Weging (%)", "Aanbevolen Stuks", "AI_Sentiment", "Wekelijkse_Trend"]
        st.dataframe(df[disp_cols], use_container_width=True, hide_index=True)

    with t2:
        st.subheader("🏢 Prestaties per Sector")
        sector_summary = df.groupby("Sector")["Totaal_Cijfer"].mean().reset_index().sort_values(by="Totaal_Cijfer", ascending=False)
        st.dataframe(sector_summary, use_container_width=True, hide_index=True)

    with t3:
        chosen = st.selectbox("Kies aandeel:", [r["Ticker"] for r in results])
        det = next(r for r in results if r["Ticker"] == chosen)
        c1, c2, c3 = st.columns(3)
        c1.metric(det["Bedrijf"], f"₺{det['Koers']}", f"Cijfer: {det['Totaal_Cijfer']}/10")
        c2.metric("Stop-Loss / Doel", f"₺{det['Stop_Loss']} / ₺{det['Doel_ATR']}")
        c3.metric("Aanbevolen Positie", f"{det['Aanbevolen Stuks']} stuks")
        if det.get("AI_Rapport"): st.success(f"**AI Duiding:** {det['AI_Rapport'].get('kap_en_nieuws_duiding')}")
        st.line_chart(det["Hist_Data"][["Close"]].assign(SMA_Short=det["Hist_Data"]["Close"].rolling(p_short).mean(), SMA_Long=det["Hist_Data"]["Close"].rolling(p_long).mean()))

    with t4:
        st.subheader("🔗 Correlatie Matrix van Geselecteerde Aandelen")
        close_df = pd.DataFrame({r["Ticker"]: r["Hist_Data"]["Close"] for r in results if r["Hist_Data"] is not None})
        if not close_df.empty:
            corr = close_df.corr()
            st.dataframe(corr.style.background_gradient(cmap="coolwarm"), use_container_width=True)

    with t5:
        if st.button("🚀 Stuur Top 3 naar Telegram"):
            msg = "🚨 *BIST Top Signalen* 🚨\n\n" + "".join([f"🔹 *{r['Bedrijf']}* ({r['Ticker']}) — Cijfer: {r['Totaal_Cijfer']}/10\n" for r in results[:3]])
            if send_telegram(t_token, t_chat, msg): st.success("Verzonden!")
            else: st.error("Fout bij verzenden.")
        st.dataframe(get_news(), use_container_width=True, hide_index=True)
else:
    st.warning("Geen aandelen gevonden die voldoen aan de criteria.")
