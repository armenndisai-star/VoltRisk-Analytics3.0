import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io

# 1. PAGE CONFIG & DARK MODE ENFORCEMENT
st.set_page_config(page_title="VoltRisk Analytics", page_icon="⚡", layout="wide")

# Force Dark Mode Styling
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    [data-testid="stMetricValue"] { font-weight: 700 !important; color: #FFFFFF !important; }
    section[data-testid="stSidebar"] { background-color: #161B22 !important; border-right: 1px solid #30363D; }
    .signal-box { padding: 20px; border-radius: 10px; text-align: center; border: 1px solid #30363D; margin-bottom: 20px; }
    .beginner-card { background-color: #161B22; padding: 15px; border-radius: 10px; border-left: 5px solid #00FBFF; margin-bottom: 10px; min-height: 120px; }
    .pro-badge { background-color: #FFD700; color: black; padding: 2px 8px; border-radius: 5px; font-weight: bold; font-size: 12px; }
    </style>
    """, unsafe_allow_html=True)

# 2. SIDEBAR & SIMULATED SUBSCRIPTION
with st.sidebar:
    st.markdown("<h1 style='text-align: center; color: #00FFAA;'>⚡ VOLTRISK</h1>", unsafe_allow_html=True)
    st.markdown("---")
    
    # Fake Subscription Logic
    st.subheader("Subscription Status")
    license_key = st.text_input("Enter License Key", type="password", help="Project Demo Key: VOLT2026")
    
    if license_key == "VOLT2026":
        st.success("Pro Access Active! ✅")
        user_status = True
    else:
        st.info("Standard Mode (Limited)")
        user_status = False
        st.caption("Enter 'VOLT2026' to simulate Pro unlock.")

    st.markdown("---")
    ticker = st.text_input("Asset Ticker", value="NVDA").upper()
    investment = st.number_input("Capital Allocation ($)", min_value=10.0, value=1000.0)
    
    # Feature Gating
    max_sims = 10000 if user_status else 500
    iterations = st.slider("Number of Simulations", 100, max_sims, 500 if not user_status else 2000, step=100)
    
    time_horizon = st.slider("Days to Forecast", 1, 730, 252)
    apply_crash = st.checkbox("Simulate '2020 Covid crash'")
    
    start_sim = st.button("RUN SIMULATION", use_container_width=True)
    
    st.markdown("---")
    st.markdown("**⚙️ Engine Notes**\nVoltRisk uses GBM math to simulate potential futures based on 3-year history.")

# 3. MAIN DASHBOARD
st.title("⚡ :blue[Volt]Risk Analytics")

if start_sim:
    with st.spinner('Calculating Probability Maps...'):
        data = yf.download(ticker, start=(datetime.now() - timedelta(days=1095)), auto_adjust=False)
        spy_data = yf.download("SPY", start=(datetime.now() - timedelta(days=1095)), auto_adjust=False)
        
        if data.empty:
            st.error("Ticker not found. Please try another symbol.")
        else:
            # Flattening headers for modern yfinance compatibility
            if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
            if isinstance(spy_data.columns, pd.MultiIndex): spy_data.columns = spy_data.columns.get_level_values(0)

            # Core Simulation Engine
            def run_mc(df, inv, n):
                rets = df['Adj Close'].pct_change().dropna()
                mu, sigma, last = rets.mean(), rets.std(), df['Adj Close'].iloc[-1]
                daily = np.random.normal(mu, sigma, (time_horizon, n))
                paths = np.zeros_like(daily); paths[0] = last * (1 + daily[0])
                for t in range(1, time_horizon): paths[t] = paths[t-1] * (1 + daily[t])
                return (paths / last) * inv

            asset_paths = run_mc(data, investment, iterations)
            final_vals = asset_paths[-1]
            win_prob = (np.sum(final_vals > investment) / iterations) * 100
            tp_95, sl_5, mean_outcome = np.percentile(final_vals, 95), np.percentile(final_vals, 5), np.mean(final_vals)
            
            # Drawdown Math
            cum_max = np.maximum.accumulate(asset_paths, axis=0)
            avg_max_dd = np.mean(np.min((asset_paths - cum_max) / cum_max, axis=0)) * 100

            # 4. GAUGE & SIGNAL SECTION
            st.divider()
            c_gauge, c_signal = st.columns([1, 1])
            
            with c_gauge:
                fig_g = go.Figure(go.Indicator(
                    mode="gauge+number", value=win_prob, number={'suffix': "%", 'font': {'color': "#FFFFFF"}},
                    title={'text': "WIN PROBABILITY", 'font': {'size': 20}},
                    gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#1b5e20"},
                           'steps': [{'range': [0, 40], 'color': "#FF4B4B"},
                                     {'range': [40, 70], 'color': "#FFD700"},
                                     {'range': [70, 100], 'color': "#00FFAA"}]}))
                fig_g.update_layout(height=300, margin=dict(t=50, b=0), paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_g, use_container_width=True)

            with c_signal:
                st.markdown("<br><br>", unsafe_allow_html=True)
                if win_prob > 60:
                    st.markdown(f"<div class='signal-box' style='background-color: rgba(0, 255, 170, 0.1); border-color: #00FFAA;'><h2 style='color:#00FFAA;'>BUY SIGNAL</h2><p>The math suggests a high chance of profit.</p></div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='signal-box'><h2 style='color:#8B949E;'>WAIT</h2><p>Risk is currently too high for a safe entry.</p></div>", unsafe_allow_html=True)

            # 5. CORE METRICS
            st.divider()
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("CURRENT PRICE", f"${data['Adj Close'].iloc[-1]:,.2f}")
            m2.metric("EXPECTED ENDING", f"${mean_outcome:,.2f}")
            m3.metric("MAX DANGER (DIP)", f"{avg_max_dd:.1f}%")
            m4.metric("SAFETY FLOOR", f"${sl_5:,.2f}")

            # 6. PERFORMANCE CHART
            st.subheader("🔍 Market Benchmark & Volatility Bands")
            fig = go.Figure()
            days = list(range(time_horizon))
            
            # Show "Ghost Paths"
            for i in range(min(50, iterations)):
                fig.add_trace(go.Scatter(x=days, y=asset_paths[:, i], line=dict(color='rgba(0, 251, 255, 0.05)', width=1), hoverinfo='none', showlegend=False))
            
            # Gated Benchmark comparison
            if user_status:
                spy_paths = run_mc(spy_data, investment, 1000)
                fig.add_trace(go.Scatter(x=days, y=np.mean(spy_paths, axis=1), name="S&P 500 (Market)", line=dict(color='white', dash='dot')))
            
            fig.add_trace(go.Scatter(x=days, y=np.mean(asset_paths, axis=1), name="Your Asset (Projected)", line=dict(color='#FFD700', width=4)))
            
            p5, p95 = np.percentile(asset_paths, 5, axis=1), np.percentile(asset_paths, 95, axis=1)
            fig.add_trace(go.Scatter(x=days+days[::-1], y=list(p95)+list(p5)[::-1], fill='toself', fillcolor='rgba(0, 255, 170, 0.1)', line_color='rgba(0,0,0,0)', name='Confidence Zone'))
            
            if apply_crash:
                fig.add_hline(y=investment * 0.70, line_dash="dash", line_color="#FF4B4B", annotation_text="COVID-LEVEL DROP")

            fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=500, margin=dict(t=20))
            st.plotly_chart(fig, use_container_width=True)

            # 7. SIMPLIFIED STRATEGIC ANALYSIS
            st.divider()
            st.subheader("📊 How to Read Your Results")
            b1, b2, b3 = st.columns(3)
            with b1: 
                st.markdown("<div class='beginner-card'><b>1. Win Probability</b><br>This is the percentage of simulations where you made money. Experts look for 60% or higher.</div>", unsafe_allow_html=True)
            with b2: 
                st.markdown("<div class='beginner-card'><b>2. The 'Stomach Test'</b><br>Max Drawdown shows how big the dips might feel. If this number scares you, invest less capital.</div>", unsafe_allow_html=True)
            with b3: 
                st.markdown("<div class='beginner-card'><b>3. Beating the Market</b><br>Compare the Gold line to the White dashed line (Pro Only). It shows if this stock is actually better than a standard index fund.</div>", unsafe_allow_html=True)

            if user_status:
                st.success("✅ PRO FEATURE: Detailed Export Available.")
                report = io.BytesIO()
                pd.DataFrame({"Metric": ["Win Prob", "Mean Outcome", "Max Drawdown"], "Value": [win_prob, mean_outcome, avg_max_dd]}).to_excel(report)
                st.download_button("📩 DOWNLOAD PRO REPORT", data=report, file_name="VoltRisk_Pro_Report.xlsx")
            else:
                st.warning("🔒 Upgrade to Pro (Key: VOLT2026) to see Market Comparisons and Download Reports.")

else:
    st.info("👋 **Welcome to VoltRisk Analytics.** Enter a ticker and click 'Run Simulation'. Use 'VOLT2026' in the sidebar to simulate Pro Access.")