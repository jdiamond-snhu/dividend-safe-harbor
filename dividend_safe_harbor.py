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
    value="JNJ, VOO, GLD, PG, KO, XPAY, O",
)

# Strip whitespace and convert strings to clean uppercase lists
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
            
            # Fetch yfinance core metadata safely
            try:
                info = asset.info
                if info is None or not isinstance(info, dict):
                    info = {}
            except Exception:
                info = {}
                
            quote_type = info.get('quoteType', 'EQUITY').upper()
            company_name = info.get('longName', ticker)
            
            # FIXED: Universal raw conversion scaling to prevent 235% layout bugs
            raw_yield = info.get('dividendYield', 0.0)
            current_yield = float(raw_yield * 100) if raw_yield else 0.0
            
            beta = info.get('beta', 1.0) if info.get('beta') else 1.0

            # --- EXTRACT AND ANALYZE PAYOUT FREQUENCY (SCHEDULE) ---
            try:
                dividends_history = asset.dividends.loc[f"{start_year}-01-01":]
            except Exception:
                dividends_history = pd.Series(dtype=float)
            
            # Handle specialized asset scheduling parameters
            if not dividends_history.empty and len(dividends_history) >= 1:
                last_year_payouts = dividends_history.loc[dividends_history.index > (dividends_history.index[-1] - pd.Timedelta(days=365))]
                payout_frequency = len(last_year_payouts)
                
                if 10 <= payout_frequency <= 15:
                    schedule = "Monthly"
                elif 3 <= payout_frequency <= 5:
                    schedule = "Quarterly"
                elif 1 <= payout_frequency <= 2:
                    schedule = "Bi-Annually / Annually"
                elif payout_frequency > 15:
                    schedule = "Weekly / Variable"
                else:
                    schedule = "Irregular Schedule"
                
                # Resample historical distribution sequences safely
                try:
                    annual_divs = dividends_history.resample('YE').sum()
                    annual_divs = annual_divs[annual_divs.index.year < current_year]
                except Exception:
                    annual_divs = pd.Series(dtype=float)
            else:
                schedule = "N/A (No Payouts)"
                annual_divs = pd.Series(dtype=float)
            
            # FIXED: Explicit row coordinate targeting (.iloc[0]) to avoid structural Pandas exceptions
            if len(annual_divs) >= 2 and float(annual_divs.iloc[0]) > 0:
                try:
                    cagr = (float(annual_divs.iloc[-1]) / float(annual_divs.iloc[0])) ** (1 / (len(annual_divs) - 1)) - 1
                    div_growth_cagr = cagr * 100
                except Exception:
                    div_growth_cagr = info.get('dividendGrowthRate5Y', 0.0) * 100 if info.get('dividendGrowthRate5Y') else 0.0
            else:
                fallback_cagr = info.get('dividendGrowthRate5Y', 0.0)
                div_growth_cagr = float(fallback_cagr * 100) if fallback_cagr else 0.0
            
            # Build unified asset metrics package
            results[ticker] = {
                "name": company_name,
                "quote_type": quote_type,
                "yield": current_yield,
                "schedule": schedule,
                "div_growth_cagr": div_growth_cagr,
                "beta": beta
            }
        except Exception:
            # Shield loop processing from individual ticker failure points
            continue
            
    return results

# Initiate global data execution thread
with st.spinner("Processing deep global ticker data and running exclusions..."):
    analysis_data = fetch_and_analyze_dividend_data(tickers)

# ==============================================================================
# 5. SCORECARD MATRIX DISPLAY
# ==============================================================================
if analysis_data:
    st.markdown("### 📊 Capital Allocation Scorecard")
    
    grid_data = []
    for ticker, data in analysis_data.items():
        # Dynamic horizon compounding calculation logic
        cagr_decimal = data["div_growth_cagr"] / 100
        compounded_growth = ((1 + cagr_decimal) ** projection_years - 1) * 100
        
        real_yield_spread = data["yield"] + data["div_growth_cagr"] - inflation_rate
        
        # Structure defensive presentation labels based on asset metadata wrappers
        if data["quote_type"] != "EQUITY":
            safety_status = "🔵 Passive Fund Pool"
            schedule_display = "Quarterly (ETF Proxy)" if "ETF" in data["quote_type"] else data["schedule"]
        else:
            schedule_display = data["schedule"]
            if data["beta"] < 1.0 and real_yield_spread > 0:
                safety_status = "🟢 Nice & Boring (Safe)"
            elif data["beta"] > 1.3 or real_yield_spread < -2.0:
                safety_status = "🔴 Value Trap (High Risk)"
            else:
                safety_status = "🟡 Moderate Allocation"
          
        column_key = "Projected Payout Growth"
            
        grid_data.append({
            "Ticker": ticker,
            "Asset Classification": data["name"],
            "Current Dividend %": data["yield"],
            "Schedule": schedule_display,
            column_key: compounded_growth,
            "Beta Risk": f"{data['beta']:.2f}",
            "Allocation Grade": safety_status
        })
        
    df_grid = pd.DataFrame(grid_data)
    
    # Render interactive spreadsheet with custom percentage column parameters
    st.dataframe(
        df_grid, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Current Dividend %": st.column_config.NumberColumn(
                label="Current Dividend %",
                format="%.2f%%"
            ),
            "Projected Payout Growth": st.column_config.NumberColumn(
                label=f"Projected Payout Growth ({projection_years}Yr)",
                help="Estimated payout velocity assuming distributed dividends are systematically reinvested into purchasing more shares.",
                format="%.2f%%"
            )
        }
    )
    
    st.markdown(f"### 🔮 Compounded Performance Projection Horizon ({projection_years} Years)")
    st.info("💡 Pro Tip: Look for assets where strong historical growth velocity pairs with low beta risk to protect family wealth.")
else:
    st.error("The underlying execution engine could not find valid asset data. Correct ticker entry formatting.")
