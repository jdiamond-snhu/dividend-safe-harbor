# 📈 Nice & Boring Dividend Screener

A robust, web-based financial intelligence tool built to filter out market noise and isolate high-quality, boring, cash-generative dividend stocks. This screener focuses strictly on fundamental financial health, payout sustainability, and historical consistency rather than speculative growth.

Deployed App: [https://dividend-safe-harbor-2vytivq2ayvzh6lq53cqi4.streamlit.app/]

---

## 🔎 The Philosophy

"Boring is beautiful." This tool is built for long-term income and dividend growth investors. It intentionally penalizes hyper-growth or highly volatile equities, instead optimizing for predictable corporate earnings, safe payout ratios, and a proven track record of consecutive annual dividend increases.

---

## 📊 Core Features & Screening Metrics

The application filters equities using a strict multi-point fundamental analysis checklist:

* **Dividend Sustainability:** Filters out companies with dangerously high payout ratios (e.g., capping trailing/forward payout ratios at 60-70% for standard equities).
* **Consistency Tracking:** Identifies companies with minimum consecutive years of dividend increases (e.g., 5+, 10+, or 25+ years for Dividend Aristocrats).
* **Balance Sheet Health:** Evaluates Debt-to-Equity ratios and interest coverage to ensure dividend safety during macroeconomic downturns.
* **Yield Optimization:** Filters out low-yield traps while flagging suspiciously high yields that may signal an impending dividend cut.
* **Instant Interactive Filtering:** Powered by Streamlit sliders and multi-select components for real-time portfolio screening.

---

## 🛠️ Tech Stack & Architecture

* **Language:** Python 3.10+
* **Web Interface & Deployment:** Streamlit (Streamlit Community Cloud)
* **Data Processing & Analytics:** Pandas / NumPy
* **Data Sources & APIs:** [yfinance]

---

## 🚀 Local Installation & Setup

Follow these steps to run the dividend screener locally on your machine.

### Prerequisites

Ensure you have Python 3.10 or higher installed.

### Installation Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com
   cd nice-boring-dividend-screener
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   # On macOS/Linux:
   source venv/bin/bin/activate
   # On Windows:
   .\venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Streamlit application:**
   ```bash
   streamlit run app.py
   ```

---

## 💡 Architecture & Scoring Framework

The screener processes data frames by calculating a custom **"Boring Stability Score"** based on the following weighted formula:

1. **Payout Ratio Score (40%):** Higher scores given to sustainable ratios between 35% and 60%.
2. **Dividend Growth History (30%):** Points scale up with consecutive years of growth.
3. **Free Cash Flow (FCF) Yield (30%):** Ensures the dividend is paid out of actual cash, not debt.

---

## 🗒 License

Distributed under the MIT License. See `LICENSE` for more information.

---

## 📌 Contact

Your Name - [https://www.linkedin.com/in/jeffry-diamond-radecki-63713b418]

Project Link: [https://github.com/jdiamond-snhu/dividend_safe_harbor]
