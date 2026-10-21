import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

# BIST Scanner 2.0 — screening tool, geen automatisch koopadvies.
st.set_page_config(page_title="BIST Scanner 2.0", layout="wide")

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
    ("Google Nieuws — bedrijven en resultaten", "https://news.google.com/rss/search?q=BIST+sirket+bilanco+kar+zarar&hl=tr&gl=TR&ceid=TR:tr"),
]

@st.cache_data(ttl=300, show_spinner=False)
def get_history(ticker, period="6mo"):
    try:
        df = yf.Ticker(ticker).history(period=period, auto_adjust=True)
        if df is None or df.empty:
            return pd.DataFrame()
        return df.dropna(subset=["Close"])
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=900, show_spinner=False)
def get_macro_data():
    output = {"usd_try": None, "xu100_return": None, "xu100_price": None}
    try:
        fx = get_history("USDTRY=X", "1mo")
        if not fx.empty:
            output["usd_try"] = float(fx["Close"].iloc[-1])
    except Exception:
        pass
    try:
        market = get_history("XU100.IS", "3mo")
        if len(market) >= 2:
            output["xu100_return"] = float((market["Close"].iloc[-1] / market["Close"].iloc[0] - 1) * 100)
            output["xu100_price"] = float(market["Close"].iloc[-1])
    except Exception:
        pass
    return output

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
                    items.append({"Bron": source, "Titel": title, "Datum": pub_date or "", "Link": link or ""})
        except Exception:
            continue
    if not items:
        return pd.DataFrame(columns=["Bron", "Titel", "Datum", "Link"])
    df = pd.DataFrame(items).drop_duplicates(subset=["Titel"]).head(20)
    return df

def safe_float(value):
    try:
        value = float(value)
        return value if np.isfinite(value) else None
    except (TypeError, ValueError):
        return None

def calculate_rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    # Geen verliezen + wel winst = 100; geen beweging in beide richtingen = 50.
    rsi = rsi.where(loss != 0, 100)
    flat = (gain == 0) & (loss == 0)
    rsi = rsi.where(~flat, 50)
    return rsi.fillna(50)

def analyze_stock(ticker):
    hist = get_history(ticker, "1y")
    if hist.empty or len(hist) < 30:
        return None

    close = hist["Close"].astype(float)
    high = hist["High"].astype(float)
    low = hist["Low"].astype(float)
    volume = hist["Volume"].astype(float) if "Volume" in hist else pd.Series(index=hist.index, dtype=float)
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

    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    atr = safe_float(tr.rolling(14).mean().iloc[-1])
    if atr is None:
        atr = price * 0.03

    ret_1m = safe_float((price / close.iloc[-22] - 1) * 100) if len(close) >= 22 else None
    ret_3m = safe_float((price / close.iloc[-64] - 1) * 100) if len(close) >= 64 else None
    vol_avg = safe_float(volume.tail(20).mean()) if not volume.empty else None
    vol_latest = safe_float(volume.iloc[-1]) if not volume.empty else None
    vol_ratio = (vol_latest / vol_avg) if vol_latest is not None and vol_avg and vol_avg > 0 else None

    # Fundamentele data via Yahoo Finance kan voor BIST onvolledig of vertraagd zijn.
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
    recommendation = str(info.get("recommendationKey") or "n.b.").upper()
    recommendation_map = {
        "STRONG_BUY": "Sterk kopen", "BUY": "Kopen", "HOLD": "Houden",
        "UNDERPERFORM": "Onderpresteren", "SELL": "Verkopen"
    }
    recommendation = recommendation_map.get(recommendation, "Niet beschikbaar")

    # Technische score: 0–10. Score is een screeningsignaal, geen voorspelling.
    tech_points = 0.0
    tech_reasons = []
    if sma20 is not None:
        if price > sma20:
            tech_points += 2
            tech_reasons.append("Koers boven SMA20")
        else:
            tech_reasons.append("Koers onder SMA20")
    if sma50 is not None:
        if price > sma50:
            tech_points += 2
            tech_reasons.append("Koers boven SMA50")
        else:
            tech_reasons.append("Koers onder SMA50")
    if rsi is not None:
        if 45 <= rsi <= 65:
            tech_points += 2
            tech_reasons.append("RSI in neutrale/positieve zone")
        elif 30 <= rsi < 45:
            tech_points += 1.5
            tech_reasons.append("RSI laag; herstel mogelijk, bevestiging nodig")
        elif rsi < 30:
            tech_points += 1
            tech_reasons.append("RSI oversold; trendrisico blijft")
        elif 65 < rsi <= 70:
            tech_points += 1
            tech_reasons.append("RSI sterk")
        else:
            tech_reasons.append("RSI hoog; oververhitting mogelijk")
    if macd_value is not None and macd_signal is not None:
        if macd_value > macd_signal:
            tech_points += 2
            tech_reasons.append("MACD boven signaallijn")
        else:
            tech_reasons.append("MACD onder signaallijn")
    if vol_ratio is not None and vol_ratio >= 1.3:
        tech_points += 1
        tech_reasons.append("Handelsvolume boven gemiddelde")
    tech_score = round(min(10, tech_points), 1)

    # Fundamentals score: alleen beschikbare indicatoren tellen mee.
    fund_points = 0.0
    fund_max = 0.0
    fund_reasons = []
    if margin is not None:
        fund_max += 2
        if margin > 0.10:
            fund_points += 2
            fund_reasons.append("Hoge winstmargin")
        elif margin > 0:
            fund_points += 1
            fund_reasons.append("Positieve winstmargin")
        else:
            fund_reasons.append("Negatieve winstmargin")
    if revenue_growth is not None:
        fund_max += 2
        if revenue_growth > 0.10:
            fund_points += 2
            fund_reasons.append("Sterke omzetgroei")
        elif revenue_growth > 0:
            fund_points += 1
            fund_reasons.append("Positieve omzetgroei")
        else:
            fund_reasons.append("Omzetgroei niet positief")
    if pe is not None and pe > 0:
        fund_max += 2
        if pe < 12:
            fund_points += 2
            fund_reasons.append("Relatief lage P/E (context nodig)")
        elif pe < 22:
            fund_points += 1
            fund_reasons.append("Gemiddelde P/E (sector vergelijken)")
        else:
            fund_reasons.append("Hoge P/E (groei moet dit rechtvaardigen)")
    if pb is not None and pb > 0:
        fund_max += 1
        if pb < 1.5:
            fund_points += 1
            fund_reasons.append("Relatief lage P/B (context nodig)")
    fundamental_score = round((fund_points / fund_max) * 10, 1) if fund_max else None

    # Overall score alleen op basis van twee expliciete onderdelen.
    if fundamental_score is not None:
        overall_score = round(0.55 * tech_score + 0.45 * fundamental_score, 1)
    else:
        overall_score = tech_score
    data_quality = "Techniek + fundamentals" if fundamental_score is not None else "Alleen techniek; fundamentals ontbreken"

    # ATR-niveaus zijn indicatieve volatiliteitsniveaus, geen gegarandeerde stop of koersdoel.
    target = price + 1.5 * atr
    stop = max(0, price - atr)
    target_upside = ((analyst_target / price) - 1) * 100 if analyst_target and analyst_target > 0 else None

    return {
        "Bedrijf": company,
        "Ticker": ticker,
        "Koers (TRY)": round(price, 2),
        "Rendement 1m %": round(ret_1m, 2) if ret_1m is not None else None,
        "Rendement 3m %": round(ret_3m, 2) if ret_3m is not None else None,
        "RSI": round(rsi, 1) if rsi is not None else None,
        "MACD": round(macd_value, 3) if macd_value is not None else None,
        "Volume/20d gem.": round(vol_ratio, 2) if vol_ratio is not None else None,
        "Technische score": tech_score,
        "Fundamentele score": fundamental_score,
        "Totaalscore": overall_score,
        "P/E": round(pe, 2) if pe is not None and pe > 0 else None,
        "P/B": round(pb, 2) if pb is not None and pb > 0 else None,
        "Winstmarge %": round(margin * 100, 2) if margin is not None else None,
        "Omzetgroei %": round(revenue_growth * 100, 2) if revenue_growth is not None else None,
        "Analistenkoersdoel": round(analyst_target, 2) if analyst_target is not None else None,
        "Koersdoelruimte %": round(target_upside, 1) if target_upside is not None else None,
        "Analistenadvies": recommendation,
        "Aantal analisten": analyst_count,
        "Indicatieve steun": round(max(0, price - atr), 2),
        "Indicatieve weerstand": round(price + atr, 2),
        "ATR-doel (indicatief)": round(target, 2),
        "ATR-stop (indicatief)": round(stop, 2),
        "Datadekking": data_quality,
        "Technische signalen": "; ".join(tech_reasons),
        "Fundamentele signalen": "; ".join(fund_reasons) if fund_reasons else "Geen bruikbare fundamentele data"
    }

st.title("BIST Scanner 2.0 — Quant + Fundamentals")
st.caption("Screening voor onderzoek en vergelijking. Geen persoonlijk financieel advies; controleer gegevens en bedrijfsrapporten voordat je handelt.")

with st.sidebar:
    st.header("Scaninstellingen")
    universe = st.multiselect("Aandelenuniversum", WATCHLIST, default=WATCHLIST)
    sort_by = st.selectbox("Rangschikken op", ["Totaalscore", "Technische score", "Fundamentele score", "Rendement 1m %", "Rendement 3m %"])
    min_data = st.selectbox("Datadekking", ["Alle resultaten", "Alleen met fundamentele data"])
    st.caption("Yahoo Finance-data kan vertraagd, onvolledig of onjuist zijn. Verifieer fundamentele cijfers bij KAP/bedrijfsrapporten.")

macro = get_macro_data()
m1, m2, m3 = st.columns(3)
with m1:
    st.metric("USD/TRY", f"₺{macro['usd_try']:.3f}" if macro["usd_try"] is not None else "Niet beschikbaar")
with m2:
    st.metric("BIST 100 — 3 maanden", f"{macro['xu100_return']:+.2f}%" if macro["xu100_return"] is not None else "Niet beschikbaar")
with m3:
    st.metric("BIST 100 laatste koers", f"{macro['xu100_price']:,.0f}" if macro["xu100_price"] is not None else "Niet beschikbaar")

st.divider()
st.subheader("Nieuwsmonitor — Turkije, SPK, fondsen en bedrijfsresultaten")
news = get_news()
if news.empty:
    st.info("Nieuwsfeed kon niet worden opgehaald. Dit betekent niet dat er geen risico's of nieuws zijn.")
else:
    for _, item in news.head(10).iterrows():
        title = str(item["Titel"])
        if item["Link"]:
            st.markdown(f"- [{title}]({item['Link']})  \n  <small>{item['Bron']} · {item['Datum']}</small>", unsafe_allow_html=True)
        else:
            st.write(f"- {title}")

st.divider()
st.subheader("Aandelenranglijst")
st.write("De score is een hulpmiddel om verder onderzoek te prioriteren. Een lage RSI is op zichzelf geen koopargument en een lage waarderingsratio kan op bedrijfsrisico wijzen.")

if st.button("Start scan", type="primary", use_container_width=True):
    if not universe:
        st.warning("Selecteer minimaal één aandeel in de zijbalk.")
    else:
        rows = []
        progress = st.progress(0, text="Scan voorbereiden...")
        for i, ticker in enumerate(universe):
            progress.progress((i + 1) / len(universe), text=f"Analyseren: {ticker}")
            result = analyze_stock(ticker)
            if result:
                rows.append(result)
        progress.empty()

        if not rows:
            st.error("Geen bruikbare resultaten ontvangen. Controleer internetverbinding, tickers en databron.")
        else:
            results = pd.DataFrame(rows)
            if min_data == "Alleen met fundamentele data":
                results = results[results["Fundamentele score"].notna()]
            if results.empty:
                st.warning("Geen aandelen met beschikbare fundamentele data in deze scan.")
            else:
                results = results.sort_values(by=sort_by, ascending=False, na_position="last").reset_index(drop=True)
                st.session_state["bist_scan_results"] = results
                st.success(f"Scan klaar: {len(results)} aandelen met bruikbare koersdata.")

if "bist_scan_results" in st.session_state:
    results = st.session_state["bist_scan_results"]
    display_cols = [
        "Bedrijf", "Ticker", "Koers (TRY)", "Rendement 1m %", "Rendement 3m %",
        "RSI", "Technische score", "Fundamentele score", "Totaalscore",
        "P/E", "P/B", "Winstmarge %", "Omzetgroei %", "Koersdoelruimte %", "Datadekking"
    ]
    st.dataframe(results[display_cols], use_container_width=True, hide_index=True)
    csv = results.to_csv(index=False).encode("utf-8-sig")
    st.download_button("Download resultaten als CSV", data=csv, file_name="bist_scanner_results.csv", mime="text/csv")

    st.subheader("Detailanalyse per aandeel")
    for _, row in results.iterrows():
        with st.expander(f"{row['Bedrijf']} ({row['Ticker']}) — score {row['Totaalscore']}/10"):
            c1, c2, c3 = st.columns(3)
            c1.metric("Technische score", f"{row['Technische score']}/10")
            c2.metric("Fundamentele score", f"{row['Fundamentele score']}/10" if pd.notna(row["Fundamentele score"]) else "Niet beschikbaar")
            c3.metric("RSI", f"{row['RSI']}" if pd.notna(row["RSI"]) else "N.B.")
            st.write(f"**Technische signalen:** {row['Technische signalen']}")
            st.write(f"**Fundamentele signalen:** {row['Fundamentele signalen']}")
            st.write(f"**Datadekking:** {row['Datadekking']}")
            st.write(f"**Analisten:** {row['Analistenadvies']} · aantal: {row['Aantal analisten']}")
            st.write(f"**Analistenkoersdoel:** ₺{row['Analistenkoersdoel'] if pd.notna(row['Analistenkoersdoel']) else 'N.B.'} · mogelijke ruimte: {row['Koersdoelruimte %'] if pd.notna(row['Koersdoelruimte %']) else 'N.B.'}%")
            st.write(f"**Indicatieve niveaus op basis van ATR:** steun/stop ₺{row['ATR-stop (indicatief)']} · weerstand ₺{row['Indicatieve weerstand']} · doel ₺{row['ATR-doel (indicatief)']}")
            st.caption("ATR-niveaus zijn uitsluitend volatiliteitsreferenties. Ze zijn geen gevalideerde handelsstrategie of gegarandeerde stop-loss/koersdoelen.")

st.divider()
with st.expander("Wat deze versie nog niet doet — belangrijk"):
    st.markdown("""
- **Geen backtest:** de scores zijn nog niet bewezen winstgevend. Historische tests met transactiekosten, slippage en survivorship-bias-controles moeten volgen.
- **Geen automatische AI-review:** de app gebruikt nog geen taalmodel om nieuws of analyses onafhankelijk te controleren. Dat moet via een expliciet gekoppelde API worden toegevoegd.
- **Nieuws is geen sentimentmodel:** de RSS-feed toont koppen; ze worden niet betrouwbaar automatisch als positief of negatief geclassificeerd.
- **Fundamentele gegevens zijn niet gegarandeerd actueel:** controleer kwartaalcijfers en toelichtingen via KAP en de officiële bedrijfsrapporten.
- **Geen automatische orders:** de app plaatst geen transacties bij je broker.
""")
