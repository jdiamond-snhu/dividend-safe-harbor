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
    value=10,  # Default to 10 years, adjustable up to 40
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
# Master manual overrides to correct yfinance data omissions for known assets
SCHEDULE_OVERRIDES = {
    "XPAY": "Monthly",
    "O": "Monthly",
    "MAIN": "Monthly"
}

@st.cache_data(ttl=3600)
def fetch_and_analyze_dividend_data(ticker_list, start_year=2018):
    results = {}
    current_year = datetime.now().year
    
    for ticker in ticker_list:
        try:
            asset = yf.Ticker(ticker)
            
            try:
                info = asset.info
                if info is None:
                    info = {}
            except Exception:
                info = {}
                
            quote_type = info.get('quoteType', 'EQUITY').upper()
            company_name = info.get('longName', ticker)
            
            # Extract baseline yield securely
            raw_yield = info.get('dividendYield', 0.0)
            current_yield = (raw_yield * 100) if raw_yield else 0.0
            beta = info.get('beta', 1.0) if info.get('beta') else 1.0

            # --- SCHEDULE ANALYZER WITH HARDCODED OVERRIDES ---
            if ticker in SCHEDULE_OVERRIDES:
                schedule = SCHEDULE_OVERRIDES[ticker]
                try:
                    dividends_history = asset.dividends.loc[f"{start_year}-01-01":]
                except Exception:
                    dividends_history = pd.Series(dtype=float)
            else:
                try:
                    dividends_history = asset.dividends.loc[f"{start_year}-01-01":]
                except Exception:
                    dividends_history = pd.Series(dtype=float)
                
                if not dividends_history.empty:
                    sample_year = current_year - 1
                    payouts_in_sample = dividends_history[dividends_history.index.year == sample_year]
                    
                    if payouts_in_sample.empty:
                        unique_years = len(set(dividends_history.index.year))
                        payout_frequency = len(dividends_history) / unique_years if unique_years > 0 else 0
                    else:
                        payout_frequency = len(payouts_in_sample)
                    
                    if 10 <= payout_frequency <= 13:
                        schedule = "Monthly"
                    elif 3 <= payout_frequency <= 5:
                        schedule = "Quarterly"
                    elif 1 <= payout_frequency <= 2:
                        schedule = "Bi-Annually / Annually"
                    else:
                        schedule = "Irregular Schedule"
                else:
                    schedule = "N/A (No Payouts)"
            
            # --- HISTORICAL CAGR VELOCITY BASELINE ---
            if not dividends_history.empty:
                annual_divs = dividends_history.resample('YE').sum()
                annual_divs = annual_divs[annual_divs.index.year < current_year]
            else:
                annual_divs = pd.Series(dtype=float)
                
            if len(annual_divs) >= 2 and float(annual_divs.iloc[0]) > 0:
                cagr = (float(annual_divs.iloc[-1]) / float(annual_divs.iloc[0])) ** (1 / (len(annual_divs) - 1)) - 1
                historical_cagr_pct = cagr * 100
            else:
                historical_cagr_pct = info.get('dividendGrowthRate5Y', 0.0) * 100 if info.get('dividendGrowthRate5Y') else 0.0
            
            # Extract FCF Payout Ratio
            fcf_payout_ratio = 999.0
            if quote_type == "EQUITY":
                try:
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
                            
                            recent_ocf = float(cf_t[ocf_col].iloc[0])
                            recent_capex = float(cf_t[capex_col].iloc[0]) if capex_col else 0.0
                            recent_fcf = recent_ocf + recent_capex if recent_capex < 0 else recent_ocf - recent_capex
                            
                            div_col = [c for c in cf_t.columns if 'Dividend' in str(c)]
                            recent_div_paid = abs(float(cf_t[div_col].iloc[0])) if div_col else 0.0
                            
                            if recent_fcf > 0:
                                fcf_payout_ratio = float((recent_div_paid / recent_fcf) * 100)
                except Exception:
                    fcf_payout_ratio = 999.0
            
            results[ticker] = {
                "name": company_name,
                "quote_type": quote_type,
                "yield": float(current_yield),
                "schedule": schedule,
                "payout_ratio": float(fcf_payout_ratio),
                "historical_cagr": float(historical_cagr_pct),
                "beta": float(beta)
            }
        except Exception:
            continue
            
    return results

with st.spinner("Processing deep global ticker data and running exclusions..."):
    analysis_data = fetch_and_analyze_dividend_data(tickers)

# ==============================================================================
# 5. SCORECARD MATRIX DISPLAY WITH DYNAMIC HORIZON COMPREHENSION
# ==============================================================================
if analysis_data:
    st.markdown("### 📊 Capital Allocation Scorecard")
    
    grid_data = []
    for ticker, data in analysis_data.items():
        payout_val = data["payout_ratio"]
        current_yield_pct = data["yield"]
        growth_velocity_cagr = data["historical_cagr"] / 100.0
        
        # --- DYNAMIC MATRIX CALCULATION ---
        # Projecting the nominal Forward Yield on Cost exactly at the slider's year horizon
        # Formula: Initial Yield * (1 + Growth Rate) ^ Chosen Horizon Years
        projected_horizon_yield = current_yield_pct * ((1 + growth_velocity_cagr) ** projection_years)
        
        # Format display output labels
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
            "Current Dividend %": f"{current_yield_pct:.2f}%",
            "Schedule": schedule_display,
            "FCF Payout Ratio": payout_display,
            f"{projection_years}Y Projected Yield on Cost": f"{projected_horizon_yield:.2f}%",
            "Beta Risk": f"{data['beta']:.2f}",
            "Allocation Grade": safety_status
        })
        
    df_grid = pd.DataFrame(grid_data)
    st.dataframe(df_grid, use_container_width=True, hide_index=True)
    
    st.markdown(f"### 🔮 Compounded Performance Projection Horizon ({projection_years} Years)")
    st.error("The underlying execution engine could not find valid asset data. Correct ticker entry formatting.")
