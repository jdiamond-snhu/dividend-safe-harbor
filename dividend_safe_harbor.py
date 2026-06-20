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
# 2. SIDEBAR CONTROL CONTROLS (INFLATION SHOCK SIMULATOR)
# ==============================================================================
st.sidebar.header("Macro Inflation Stress Test")
st.sidebar.markdown(
    "Simulate structural pricing power against high inflation environments "
    "(e.g., the Reagan-Volcker era)."
)

# Reagan-Volcker slider: 0% to 13%+ with a default of 2.5%
inflation_rate = st.sidebar.slider(
    label="Simulated Annual Inflation Rate (%)",
    min_value=0.0,
    max_value=15.0,
    value=2.5,
    step=0.1,
    help="Default is 2.5%. Push past 13% to simulate the 1979-1981 Volcker tightening cycle.",
)

# ==============================================================================
# 3. TICKER INPUT & VALIDATION (1 MIN, 10 MAX)
# ==============================================================================
st.markdown("### 🔍 Enterprise Search Pipeline")
ticker_input = st.text_input(
    label="Enter Ticker Symbols (separated by commas):",
    value="PG, JNJ, KO, O",
    help="Minimum: 1 ticker. Maximum: 10 tickers.",
)

# Clean, split, and limit tickers
tickers = [t.strip().upper() for t in ticker_input.split(",") if t.strip()]

if len(tickers) == 0:
    st.error("❌ Action Required: Please enter at least one ticker symbol.")
    st.stop()
elif len(tickers) > 10:
    st.warning("⚠️ Optimization Limit: Truncating list to the first 10 tickers max.")
    tickers = tickers[:10]

# ==============================================================================
# 4. DATA PROCESSING & METRIC CALCULATION ENGINE
# ==============================================================================
@st.cache_data(ttl=3600)
def fetch_and_analyze_dividend_data(ticker_list, start_year=2018):
    results = {}
    
    for ticker in ticker_list:
        try:
            asset = yf.Ticker(ticker)
            info = asset.info
            
            # Fetch historical financials and cash flows
            cashflow = asset.cashflow
            financials = asset.financials
            history = asset.history(start=f"{start_year}-01-01")
            
            if cashflow.empty or financials.empty or history.empty:
                continue
                
            # Transpose dataframes to have years as rows for easier analysis
            cf_t = cashflow.T
            fin_t = financials.T
            
            # Align indices to ensure year-by-year matches
            available_years = cf_t.index.intersection(fin_t.index)
            cf_t = cf_t.loc[available_years]
            fin_t = fin_t.loc[available_years]
            
            # 1. Calculate Free Cash Flow (Operating Cash Flow - Capital Expenditures)
            # Use fallback names commonly found in yfinance structures
            ocf_col = 'Operating Cash Flow' if 'Operating Cash Flow' in cf_t.columns else cf_t.columns[0]
            capex_col = 'Capital Expenditures' if 'Capital Expenditures' in cf_t.columns else None
            
            if capex_col:
                # Capex is usually negative in yfinance, use absolute addition/subtraction safely
                fcf_series = cf_t[ocf_col] + cf_t[capex_col]
            else:
                # Alternative fallback if Capex row is named differently
                capex_alt = [c for c in cf_t.columns if 'Capital' in str(c) or 'Invest' in str(c)]
                if capex_alt:
                    fcf_series = cf_t[ocf_col] + cf_t[capex_alt[0]]
                else:
                    fcf_series = cf_t[ocf_col] * 0.8 # Conservative fallback proxy
                    
            # 2. Extract Cash Dividends Paid
            div_col = [c for c in cf_t.columns if 'Dividend' in str(c)]
            div_series = cf_t[div_col[0]].abs() if div_col else pd.Series(0, index=available_years)
            
            # 3. Calculate FCF Dividend Payout Ratio for the most recent year
            most_recent_year = available_years[0] # yfinance historical indices typically descend
            recent_fcf = fcf_series.iloc[0]
            recent_div_paid = div_series.iloc[0]
            
            fcf_payout_ratio = (recent_div_paid / recent_fcf) if recent_fcf > 0 else 999.0
            
            # 4. Calculate 5-Year Dividend Growth Velocity
            dividends_history = asset.dividends.loc[f"{start_year}-01-01":]
            annual_divs = dividends_history.resample('YE').sum()
            
            if len(annual_divs) >= 2:
                cagr = (annual_divs.iloc[-1] / annual_divs.iloc[0]) ** (1 / (len(annual_divs) - 1)) - 1
            else:
                cagr = info.get('dividendGrowthRate5Y', 0.0) if info.get('dividendGrowthRate5Y') else 0.0
                
            # 5. Extract Core Profiling Metrics
            current_yield = info.get('dividendYield', 0.0) * 100 if info.get('dividendYield') else 0.0
            beta = info.get('beta', 1.0)
            company_name = info.get('longName', ticker)
            
            results[ticker] = {
                "name": company_name,
                "yield": current_yield,
                "payout_ratio": fcf_payout_ratio * 100,
                "div_growth_cagr": cagr * 100,
                "beta": beta,
                "annual_div_history": annual_divs
            }
        except Exception as e:
            st.error(f"Error parsing data for {ticker}: {str(e)}")
            
    return results

# Trigger data fetch pipeline
with st.spinner("Executing financial pipeline and parsing SEC data..."):
    analysis_data = fetch_and_analyze_dividend_data(tickers)

# ==============================================================================
# 5. ANALYSIS DISPLAY & THE "BORING" METRIC ASSESSMENT
# ==============================================================================
if analysis_data:
    st.markdown("### 📊 Capital Allocation Scorecard")
    
    # Generate table grid rows
    grid_data = []
    for ticker, data in analysis_data.items():
        # Evaluate spread against inflation (Pricing Power Test)
        real_yield = data["yield"] + data["div_growth_cagr"] - inflation_rate
        
        # Grading capital safety
        if data["payout_ratio"] < 60.0 and data["beta"] < 1.0 and real_yield > 0:
            safety_status = "🟢 Nice & Boring (Safe)"
        elif data["payout_ratio"] > 85.0 or data["beta"] > 1.3:
            safety_status = "🔴 Value Trap (High Risk)"
        else:
            safety_status = "🟡 Moderate Allocation"
            
        grid_data.append({
            "Ticker": ticker,
            "Company Name": data["name"],
            "Div Yield (%)": f"{data['yield']:.2f}%",
            "FCF Payout Ratio (%)": f"{data['payout_ratio']:.2f}%" if data['payout_ratio'] != 99900.0 else "No Cash Flow",
            "5Y Div Growth Velocity": f"{data['div_growth_cagr']:.2f}%",
            "Beta Volatility": f"{data['beta']:.2f}",
            "Real Return Spread": f"{real_yield:.2f}%",
            "Allocation Grade": safety_status
        })
        
    df_grid = pd.DataFrame(grid_data)
    st.dataframe(df_grid, use_container_width=True, hide_index=True)
    
    # Visualizations: Historic Growth Trends
    st.markdown("### 📈 Dividend Growth Vector (Pre-Pandemic Baseline to Present)")
    col1, col2 = st.columns(2)
    
    with col1:
        fig, ax = plt.subplots(figsize=(10, 5))
        for ticker, data in analysis_data.items():
            hist = data["annual_div_history"]
            if not hist.empty:
                ax.plot(hist.index.year, hist.values, marker='o', label=ticker, linewidth=2)
        ax.set_title("Absolute Annual Dividend Payout Trend ($ per share)")
        ax.set_xlabel("Calendar Year")
        ax.set_ylabel("Annualized Payout")
        ax.grid(True, linestyle="--", alpha=0.5)
        ax.legend()
        st.pyplot(fig)
        
    with col2:
        st.markdown("#### 💡 Structural Allocation Insights")
        st.markdown(
            "An elite capital allocator looks for companies where the **5Y Div Growth Velocity** "
            "consistently outpaces your **Simulated Inflation Rate** slider. If a company has a low growth "
            "rate and high payout ratio during macro spikes, inflation will quietly bleed the value "
            "of that dividend distribution to zero."
        )
        st.markdown(
            "**The 'Nice & Boring' Framework Checklist:**\n"
            "- **FCF Payout Ratio < 60%**: Guarantees a fortress balance sheet.\n"
            "- **Beta < 1.0**: Shields friends and family from broad market panic attacks.\n"
            "- **Positive Real Return Spread**: Ensures purchasing power expansion."
        )
else:
    st.error("No valid financial data could be mapped for the selected tickers. Verify the symbols.")
