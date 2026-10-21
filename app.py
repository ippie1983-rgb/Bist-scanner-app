import yfinance as yf
import pandas as pd
import numpy as np
import urllib.request
import xml.etree.ElementTree as ET

# Uitgebreide BIST Watchlist (Borsa Istanbul Aandelen)
WATCHLIST = [
    'GARAN.IS', 'AKBNK.IS', 'EREGL.IS', 'THYAO.IS', 
    'TUPRS.IS', 'KCHOL.IS', 'SAHOL.IS', 'BIMAS.IS',
    'YKBNK.IS', 'ISCTR.IS', 'ASELS.IS', 'SISE.IS', 'MGROS.IS'
]

def analyze_macro_and_global_news():
    print("=" * 75)
    print(" 🧠 BIST QUANT-SYSTEEM: ULTIEME MACRO, NIEUWS & ANALISTEN ANALYSE")
    print("=" * 75)
    
    # 1. USD/TRY Devaluatie-tracking
    usd_try = 49.50
    try:
        df = yf.Ticker("USDTRY=X").history(period="5d")
        if not df.empty and 'Close' in df.columns:
            usd_try = float(df['Close'].iloc[-1])
    except Exception as e:
        print(f"⚠️ Waarschuwing USD/TRY ophalen: {e}")
        
    # 2. BIST 100 Benchmark Rendement (3 maanden)
    mkt_ret = 0.0
    try:
        df = yf.Ticker("XU100.IS").history(period="3mo")
        if not df.empty and len(df) > 1 and 'Close' in df.columns:
            mkt_ret = round(float((df['Close'].iloc[-1] - df['Close'].iloc[0]) / df['Close'].iloc[0]) * 100, 2)
    except Exception as e:
        print(f"⚠️ Waarschuwing BIST 100 ophalen: {e}")

    # 3. Live RSS / Financiële Nieuws & Schandalen Filter
    news_warnings = []
    try:
        url = "https://news.google.com/rss/search?q=Borsa+Istanbul+stock+market&hl=en-US&gl=US&ceid=US:en"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)
            for item in root.findall('.//item')[:5]:
                title = item.find('text') or item.find('title')
                if title is not None and title.text:
                    t_lower = title.text.lower()
                    if any(w in t_lower for w in ['investigation', 'spk', 'crash', 'scandal', 'fall', 'crisis', 'probe']):
                        news_warnings.append(title.text)
    except Exception:
        pass

    dev_risk = usd_try > 48.0
    print(f" 💱 USD/TRY Koers: ₺{usd_try:.2f} | BIST 100 (3m rendement): {mkt_ret}%")
    if news_warnings:
        print(f" 🚨 Let op (Nieuws-filter): {len(news_warnings)} marktwaarschuwing(en) gedetecteerd!")
        for w_item in news_warnings[:2]:
            print(f"     • {w_item}")
    else:
        print(" 🛡️ Nieuws-filter: Geen directe macro-schandalen of onderzoeken gedetecteerd.")
        
    return dev_risk, mkt_ret

def analyze_stock(ticker, dev_risk, mkt_ret):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1mo")
        if hist is None or hist.empty or len(hist) < 5: 
            return None, "Onvoldoende historische data beschikbaar"
        
        info = stock.info or {}
        name = str(info.get('longName') or ticker)
        price = float(hist['Close'].iloc[-1])
        
        # 4. Analistenconsensus & Koersdoelen integratie vanuit Ticker Info
        target_mean = info.get('targetMeanPrice')
        analyst_recommendation = info.get('recommendationKey', 'hold').upper()
        num_analysts = info.get('numberOfAnalystOpinions', 0)
        
        # Daytrading Pivot Niveaus (R1, S1 op basis van gisteren)
        if len(hist) >= 2:
            h, l, c = float(hist['High'].iloc[-2]), float(hist['Low'].iloc[-2]), float(hist['Close'].iloc[-2])
        else:
            h, l, c = price, price, price
            
        pivot = (h + l + c) / 3
        r1 = round((2 * pivot) - l, 2)
        s1 = round((2 * pivot) - h, 2)
        
        # Technische Indicatoren (SMA & RSI)
        sma = float(hist['Close'].rolling(min(10, len(hist))).mean().iloc[-1])
        delta = hist['Close'].diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        
        rsi = 50.0
        if not gain.empty and not loss.empty:
            rs_val = gain / loss
            rsi_series = 100 - (100 / (1 + rs_val))
            if not rsi_series.empty:
                rsi = float(rsi_series.iloc[-1])
        
        # 5. Geavanceerd Puntsysteem inclusief Analisten-advies
        points = 4.0
        reasons = []
        
        if price > sma: 
            points += 1.5
            reasons.append("Koers boven korte SMA (+1.5p)")
        if 30 <= rsi <= 80: 
            points += 1.5
            reasons.append(f"Gezonde RSI ({rsi:.1f}) (+1.5p)")
            
        # Devaluatie-buffer voor export / zware fondsen
        if ticker in ['THYAO.IS', 'EREGL.IS', 'SISE.IS', 'TUPRS.IS'] and dev_risk:
            points += 2.0
            reasons.append("🚨 Devaluatie-buffer actief (+2.0p)")
            
        # Analisten waardering bonus/straf
        if analyst_recommendation in ['BUY', 'STRONG_BUY']:
            points += 1.0
            reasons.append(f"📈 Analisten consensus: {analyst_recommendation} (+1.0p)")
        elif analyst_recommendation in ['UNDERPERFORM', 'SELL']:
            points -= 1.0
            reasons.append(f"📉 Analisten consensus: {analyst_recommendation} (-1.0p)")
            
        score = round(min(10.0, max(1.0, points)), 1)
        atr = float((
