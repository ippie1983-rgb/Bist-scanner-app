def analyze_stock(ticker, dev_risk):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1mo")
        if hist is None or hist.empty or len(hist) < 5: 
            return None
        
        info = stock.info or {}
        name = str(info.get('longName') or ticker)
        price = float(hist['Close'].iloc[-1])
        
        target_mean = info.get('targetMeanPrice')
        raw_rec = str(info.get('recommendationKey', 'hold')).upper()
        
        advies_map = {'BUY': 'KOPEN', 'STRONG_BUY': 'STERK KOPEN', 'HOLD': 'HOUDEN', 'UNDERPERFORM': 'ONDERPRESTATIE', 'SELL': 'VERKOPEN'}
        analyst_recommendation = advies_map.get(raw_rec, 'HOUDEN')
        num_analysts = info.get('numberOfAnalystOpinions', 0)
        
        profit_margin = info.get('profitMargins', 0.0)
        profit_margin_pct = round(profit_margin * 100, 2) if profit_margin else 0.0
        
        revenue_growth = info.get('revenueGrowth', 0.0)
        revenue_growth_pct = round(revenue_growth * 100, 2) if revenue_growth else 0.0
        
        # --- NAUWKEURIGE BEREKENING P/E EN P/B VIA FINANCIALS & BALANCE SHEET ---
        pe_val = 0.0
        pb_val = 0.0
        try:
            # P/E berekenen via Netto Winst (Trailing Net Income) en Marktkapitalisatie
            financials = stock.financials
            shares = info.get('sharesOutstanding')
            if financials is not None and not financials.empty and shares and shares > 0:
                # Zoek naar net income in de financials
                net_income_rows = [row for row in financials.index if 'Net Income' in row]
                if net_income_rows:
                    net_income = financials.loc[net_income_rows[0]].iloc[0]
                    market_cap = price * shares
                    if net_income and net_income > 0:
                        pe_val = round(market_cap / net_income, 2)
            
            # Fallback op info als financials faalt
            if pe_val == 0.0 and info.get('trailingPE'):
                pe_val = round(float(info.get('trailingPE')), 2)
        except Exception:
            pe_val = round(float(info.get('trailingPE', 0.0)), 2) if info.get('trailingPE') else 0.0

        try:
            # P/B berekenen via Boekwaarde (Total Stockholder Equity)
            balance_sheet = stock.balance_sheet
            shares = info.get('sharesOutstanding')
            if balance_sheet is not None and not balance_sheet.empty and shares and shares > 0:
                equity_rows = [row for row in balance_sheet.index if 'Stockholder Equity' in row or 'Total Equity' in row]
                if equity_rows:
                    total_equity = balance_sheet.loc[equity_rows[0]].iloc[0]
                    book_value_per_share = total_equity / shares
                    if book_value_per_share > 0:
                        pb_val = round(price / book_value_per_share, 2)
            
            if pb_val == 0.0 and info.get('priceToBook'):
                pb_val = round(float(info.get('priceToBook')), 2)
        except Exception:
            pb_val = round(float(info.get('priceToBook', 0.0)), 2) if info.get('priceToBook') else 0.0
        # -----------------------------------------------------------------------
        
        if len(hist) >= 2:
            h, l, c = float(hist['High'].iloc[-2]), float(hist['Low'].iloc[-2]), float(hist['Close'].iloc[-2])
        else:
            h, l, c = price, price, price
            
        pivot = (h + l + c) / 3
        r1 = round((2 * pivot) - l, 2)
        s1 = round((2 * pivot) - h, 2)
        
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
        
        points = 4.0
        reasons = []
        
        if price > sma: 
            points += 1.5
            reasons.append("Koers boven korte SMA (+1.5p)")
            
        if 30 <= rsi <= 80: 
            points += 1.5
            reasons.append(f"Gezonde RSI ({rsi:.1f}) (+1.5p)")
            
        if ticker in ['THYAO.IS', 'EREGL.IS', 'SISE.IS', 'TUPRS.IS'] and dev_risk:
            points += 2.0
            reasons.append("Devaluatie-buffer actief (+2.0p)")
            
        if raw_rec in ['BUY', 'STRONG_BUY']:
            points += 1.0
            reasons.append(f"Analisten consensus: {analyst_recommendation} (+1.0p)")
        elif raw_rec in ['UNDERPERFORM', 'SELL']:
            points -= 1.0
            reasons.append(f"Analisten consensus: {analyst_recommendation} (-1.0p)")
            
        score = round(min(10.0, max(1.0, points)), 1)
        
        if len(hist) >= 14:
            atr = float((hist['High'] - hist['Low']).rolling(14).mean().iloc[-1])
        else:
            atr = price * 0.03
        
        toekomst_outlook = f"Winstmarge: {profit_margin_pct}%. Omzetgroei j-o-j: {revenue_growth_pct}%. Koersdoel analisten: ₺{target_mean if target_mean else 'N.B.'}."

        stock_data = {
            "Ticker": ticker, 
            "Bedrijf": name, 
            "Prijs (TRY)": round(price, 2), 
            "RSI": round(rsi, 1),
            "Cijfer": score, 
            "P/E (FK)": pe_val,
            "P/B (PD/DD)": pb_val,
            "Winstmarge %": profit_margin_pct,
            "Omzetgroei %": revenue_growth_pct,
            "Koersdoel (₺)": round(target_mean, 2) if target_mean else 0.0,
            "Advies": analyst_recommendation,
            "Analisten": num_analysts,
            "Res1": r1, 
            "Sup1": s1, 
            "StopLoss": round(price - atr, 2),
            "Doel": round(price + (1.5 * atr), 2), 
            "Toekomst Outlook": toekomst_outlook,
            "Onderbouwing": ", ".join(reasons)
        }
        return stock_data

    except Exception:
        return None
