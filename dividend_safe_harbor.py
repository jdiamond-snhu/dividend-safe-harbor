import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# ==============================================================================
# 1. UI CONFIGURATION & HEADERS
# ==============================================================================
st.set_page_config(page_title="Nice & Boring Dividend Screener", layout="wide")
st.title("🛡️ The 'Nice & Boring' Dividend Safety Screener")
st.subheader("Evaluating Corporate Capital Allocation & Pricing Power (2018 - Present)")

# ==============================================================================
# 2. SIDEBAR CONTROLS (MACRO INFLATION & TIMELINE SLIDERS)
# ==============================================================================
st.sidebar.header("Macro Stress-Test Suite")
st.sidebar.markdown(
    "Simulate structural pricing power and future compounding timelines."
)

# Slider 1: Reagan-Volcker Inflation Simulator
inflation_rate = st.sidebar.slider(
    label="Simulated Annual Inflation Rate (%)",
    min_value=0.0,
    max_value=15.0,
    value=2.5,
    step=0.1,
    help="Default is 2.5%. Push past 13% to simulate the 1979-1981 Volcker tightening cycle.",
)

# Slider 2: Future Performance Projection Window (5 to 40 Years)
projection_years = st.sidebar.slider(
    label="Future Projection Horizon (Years)",
    min_value=5,
    max_value=40,
    value=10,
    step=1,
    help="Define the time frame over which to project future real value compounding.",
)

# ==============================================================================
# 3. TICKER INPUT & PIPELINE SANITIZATION
# ==============================================================================
st.markdown("### 🔍 Enterprise Search Pipeline")
ticker_input = st.text_input(
    label="Enter Ticker Symbols (separated by commas):",
    value="JNJ, VOO, GLD, PG, KO",
    help="Minimum: 1 ticker. Maximum: 10 tickers.",
)

# Clean, split, and filter inputs safely
raw_tickers = [t.strip().upper() for t in ticker_input.split(",") if t.strip()]

if len(raw_tickers) == 0:
    st.error("❌ Action Required: Please enter at least one ticker symbol.")
    st.stop()
elif len(raw_tickers) > 10:
    st.warning("⚠️ Optimization Limit: Truncating list to the first 10 tickers max.")
    tickers = raw_tickers[:10]
else:
    tickers = raw_tickers

# ==============================================================================
# 4. DATA PROCESSING & ROBUST METRIC COMPUTATION
# ==============================================================================
@st.cache_data(ttl=3600)
def fetch_and_analyze_dividend_data(ticker_list, start_year=2018):
    results = {}
    current_year = datetime.now().year
    
    for ticker in ticker_list:
        try:
            asset = yf.Ticker(ticker)
            info = asset.info
            
            # Defensive check for ticker validity
            if not info or 'quoteType' not in info:
                continue
                
            quote_type = info.get('quoteType', 'EQUITY').upper()
            company_name = info.get('longName', ticker)
            current_yield = info.get('dividendYield', 0.0) * 100 if info.get('dividendYield') else 0.0
            beta = info.get('beta', 1.0) if info.get('beta') else 1.0
            
            # Fetch historical dividend distribution series
            dividends_history = asset.dividends.loc[f"{start_year}-01-01":]
            
            # Resample dividends annually, but completely drop the partial current year 
            # to prevent artificial chart drops
            if not dividends_history.empty:
                annual_divs = dividends_history.resample('YE').sum()
                annual_divs = annual_divs[annual_divs.index.year < current_year]
            else:
                annual_divs = pd.Series(dtype=float)
            
            # Calculate 5-Year Dividend Growth Velocity using historical CAGR
            if len(annual_divs) >= 2 and annual_divs.iloc[0] > 0:
                cagr = (annual_divs.iloc[-1] / annual_divs.iloc[0]) ** (1 / (len(annual_divs) - 1)) - 1
                div_growth_cagr = cagr * 100
            else:
                # Fallback to institutional data point or zero for non-dividend payers
                div_growth_cagr = info.get('dividendGrowthRate5Y', 0.0) * 100 if info.get('dividendGrowthRate5Y') else 0.0
            
            # Handle Cash Flow parsing logic specifically for corporate equities
            fcf_payout_ratio = 999.0 # Default representation for non-applicable structures
            
            if quote_type == "EQUITY":
                cashflow = asset.cashflow
                financials = asset.financials
                
                if not cashflow.empty and not financials.empty:
                    cf_t = cashflow.T
                    fin_t = financials.T
                    available_years = cf_t.index.intersection(fin_t.index)
                    
                    if not available_years.empty:
                        cf_t = cf_t.loc[available_years]
                        ocf_col = 'Operating Cash Flow' if 'Operating Cash Flow' in cf_t.columns else cf_t.columns[0]
                        capex_col = [c for c in cf_t.columns if 'Capital Expenditures' in str(c)]
                        
                        recent_ocf = cf_t[ocf_col].iloc[0]
                        recent_capex = cf_t[capex_col[0]].iloc[0] if capex_col else 0.0
                        
                        # Calculate Free Cash Flow conservatively
                        recent_fcf = recent_ocf + recent_capex if recent_capex < 0 else recent_ocf - recent_capex
                        
                        div_col = [c for c in cf_t.columns if 'Dividend' in str(c)]
                        recent_div_paid = abs(cf_t[div_col[0]].iloc[0]) if div_col else 0.0
                        
                        if recent_fcf > 0:
                            fcf_payout_ratio = (recent_div_paid / recent_fcf) * 100
            
            # Package verified asset telemetry
            results[ticker] = {
                "name": company_name,
                "quote_type": quote_type,
                "yield": current_yield,
                "payout_ratio": fcf_payout_ratio,
                "div_growth_cagr": div_growth_cagr,
                "beta": beta,
                "annual_div_history": annual_divs
            }
            
        except Exception as e:
            st.error(f"Error parsing data pipeline for {ticker}: {str(e)}")
            
    return results

# Trigger data fetch processing
with st.spinner("Processing deep global ticker data and running exclusions..."):
    analysis_data = fetch_and_analyze_dividend_data(tickers)

# ==============================================================================
# 5. SCORECARD MATRIX DISPLAY
# ==============================================================================
if analysis_data:
    st.markdown("### 📊 Capital Allocation Scorecard")
    
    grid_data = []
    for ticker, data in analysis_data.items():
        # Mathematics of Pricing Power
        real_yield = data["yield"] + data["div_growth_cagr"] - inflation_rate
        
        # Determine Payout Display Label for Non-Enterprises (ETFs/Funds)
        if data["quote_type"] != "EQUITY":
            payout_display = f"N/A ({data['quote_type']})"
        elif data["payout_ratio"] == 999.0:
            payout_display = "Data Stalled"
        else:
            payout_display = f"{data['payout_ratio']:.2f}%"
            
        # Capital Safety Grading Logic
        if data["quote_type"] != "EQUITY":
            safety_status = "🔵 Passive Fund Pool"
        elif data["payout_ratio"] < 60.0 and data["beta"] < 1.0 and real_yield > 0:
            safety_status = "🟢 Nice & Boring (Safe)"
        elif data["payout_ratio"] > 85.0 or data["beta"] > 1.3:
            safety_status = "🔴 Value Trap (High Risk)"
        else:
            safety_status = "🟡 Moderate Allocation"
            
        grid_data.append({
            "Ticker": ticker,
            "Asset Classification": data["name"],
            "Current Yield": f"{data['yield']:.2f}%",
            "FCF Payout Ratio": payout_display,
            "5Y Payout Velocity": f"{data['div_growth_cagr']:.2f}%",
            "Beta Risk": f"{data['beta']:.2f}",
            "Inflation Spread": f"{real_yield:.2f}%",
            "Allocation Grade": safety_status
        })
        
    df_grid = pd.DataFrame(grid_data)
    st.dataframe(df_grid, use_container_width=True, hide_index=True)
    
    # ==============================================================================
    # 6. FUTURE PERFORMANCE PROJECTION VISUALIZATION
    # ==============================================================================
    st.markdown(f"### 🔮 Compounded Performance Projection Horizon ({projection_years} Years)")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        fig, ax = plt.subplots(figsize=(10, 5))
        
        # Calculate expected payout scaling over user-selected timeline
        future_years = list(range(0, projection_years + 1))
        
        for ticker, data in analysis_data.items():
            initial_yield = data["yield"]
            growth_rate = data["div_growth_cagr"] / 100.0
            
            # Base Case: Projecting Yield on Cost or Cumulative Growth Factor
            if initial_yield > 0:
                # Mathematical formula modeling nominal yield compounding out over time
                projected_values = [initial_yield * ((1 + growth_rate) ** y) for y in future_years]
                ax.plot(future_years, projected_values, marker='s', label=f"{ticker} (Yield on Cost)", linewidth=2)
                
        ax.set_title(f"Projected Future Nominal Yield on Cost Over {projection_years} Years")
        ax.set_xlabel("Years into the Future")
        ax.set_ylabel("Yield on Cost (%)")
