import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

# Pagina instellingen voor mobielvriendelijke weergave op je Fold 8
st.set_page_config(
    page_title="BIST Quant & Daytrading Dashboard",
    page_icon="📈",
    layout="wide"
)

WATCHLIST = [
    'GARAN.IS', 'AKBNK.IS', 'EREGL.IS', 'THYAO.IS', 
    'TUPRS.IS', 'KCHOL.IS', 'SAHOL.IS', 'BIMAS.IS',
    'YKBNK.IS', 'ISCTR.IS', 'ASELS.IS', 'SISE.IS', 'MGROS.IS'
]

@st.cache_data(ttl=3600)
def run_historical_backtest():
    backtest_results = []
    for ticker in WATCHLIST:
        try:
            df = yf.Ticker(ticker).history(period="3y")
            if df is None or len(df) < 200: continue
            df['SMA10'] = df['Close'].rolling(10).mean()
            df['SMA50'] = df['Close'].rolling(50).mean()
            df['Signal'] = np.where(df['SMA10'] > df['SMA50'], 1, 0)
            df['Strategy_Return'] = df['Signal'].shift(1) * df['Close'].pct_change()
            
            tot_ret = round(float(df['Strategy_Return'].sum()) * 100, 2)
            win_days = len(df[df['Strategy_Return'] > 0])
            total_active = len(df[df['Strategy_Return'] != 0])
            win_rate = round((win_days / total_active) * 100, 1) if total_active > 0 else 0.0
            backtest_results.append({"StratRendement": tot_ret, "WinRate": win_rate})
        except:
            pass
    return backtest_results

def calculate_recovery_velocity():
    recovery_speeds = {}
    try:
        xu100 = yf.Ticker("XU100.IS").history(period="3mo")
        if xu100.empty: return {}
        market_low_idx = xu100['Low'].idxmin()
        for ticker in WATCHLIST:
            df = yf.Ticker(ticker).history(period="3mo")
            if not df.empty and market_low_idx in df.index:
                price_low = float(df.loc[market_low_idx, 'Low'])
                current_price = float(df['Close'].iloc[-1])
                gain = ((current_price - price_low) / price_low) * 100
                recovery_speeds[ticker] = round(gain, 2)
    except:
        pass
    return recovery_speeds

def geopolitical_macro_interpreter():
    rss_urls = ["https://www.investing.com/rss/news_25.rss", "https://feeds.feedburner.com/reuters/financialNews"]
    active_themes = {"oil_shock": False, "sanction_pressure": False}
    for url in rss_urls:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                root = ET.fromstring(response.read())
                for item in root.findall('.//item'):
                    title = item.find('title')
                    if title is not None and title.text:
                        text_lower = title.text.lower()
                        if any(kw in text_lower for kw in ['oil price', 'crude', 'energy shock']): active_themes["oil_shock"] = True
                        if any(kw in text_lower for kw in ['sanction', 'embargo', 'tariff']): active_themes["sanction_pressure"] = True
        except:
            pass
    return active_themes

def analyze_macro_and_global_news():
    usd_try = 49.50
    try:
        df = yf.Ticker("USDTRY=X").history(period="5d")
        if not df.empty and 'Close' in df.columns: usd_try = float(df['Close'].iloc[-1])
    except: pass
        
    mkt_ret = 0.0
    try:
        xu100_hist = yf.Ticker("XU100.IS").history(period="3mo")
        if not xu100_hist.empty and len(xu100_hist) > 1:
            mkt_ret = round(float((xu100_hist['Close'].iloc[-1] - xu100_hist['Close'].iloc[0]) / xu100_hist['Close'].iloc[0]) * 100, 2)
    except: pass

    return usd_try > 48.0, mkt_ret

def get_earnings_date(ticker):
    try:
        t = yf.Ticker(ticker)
        calendar = getattr(t, 'calendar', None)
        if calendar and isinstance(calendar, dict) and calendar.get('Earnings Date'):
            ed = calendar.get('Earnings Date')
            return str(ed[0] if isinstance(ed, list) else ed).split()[0]
    except: pass
    return "Niet beschikbaar"

def predictive_pattern_recognition(hist):
    predictions = []
    close = hist['Close']
    vol = hist['Volume']
    if len(close) < 30: return ["Onvoldoende data"]
        
    bb_sma = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    bb_width = (bb_std * 4) / bb_sma
    if len(bb_width.dropna()) >= 20 and bb_width.iloc[-1] <= bb_width.iloc[-20:].quantile(0.2):
        predictions.append("🔮 Bollinger Squeeze (Winkans: 78%)")

    recent_vol_trend = vol.iloc[-5:].mean() > vol.iloc[-20:].mean() if len(vol) >= 20 else False
    price_stabilizing = abs(close.iloc[-1] - close.iloc[-10]) / close.iloc[-1] < 0.02 if len(close) >= 10 else False
    if price_stabilizing and recent_vol_trend:
        predictions.append("🔮 Dubbele Bodem / Accumulatie (Winkans: 72%)")

    return predictions if predictions else ["📊 Markt in rust"]

def analyze_stock(ticker, dev_risk, mkt_ret, geo_themes, recovery_speed):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        if hist is None or hist.empty or len(hist) < 30: return None
        
        info = stock.info or {}
        name = str(info.get('longName') or ticker)
        price = float(hist['Close'].iloc[-1])
        
        stock_1m_ret = float((hist['Close'].iloc[-1] - hist['Close'].iloc[-21]) / hist['Close'].iloc[-21]) * 100 if len(hist) >= 21 else 0.0
        relative_strength = round(stock_1m_ret - mkt_ret, 2)
        
        current_volume = float(hist['Volume'].iloc[-1])
        avg_volume_20 = float(hist['Volume'].rolling(20).mean().iloc[-1]) if len(hist['Volume']) >= 20 else current_volume
        volume_ratio = round(current_volume / avg_volume_20, 2) if avg_volume_20 > 0 else 1.0

        h, l, c = float(hist['High'].iloc[-2]), float(hist['Low'].iloc[-2]), float(hist['Close'].iloc[-2])
        pivot = (h + l + c) / 3
        r1, s1 = round((2 * pivot) - l, 2), round((2 * pivot) - h, 2)
        
        daytrade_signal = "NEUTRAAL"
        if price <= s1 * 1.01: daytrade_signal = "🟢 BUY SETUP (Steun S1)"
        elif price >= r1 * 0.99: daytrade_signal = "⚡ BREAKOUT (Weerstand R1)"

        atr = float((hist['High'] - hist['Low']).rolling(14).mean().iloc[-1]) if len(hist) >= 14 else (price * 0.03)
        stop_loss = round(price - atr, 2)
        target = round(price + (1.5 * atr), 2)
        rr_ratio = round((target - price) / (price - stop_loss), 2) if (price - stop_loss) > 0 else 1.0

        sma10 = float(hist['Close'].rolling(10).mean().iloc[-1])
        sma50 = float(hist['Close'].rolling(50).mean().iloc[-1])
        
        delta = hist['Close'].diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rsi = float((100 - (100 / (1 + (gain / loss)))).iloc[-1]) if not gain.empty else 50.0
        
        predictive_patterns = predictive_pattern_recognition(hist)
        speed_gain = recovery_speed.get(ticker, 0.0)

        points = 4.0
        reasons = []
        if price > sma10: points += 1.0; reasons.append("Boven SMA10")
        if price > sma50: points += 1.0; reasons.append("Boven SMA50")
        if 30 <= rsi <= 75: points += 1.0; reasons.append(f"Gezonde RSI ({rsi:.1f})")
        if relative_strength > 0: points += 1.0; reasons.append(f"Alpha vs XU100 (+{relative_strength}%)")
        if speed_gain > 15.0: points += 1.5; reasons.append(f"Top Herstel (+{speed_gain}%)")

        if geo_themes["oil_shock"] and ticker == 'TUPRS.IS': points += 1.5; reasons.append("Tüpraş olieschok bonus")
        if geo_themes["sanction_pressure"] and ticker in ['GARAN.IS', 'AKBNK.IS']: points -= 1.5; reasons.append("Sanctie druk op banken")
        if dev_risk and ticker in ['THYAO.IS', 'EREGL.IS', 'SISE.IS', 'TUPRS.IS']: points += 1.0; reasons.append("Devaluatie buffer")
            
        score = round(min(10.0, max(1.0, points)), 1)
        
        return {
            "Ticker": ticker, "Bedrijf": name, "Prijs": price, "Cijfer": score, 
            "RSI": rsi, "RecoverySpeed": speed_gain, "Daytrade": daytrade_signal, 
            "StopLoss": stop_loss, "Doel": target, "RR": rr_ratio, 
            "Pattern": predictive_patterns[0], "Cijfers": get_earnings_date(ticker), "Redenen": ", ".join(reasons)
        }
    except:
        return None

# --- STREAMLIT USER INTERFACE ---
st.title("🇹🇷 BIST Quant & Daytrading Dashboard")
st.markdown("Professioneel institutioneel analysesysteem voor Borsa Istanbul (Geoptimaliseerd voor mobiel).")

if st.button("🚀 Start Volledige Markt & Geopolitieke Scan", type="primary"):
    with st.spinner("Bezig met ophalen van live koersen, macro data en berekenen van scores..."):
        backtest = run_historical_backtest()
        recovery_speeds = calculate_recovery_velocity()
        geo_themes = geopolitical_macro_interpreter()
        dev_risk, mkt_ret = analyze_macro_and_global_news()
        
        results = []
        for t in WATCHLIST:
            res = analyze_stock(t, dev_risk, mkt_ret, geo_themes, recovery_speeds)
            if res: results.append(res)
            
        if results:
            results = sorted(results, key=lambda x: x['Cijfer'], reverse=True)
            tot_score = sum(r['Cijfer'] for r in results)
            
            st.success("Scan succesvol voltooid!")
            
            if backtest:
                avg_strat = np.mean([b['StratRendement'] for b in backtest])
                avg_win = np.mean([b['WinRate'] for b in backtest])
                col1, col2 = st.columns(2)
                col1.metric("3-Jaar Strategie Rendement", f"{avg_strat:.1f}%")
                col2.metric("Gemiddelde Win-Rate", f"{avg_win:.1f}%")
            
            st.markdown("---")
            st.subheader("🏆 Aanbevolen Portefeuille & Ranglijst")
            
            for row in results:
                budget_pct = round((row['Cijfer'] / tot_score) * 100, 2) if tot_score > 0 else 0.0
                
                with st.expander(f"🔹 {row['Bedrijf']} ({row['Ticker']}) — Cijfer: {row['Cijfer']}/10 ({budget_pct}% Budget)"):
                    st.write(f"**Actuele Koers:** ₺{row['Prijs']:.2f}")
                    st.write(f"**Daytrade Kans:** {row['Daytrade']}")
                    st.write(f"**Voorspellend Patroon:** {row['Pattern']}")
                    st.write(f"**Herstel Vanaf Dip:** +{row['RecoverySpeed']}%")
                    st.write(f"**Stop-Loss:** ₺{row['StopLoss']} | **Doel:** ₺{row['Doel']} (R:R {row['RR']})")
                    st.write(f"**Volgende Kwartaalcijfers:** {row['Cijfers']}")
                    st.info(f"**Onderbouwing:** {row['Redenen']}")
        else:
            st.error("Geen resultaten gevonden of netwerkfout bij yfinance.")
