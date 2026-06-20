import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# ==============================================================================
# 1. UI CONFIGURATION & HEADERS
# ==============================================================================
st.set_page_config(page_title="Nice & Boring Dividend Screener", layout="wide")
st.title("🛡️ The 'Nice & Boring' Dividend Safety Screener")
st.subheader("Evaluating Corporate Capital Allocation & Pricing Power (2018 - Present)")

# ==============================================================================
# 2. SIDEBAR CONTROLS
# ==============================================================================
st.sidebar.header("Macro Stress-Test Suite")
st.sidebar.markdown("Simulate structural pricing power and future compounding timelines.")

inflation_rate = st.sidebar.slider(
    label="Simulated Annual Inflation Rate (%)",
    min_value=0.0,
    max_value=15.0,
    value=2.5,
    step=0.1,
)

projection_years = st.sidebar.slider(
    label="Future Projection Horizon (Years)",
    min_value=5,
    max_value=40,
    value=5,
    step=1,
)

# ==============================================================================
# 3. TICKER INPUT
# ==============================================================================
st.markdown("### 🔍 Enterprise Search Pipeline")
ticker_input = st.text_input(
    label="Enter Ticker Symbols (separated by commas):",
    value="JNJ, VOO, GLD, PG, KO, XPAY",
)

tickers = [t.strip().upper() for t in ticker_input.split(",") if t.strip()]

if len(tickers) == 0:
    st.error("❌ Action Required: Please enter at least one ticker symbol.")
    st.stop()

# ==============================================================================
# 4. DATA PROCESSING ENGINE
# ==============================================================================
@st.cache_data(ttl=3600)
def fetch_and_analyze_dividend_data(ticker_list, start_year=2018):
    results = {}
    current_year = datetime.now().year
    
    for ticker in ticker_list:
        try:
            asset = yf.Ticker(ticker)
            info = asset.info
            
            if not info or 'quoteType' not in info:
                continue
                
            quote_type = info.get('quoteType', 'EQUITY').upper()
            company_name = info.get('longName', ticker)
            
            # --- EXTRACT CURRENT DIVIDEND % (FIXED FORMATTING BUG) ---
            raw_yield = info.get('dividendYield', 0.0)
            current_yield = (raw_yield * 100) if raw_yield else 0.0
            
            beta = info.get('beta', 1.0) if info.get('beta') else 1.0

            # --- EXTRACT AND ANALYZE PAYOUT FREQUENCY (SCHEDULE) ---
            dividends_history = asset.dividends.loc[f"{start_year}-01-01":]
            
            if not dividends_history.empty:
                # Filter for a representative full historical year (e.g., 2024 or 2025) to judge frequency
                sample_year = current_year - 1
                payouts_in_sample = dividends_history[dividends_history.index.year == sample_year]
                
                # If sample year is completely blank, fallback to counting all rows divided by historical years
                if payouts_in_sample.empty:
                    unique_years = len(set(dividends_history.index.year))
                    payout_frequency = len(dividends_history) / unique_years if unique_years > 0 else 0
                else:
                    payout_frequency = len(payouts_in_sample)
                
                # Determine Schedule String based on frequency clusters
                if 10 <= payout_frequency <= 13:
                    schedule = "Monthly"
                elif 3 <= payout_frequency <= 5:
                    schedule = "Quarterly"
                elif 1 <= payout_frequency <= 2:
                    schedule = "Bi-Annually / Annually"
                elif payout_frequency > 13:
                    schedule = "Weekly / Variable"
                else:
                    schedule = "Irregular Schedule"
                
                # Resample and clean up annual dividend totals for growth velocity
                annual_divs = dividends_history.resample('YE').sum()
                annual_divs = annual_divs[annual_divs.index.year < current_year]
            else:
                schedule = "N/A (No Payouts)"
                annual_divs = pd.Series(dtype=float)
            
            # Calculate Payout Velocity
            if len(annual_divs) >= 2 and float(annual_divs.iloc) > 0:
                cagr = (float(annual_divs.iloc[-1]) / float(annual_divs.iloc)) ** (1 / (len(annual_divs) - 1)) - 1
                div_growth_cagr = cagr * 100
            else:
                div_growth_cagr = info.get('dividendGrowthRate5Y', 0.0) * 100 if info.get('dividendGrowthRate5Y') else 0.0
            
            # Extract FCF Payout Ratio cleanly 
            fcf_payout_ratio = 999.0
            if quote_type == "EQUITY":
                cashflow = asset.cashflow
                financials = asset.financials
                if not cashflow.empty and not financials.empty:
                    cf_t = cashflow.T
                    fin_t = financials.T
                    available_years = cf_t.index.intersection(fin_t.index)
                    if not available_years.empty:
                        cf_t = cf_t.loc[available_years]
                        ocf_col = 'Operating Cash Flow' if 'Operating Cash Flow' in cf_t.columns else cf_t.columns
                        capex_col = [c for c in cf_t.columns if 'Capital Expenditures' in str(c)]
                        
                        recent_ocf = float(cf_t[ocf_col].iloc)
                        recent_capex = float(cf_t[capex_col].iloc) if capex_col else 0.0
                        recent_fcf = recent_ocf + recent_capex if recent_capex < 0 else recent_ocf - recent_capex
                        
                        div_col = [c for c in cf_t.columns if 'Dividend' in str(c)]
                        recent_div_paid = abs(float(cf_t[div_col].iloc)) if div_col else 0.0
                        
                        if recent_fcf > 0:
                            fcf_payout_ratio = float((recent_div_paid / recent_fcf) * 100)
            
            results[ticker] = {
                "name": company_name,
                "quote_type": quote_type,
                "yield": float(current_yield),
                "schedule": schedule,
                "payout_ratio": float(fcf_payout_ratio),
                "div_growth_cagr": float(div_growth_cagr),
                "beta": float(beta)
            }
        except Exception:
            continue
            
    return results

with st.spinner("Processing deep global ticker data and running exclusions..."):
    analysis_data = fetch_and_analyze_dividend_data(tickers)

# ==============================================================================
# 5. SCORECARD MATRIX DISPLAY
# ==============================================================================
if analysis_data:
    st.markdown("### 📊 Capital Allocation Scorecard")
    
    grid_data = []
    for ticker, data in analysis_data.items():
        payout_val = data["payout_ratio"]
        
        # Override structural displays for ETFs/Passive funds
        if data["quote_type"] != "EQUITY":
            payout_display = f"N/A ({data['quote_type']})"
            safety_status = "🔵 Passive Fund Pool"
            schedule_display = "Quarterly (ETF Proxy)" if "ETF" in data["quote_type"] else data["schedule"]
        elif payout_val == 999.0:
            payout_display = "Data Stalled"
            safety_status = "🟡 Moderate Allocation"
            schedule_display = data["schedule"]
        else:
            payout_display = f"{payout_val:.2f}%"
            schedule_display = data["schedule"]
            if payout_val < 60.0 and data["beta"] < 1.0:
                safety_status = "🟢 Nice & Boring (Safe)"
            elif payout_val > 85.0 or data["beta"] > 1.3:
                safety_status = "🔴 Value Trap (High Risk)"
            else:
                safety_status = "🟡 Moderate Allocation"
            
        grid_data.append({
            "Ticker": ticker,
            "Asset Classification": data["name"],
            "Current Dividend %": f"{data['yield']:.2f}%",
            "Schedule": schedule_display,
            "FCF Payout Ratio": payout_display,
            "5Y Payout Velocity": f"{data['div_growth_cagr']:.2f}%",
            "Beta Risk": f"{data['beta']:.2f}",
            "Allocation Grade": safety_status
        })
        
    df_grid = pd.DataFrame(grid_data)
    st.dataframe(df_grid, use_container_width=True, hide_index=True)
    
    st.markdown(f"### 🔮 Compounded Performance Projection Horizon ({projection_years} Years)")
    st.info("💡 Pro Tip: Look for assets where strong historical growth velocity pairs with low beta risk to protect family wealth.")
else:
    st.error("The underlying execution engine could not find valid asset data. Correct ticker entry formatting.")
