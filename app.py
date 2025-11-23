import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import database as db
import ai_predictor as ai
import requests

# Page Config
st.set_page_config(
    page_title="StockMinds Desktop",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize DB
try:
    db.init_db()
except Exception as e:
    st.error(f"Database Connection Failed: {e}")

# --- Helper Functions ---
@st.cache_data(ttl=300)
def search_yahoo(query):
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search"
        params = {"q": query, "quotesCount": 10, "newsCount": 0}
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, params=params, headers=headers)
        data = response.json()
        
        results = []
        if 'quotes' in data:
            for q in data['quotes']:
                if 'symbol' in q and 'shortname' in q:
                    results.append({
                        "symbol": q['symbol'],
                        "name": q['shortname'],
                        "exch": q.get('exchange', 'N/A')
                    })
        return results
    except Exception as e:
        st.error(f"Search Error: {e}")
        return []

@st.cache_data(ttl=60)
def get_stock_data(symbol):
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period="1d")
        if not hist.empty:
            price = hist['Close'].iloc[-1]
            hist_5d = stock.history(period="5d")
            if len(hist_5d) >= 2:
                prev_close = hist_5d['Close'].iloc[-2]
                change = price - prev_close
                change_pct = (change / prev_close) * 100
            else:
                change = 0
                change_pct = 0
                
            return {
                'symbol': symbol,
                'name': symbol,
                'price': price,
                'change': change,
                'change_pct': change_pct
            }
        return None
    except Exception as e:
        return None

@st.cache_data(ttl=60)
def get_timeframe_pl(symbol, timeframe):
    """Calculate P/L for a specific timeframe using exact date calculations"""
    try:
        from datetime import datetime, timedelta
        
        # Map timeframe to exact days
        days_map = {
            "1D": 1,
            "5D": 5,
            "1M": 30,
            "3M": 90,
            "6M": 180,
            "1Y": 365,
            "5Y": 365 * 5,
            "Max": None  # Special case
        }
        
        days = days_map.get(timeframe)
        stock = yf.Ticker(symbol)
        
        if days is None:  # Max period
            hist = stock.history(period='max')
            if len(hist) >= 2:
                start_price = hist['Close'].iloc[0]
                current_price = hist['Close'].iloc[-1]
                start_date = hist.index[0]
        else:
            # Fetch enough data to ensure we have the exact date
            # Use 2x the period to be safe, or 2y for long periods
            if days <= 180:
                fetch_period = f"{days * 2}d"
            else:
                fetch_period = "2y"
            
            hist = stock.history(period=fetch_period)
            
            if len(hist) < 2:
                return None
            
            # Calculate target date (exactly N days ago)
            target_date = datetime.now() - timedelta(days=days)
            
            # Find closest trading day to target date
            closest_date = None
            min_diff = timedelta(days=999)
            
            for date in hist.index:
                date_naive = date.to_pydatetime().replace(tzinfo=None)
                diff = abs(date_naive - target_date)
                if diff < min_diff:
                    min_diff = diff
                    closest_date = date
            
            if closest_date is None:
                return None
            
            # Validation: Check if we found a date within reasonable range (7 days)
            date_diff_days = min_diff.days
            if date_diff_days > 7:
                # Data quality issue - date is too far from target
                return None
            
            start_price = hist.loc[closest_date, 'Close']
            current_price = hist['Close'].iloc[-1]
            start_date = closest_date
        
        # Calculate P/L
        price_change = current_price - start_price
        pct_change = (price_change / start_price) * 100
        
        return {
            'start_price': start_price,
            'current_price': current_price,
            'change': price_change,
            'change_pct': pct_change,
            'period': timeframe,
            'start_date': start_date,
            'data_quality': 'verified'
        }
    except Exception as e:
        return None

def get_market_indices():
    indices = {
        'NIFTY 50': '^NSEI',
        'SENSEX': '^BSESN',
        'BANK NIFTY': '^NSEBANK'
    }
    data = []
    for name, symbol in indices.items():
        info = get_stock_data(symbol)
        if info:
            info['name'] = name
            data.append(info)
    return data

def display_ai_insight(p):
    """Reusable function to display AI prediction details"""
    sig_color = "green" if "BUY" in p['signal'] else "red" if "SELL" in p['signal'] else "gray"
    st.markdown(f"### :{sig_color}[{p['signal']}] (Confidence: {p['confidence']:.1f}%)")
    
    with st.expander("🔍 Analysis & News", expanded=True):
        st.write(p['reason'])
        
        if 'metrics' in p:
            m = p['metrics']
            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("RSI", f"{m['RSI']:.1f}")
            mc2.metric("MACD", f"{m['MACD']:.2f}")
            mc3.metric("200 SMA", f"{m['SMA_200']:.2f}")
            mc4.metric("Close", f"₹{m['Close']:,.2f}")
            
        if 'news' in p and p['news']:
            st.markdown("---")
            st.subheader("📰 Recent News")
            for n in p['news']:
                st.markdown(f"- [{n['title']}]({n['link']})")

# --- UI Components ---

@st.fragment(run_every=10)
def render_market_indices_fragment():
    """Auto-refreshing market indices only - updates every 10 seconds without affecting other content"""
    indices = get_market_indices()
    
    cols = st.columns(len(indices))
    for i, index in enumerate(indices):
        with cols[i]:
            st.metric(
                label=index['name'],
                value=f"₹{index['price']:,.2f}",
                delta=f"{index['change_pct']:.2f}%"
            )

def render_dashboard():
    st.title("📊 Market Dashboard")
    st.caption(f"💹 Live market data updates every 10 seconds")

    # Auto-refreshing market indices in isolated fragment
    render_market_indices_fragment()

    st.markdown("---")
    
    # Stock Search Section - This section is static and won't re-render
    render_stock_search_section()

@st.fragment(run_every=10)
def render_market_indices_fragment():
    """Auto-refreshing market indices only - updates every 10 seconds without affecting other content"""
    indices = get_market_indices()
    
    cols = st.columns(len(indices))
    for i, index in enumerate(indices):
        with cols[i]:
            st.metric(
                label=index['name'],
                value=f"₹{index['price']:,.2f}",
                delta=f"{index['change_pct']:.2f}%"
            )

def render_stock_search_section():
    """Static stock search section that doesn't re-render"""
    st.subheader("🔍 Search Stock")
    
    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
    with c1:
        search_query = st.text_input("Search for any stock", placeholder="e.g. Reliance, TCS, INFY", key="dashboard_search")
    
    # Search Logic
    if "dashboard_search_res" not in st.session_state:
        st.session_state["dashboard_search_res"] = {}
        
    if search_query and search_query != st.session_state.get("last_dashboard_search", ""):
        results = search_yahoo(search_query)
        if results:
            st.session_state["dashboard_search_res"] = {f"{r['symbol']} - {r['name']}": r['symbol'] for r in results}
        else:
            st.session_state["dashboard_search_res"] = {}
        st.session_state["last_dashboard_search"] = search_query
    elif not search_query:
        st.session_state["dashboard_search_res"] = {}
    
    selected_symbol = None
    if st.session_state["dashboard_search_res"]:
        lbl = st.selectbox("Select Stock", options=list(st.session_state["dashboard_search_res"].keys()), key="dashboard_sel")
        if lbl:
            selected_symbol = st.session_state["dashboard_search_res"][lbl]
    
    with c2:
        if st.button("🔍 Analyze", key="dashboard_analyze", type="primary"):
            if selected_symbol:
                st.session_state["dashboard_selected_stock"] = selected_symbol
    
    # Display Stock Details
    if "dashboard_selected_stock" in st.session_state and st.session_state["dashboard_selected_stock"]:
        stock_symbol = st.session_state["dashboard_selected_stock"]
        
        st.markdown("---")
        st.subheader(f"📈 {stock_symbol} - Complete Analysis")
        
        # Fetch stock data
        stock_data = get_stock_data(stock_symbol)
        
        if stock_data:
            # ========================================
            # SECTION 1: CHART WITH TIMEFRAME SELECTOR (FIRST - MOST IMPORTANT)
            # ========================================
            
            # Get additional data from yfinance for chart
            try:
                stock = yf.Ticker(stock_symbol)
                
                
                # Interactive Chart Section
                st.markdown("---")
                st.markdown("**📈 Select Timeframe**")
                
                # Map timeframe to intervals (kept for compatibility)
                tv_config_map = {
                    "1D": {"interval": "5", "range": "1D"},
                    "5D": {"interval": "30", "range": "5D"}, 
                    "1M": {"interval": "D", "range": "1M"},
                    "3M": {"interval": "D", "range": "3M"},
                    "6M": {"interval": "D", "range": "6M"},
                    "1Y": {"interval": "W", "range": "12M"},
                    "5Y": {"interval": "W", "range": "60M"},
                    "Max": {"interval": "M", "range": "ALL"}
                }
                
                # Initialize selected timeframe in session state
                if f"selected_tf_{stock_symbol}" not in st.session_state:
                    st.session_state[f"selected_tf_{stock_symbol}"] = "1M"
                
                # Timeframe selector buttons
                st.markdown("**Select Timeframe:**")
                tf_col1, tf_col2, tf_col3, tf_col4, tf_col5, tf_col6, tf_col7, tf_col8 = st.columns(8)
                
                with tf_col1:
                    if st.button("1D", key=f"tf_1d_{stock_symbol}",
                                type="primary" if st.session_state[f"selected_tf_{stock_symbol}"] == "1D" else "secondary",
                                use_container_width=True):
                        st.session_state[f"selected_tf_{stock_symbol}"] = "1D"
                        st.rerun()
                
                with tf_col2:
                    if st.button("5D", key=f"tf_5d_{stock_symbol}",
                                type="primary" if st.session_state[f"selected_tf_{stock_symbol}"] == "5D" else "secondary",
                                use_container_width=True):
                        st.session_state[f"selected_tf_{stock_symbol}"] = "5D"
                        st.rerun()
                
                with tf_col3:
                    if st.button("1M", key=f"tf_1m_{stock_symbol}",
                                type="primary" if st.session_state[f"selected_tf_{stock_symbol}"] == "1M" else "secondary",
                                use_container_width=True):
                        st.session_state[f"selected_tf_{stock_symbol}"] = "1M"
                        st.rerun()
                
                with tf_col4:
                    if st.button("3M", key=f"tf_3m_{stock_symbol}",
                                type="primary" if st.session_state[f"selected_tf_{stock_symbol}"] == "3M" else "secondary",
                                use_container_width=True):
                        st.session_state[f"selected_tf_{stock_symbol}"] = "3M"
                        st.rerun()
                
                with tf_col5:
                    if st.button("6M", key=f"tf_6m_{stock_symbol}",
                                type="primary" if st.session_state[f"selected_tf_{stock_symbol}"] == "6M" else "secondary",
                                use_container_width=True):
                        st.session_state[f"selected_tf_{stock_symbol}"] = "6M"
                        st.rerun()
                
                with tf_col6:
                    if st.button("1Y", key=f"tf_1y_{stock_symbol}",
                                type="primary" if st.session_state[f"selected_tf_{stock_symbol}"] == "1Y" else "secondary",
                                use_container_width=True):
                        st.session_state[f"selected_tf_{stock_symbol}"] = "1Y"
                        st.rerun()
                
                with tf_col7:
                    if st.button("5Y", key=f"tf_5y_{stock_symbol}",
                                type="primary" if st.session_state[f"selected_tf_{stock_symbol}"] == "5Y" else "secondary",
                                use_container_width=True):
                        st.session_state[f"selected_tf_{stock_symbol}"] = "5Y"
                        st.rerun()
                
                with tf_col8:
                    if st.button("Max", key=f"tf_max_{stock_symbol}",
                                type="primary" if st.session_state[f"selected_tf_{stock_symbol}"] == "Max" else "secondary",
                                use_container_width=True):
                        st.session_state[f"selected_tf_{stock_symbol}"] = "Max"
                        st.rerun()
                
                selected_tf = st.session_state[f"selected_tf_{stock_symbol}"]
                tv_config = tv_config_map[selected_tf]
                
                # Calculate and display P/L for selected timeframe
                pl_data = get_timeframe_pl(stock_symbol, selected_tf)
                
                if pl_data:
                    st.markdown("---")
                    st.markdown(f"**📊 Performance for {selected_tf} Period**")
                    
                    # Show start date for transparency
                    if 'start_date' in pl_data:
                        from datetime import datetime
                        start_date_str = pl_data['start_date'].strftime('%Y-%m-%d')
                        end_date_str = datetime.now().strftime('%Y-%m-%d')
                        st.caption(f"Period: {start_date_str} to {end_date_str}")
                    
                    pl_col1, pl_col2, pl_col3 = st.columns(3)
                    
                    with pl_col1:
                        st.metric(
                            label="Start Price",
                            value=f"₹{pl_data['start_price']:,.2f}"
                        )
                    
                    with pl_col2:
                        st.metric(
                            label="Current Price",
                            value=f"₹{pl_data['current_price']:,.2f}"
                        )
                    
                    with pl_col3:
                        st.metric(
                            label=f"{selected_tf} P/L",
                            value=f"₹{pl_data['change']:,.2f}",
                            delta=f"{pl_data['change_pct']:.2f}%"
                        )
                    
                    # Data quality indicator
                    if pl_data.get('data_quality') == 'verified':
                        st.caption("✅ Data verified with exact date calculation")
                else:
                    st.warning("⚠️ Unable to calculate P/L - insufficient historical data")
                
                st.markdown("")  # Spacing
                
                # Create interactive candlestick chart using Plotly
                st.markdown("---")
                st.markdown("**📈 Interactive Price Chart**")
                
                # Fetch historical data based on selected timeframe
                period_map = {
                    "1D": "1d",
                    "5D": "5d",
                    "1M": "1mo",
                    "3M": "3mo",
                    "6M": "6mo",
                    "1Y": "1y",
                    "5Y": "5y",
                    "Max": "max"
                }
                
                chart_period = period_map[selected_tf]
                
                try:
                    # Fetch data
                    stock = yf.Ticker(stock_symbol)
                    chart_data = stock.history(period=chart_period)
                    
                    if not chart_data.empty:
                        # Create candlestick chart
                        fig = go.Figure(data=[go.Candlestick(
                            x=chart_data.index,
                            open=chart_data['Open'],
                            high=chart_data['High'],
                            low=chart_data['Low'],
                            close=chart_data['Close'],
                            name=stock_symbol
                        )])
                        
                        # Add moving average
                        if len(chart_data) >= 20:
                            ma20 = chart_data['Close'].rolling(window=20).mean()
                            fig.add_trace(go.Scatter(
                                x=chart_data.index,
                                y=ma20,
                                mode='lines',
                                name='MA20',
                                line=dict(color='orange', width=1)
                            ))
                        
                        # Update layout
                        fig.update_layout(
                            title=f"{stock_symbol} - {selected_tf} Chart",
                            yaxis_title="Price (₹)",
                            xaxis_title="Date",
                            template="plotly_dark",
                            height=600,
                            xaxis_rangeslider_visible=False,
                            hovermode='x unified',
                            showlegend=True,
                            legend=dict(
                                yanchor="top",
                                y=0.99,
                                xanchor="left",
                                x=0.01
                            )
                        )
                        
                        # Display chart
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Point-to-Point P/L Calculator
                        st.markdown("---")
                        st.markdown("**📊 Point-to-Point P/L Calculator**")
                        st.caption("Select any two dates to calculate P/L between them")
                        
                        # Create date options
                        available_dates = chart_data.index.tolist()
                        date_options = [d.strftime('%Y-%m-%d') for d in available_dates]
                        
                        p2p_col1, p2p_col2 = st.columns(2)
                        
                        with p2p_col1:
                            start_date_str = st.selectbox(
                                "Start Date",
                                options=date_options,
                                index=0,
                                key=f"p2p_start_{stock_symbol}_{selected_tf}"
                            )
                        
                        with p2p_col2:
                            end_date_str = st.selectbox(
                                "End Date",
                                options=date_options,
                                index=len(date_options)-1,
                                key=f"p2p_end_{stock_symbol}_{selected_tf}"
                            )
                        
                        # Calculate P/L between selected dates
                        try:
                            # Find the selected dates in the data
                            start_idx = date_options.index(start_date_str)
                            end_idx = date_options.index(end_date_str)
                            
                            start_date = available_dates[start_idx]
                            end_date = available_dates[end_idx]
                            
                            start_price = chart_data.loc[start_date, 'Close']
                            end_price = chart_data.loc[end_date, 'Close']
                            
                            p2p_change = end_price - start_price
                            p2p_pct = (p2p_change / start_price) * 100
                            
                            # Display results
                            p2p_res_col1, p2p_res_col2, p2p_res_col3 = st.columns(3)
                            
                            with p2p_res_col1:
                                st.metric(
                                    label=f"Price on {start_date_str}",
                                    value=f"₹{start_price:,.2f}"
                                )
                            
                            with p2p_res_col2:
                                st.metric(
                                    label=f"Price on {end_date_str}",
                                    value=f"₹{end_price:,.2f}"
                                )
                            
                            with p2p_res_col3:
                                st.metric(
                                    label="Point-to-Point P/L",
                                    value=f"₹{p2p_change:,.2f}",
                                    delta=f"{p2p_pct:.2f}%"
                                )
                            
                            # Show number of days
                            days_diff = (end_date - start_date).days
                            st.caption(f"Period: {days_diff} days | {start_date_str} to {end_date_str}")
                            
                        except Exception as e:
                            st.error(f"Error calculating P/L: {str(e)}")
                        
                    else:
                        st.warning("Unable to load chart data for this timeframe")
                        
                except Exception as e:
                    st.error(f"Error loading chart: {str(e)}")
                
                # ========================================
                # SECTION 2: STOCK DETAILS (SECOND)
                # ========================================
                
                st.markdown("---")
                st.markdown("### 📊 Stock Details")
                
                # Price Information
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Current Price", f"₹{stock_data['price']:,.2f}")
                col2.metric("Change", f"₹{stock_data['change']:,.2f}", f"{stock_data['change_pct']:+.2f}%")
                
                # Get info for additional metrics
                info = stock.info
                
                # Market Cap and Volume
                if 'marketCap' in info:
                    col3.metric("Market Cap", f"₹{info['marketCap']/10000000:,.2f} Cr")
                if 'volume' in info:
                    col4.metric("Volume", f"{info['volume']:,}")
                
                # More details in expandable section
                with st.expander("📈 Detailed Stock Information", expanded=False):
                    detail_col1, detail_col2, detail_col3 = st.columns(3)
                    
                    with detail_col1:
                        st.markdown("**Trading Info**")
                        if 'open' in info:
                            st.write(f"Open: ₹{info['open']:,.2f}")
                        if 'dayHigh' in info:
                            st.write(f"Day High: ₹{info['dayHigh']:,.2f}")
                        if 'dayLow' in info:
                            st.write(f"Day Low: ₹{info['dayLow']:,.2f}")
                        if 'previousClose' in info:
                            st.write(f"Prev Close: ₹{info['previousClose']:,.2f}")
                    
                    with detail_col2:
                        st.markdown("**52 Week Range**")
                        if 'fiftyTwoWeekHigh' in info:
                            st.write(f"52W High: ₹{info['fiftyTwoWeekHigh']:,.2f}")
                        if 'fiftyTwoWeekLow' in info:
                            st.write(f"52W Low: ₹{info['fiftyTwoWeekLow']:,.2f}")
                        if 'fiftyDayAverage' in info:
                            st.write(f"50 Day Avg: ₹{info['fiftyDayAverage']:,.2f}")
                        if 'twoHundredDayAverage' in info:
                            st.write(f"200 Day Avg: ₹{info['twoHundredDayAverage']:,.2f}")
                    
                    with detail_col3:
                        st.markdown("**Fundamentals**")
                        if 'trailingPE' in info and info['trailingPE']:
                            st.write(f"P/E Ratio: {info['trailingPE']:.2f}")
                        if 'priceToBook' in info and info['priceToBook']:
                            st.write(f"P/B Ratio: {info['priceToBook']:.2f}")
                        if 'dividendYield' in info and info['dividendYield']:
                            st.write(f"Dividend Yield: {info['dividendYield']*100:.2f}%")
                        if 'beta' in info and info['beta']:
                            st.write(f"Beta: {info['beta']:.2f}")
                
                # ========================================
                # SECTION 3: QUICK ACTIONS (LAST)
                # ========================================
                
                st.markdown("---")
                st.markdown("### ⚡ Quick Actions")
                qa_c1, qa_c2 = st.columns(2)
                
                with qa_c1:
                    st.markdown("**Add to Watchlist**")
                    watchlists = db.get_watchlists(st.session_state.user_id)
                    if watchlists:
                        wl_names = {w['name']: w['id'] for w in watchlists}
                        selected_wl = st.selectbox("Select Watchlist", options=list(wl_names.keys()), key="qa_wl_sel")
                        if st.button("➕ Add to Watchlist", key="qa_add_wl"):
                            if db.add_to_watchlist(wl_names[selected_wl], stock_symbol):
                                st.success(f"Added {stock_symbol} to {selected_wl}!")
                            else:
                                st.error("Could not add (maybe duplicate?)")
                    else:
                        st.info("No watchlists found. Create one in Watchlist tab.")

                with qa_c2:
                    st.markdown("**Add to Portfolio**")
                    portfolios = db.get_portfolios(st.session_state.user_id)
                    if portfolios:
                        pf_names = {p['name']: p['id'] for p in portfolios}
                        selected_pf = st.selectbox("Select Portfolio", options=list(pf_names.keys()), key="qa_pf_sel")
                        
                        c_qty, c_price = st.columns(2)
                        with c_qty:
                            q_qty = st.number_input("Qty", min_value=1, value=1, key="qa_qty")
                        with c_price:
                            q_price = st.number_input("Price", min_value=0.0, value=float(stock_data['price']), key="qa_price")
                        
                        if st.button("💰 Buy / Add", key="qa_add_pf"):
                            pf_id = pf_names[selected_pf]
                            # Add transaction
                            db.add_transaction(pf_id, stock_symbol, "BUY", q_qty, q_price, datetime.now())
                            
                            # Update holdings with weighted average
                            holdings = db.get_portfolio_holdings(pf_id)
                            current_holding = next((h for h in holdings if h['symbol'] == stock_symbol), None)
                            
                            if current_holding:
                                new_qty = current_holding['quantity'] + q_qty
                                total_cost = (float(current_holding['quantity']) * float(current_holding['avg_price'])) + (q_qty * q_price)
                                new_avg = total_cost / new_qty
                            else:
                                new_qty = q_qty
                                new_avg = q_price
                                
                            db.update_portfolio_holding(pf_id, stock_symbol, new_qty, new_avg)
                            st.success(f"Bought {q_qty} {stock_symbol} in {selected_pf}!")
                    else:
                        st.info("No portfolios found. Create one in Portfolio tab.")
                
                # AI Insight Section
                st.markdown("---")
                st.subheader("🤖 AI-Powered Insight")
                
                if st.button("Generate AI Analysis", key=f"ai_dashboard_{stock_symbol}", type="primary"):
                    with st.spinner("Analyzing stock with AI..."):
                        pred = ai.predict_signal(stock_symbol)
                        st.session_state[f"dashboard_pred_{stock_symbol}"] = pred
                
                # Display AI prediction if available
                if f"dashboard_pred_{stock_symbol}" in st.session_state:
                    display_ai_insight(st.session_state[f"dashboard_pred_{stock_symbol}"])
            except Exception as e:
                st.warning(f"Could not fetch detailed information: {e}")
        else:
            st.error("Could not fetch stock data. Please try another symbol.")
    
    st.markdown("---")
    st.subheader("📈 Market Trends")
    
    st.markdown("---")
    render_nifty_dashboard()

def render_nifty_dashboard():
    st.subheader("Market Summary > NIFTY 50")
    
    # Initialize session state for timeframe
    if 'nifty_timeframe' not in st.session_state:
        st.session_state.nifty_timeframe = '1D'
        
    # Timeframe mapping
    tf_map = {
        '1D': {'period': '1d', 'interval': '5m'},
        '5D': {'period': '5d', 'interval': '15m'},
        '1M': {'period': '1mo', 'interval': '1d'},
        '6M': {'period': '6mo', 'interval': '1d'},
        'YTD': {'period': 'ytd', 'interval': '1d'},
        '1Y': {'period': '1y', 'interval': '1d'},
        '5Y': {'period': '5y', 'interval': '1wk'},
        'Max': {'period': 'max', 'interval': '1mo'}
    }
    
    # Fetch Data
    nifty = yf.Ticker("^NSEI")
    tf = st.session_state.nifty_timeframe
    params = tf_map[tf]
    hist = nifty.history(period=params['period'], interval=params['interval'])
    
    if hist.empty:
        st.error("No data available for NIFTY 50")
        return

    # Current Metrics
    current_price = hist['Close'].iloc[-1]
    prev_close = nifty.info.get('previousClose', hist['Close'].iloc[0])
    
    # Calculate change based on timeframe
    if tf == '1D':
        base_price = prev_close
    else:
        base_price = hist['Close'].iloc[0]
        
    change = current_price - base_price
    change_pct = (change / base_price) * 100
    
    color = "green" if change >= 0 else "red"
    sign = "+" if change >= 0 else ""
    
    # Header Metrics
    st.markdown(f"""
    <div style="margin-bottom: 20px;">
        <span style="font-size: 3rem; font-weight: bold;">{current_price:,.2f}</span>
        <span style="font-size: 1.5rem; color: {color}; margin-left: 10px;">
            {sign}{change:,.2f} ({sign}{change_pct:.2f}%)
        </span>
    </div>
    """, unsafe_allow_html=True)
    
    # Timeframe Selector
    cols = st.columns(len(tf_map))
    for i, (label, _) in enumerate(tf_map.items()):
        with cols[i]:
            if st.button(label, key=f"nifty_tf_{label}", 
                        type="primary" if st.session_state.nifty_timeframe == label else "secondary",
                        use_container_width=True):
                st.session_state.nifty_timeframe = label
                st.rerun()
                
    # Chart
    fig = go.Figure()
    
    # Area Chart
    fig.add_trace(go.Scatter(
        x=hist.index, 
        y=hist['Close'],
        mode='lines',
        fill='tozeroy',
        line=dict(color='#34a853' if change >= 0 else '#ea4335', width=2),
        name='NIFTY 50'
    ))
    
    # Previous Close Line (only relevant for shorter timeframes or as reference)
    if tf in ['1D', '5D']:
        fig.add_trace(go.Scatter(
            x=[hist.index[0], hist.index[-1]],
            y=[prev_close, prev_close],
            mode='lines',
            line=dict(color='gray', width=1, dash='dot'),
            name='Prev Close'
        ))
        
    # Calculate dynamic Y-axis range to avoid 0-based scaling
    y_min = hist['Close'].min()
    y_max = hist['Close'].max()
    y_range = y_max - y_min
    y_min -= y_range * 0.05  # Add 5% padding below
    y_max += y_range * 0.05  # Add 5% padding above

    fig.update_layout(
        height=400,
        margin=dict(l=0, r=0, t=20, b=20),
        xaxis=dict(showgrid=False, visible=True),
        yaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)', range=[y_min, y_max]),
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Stats Grid
    info = nifty.info
    st.markdown("### Key Statistics")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    
    c1.metric("Open", f"{info.get('open', 0):,.2f}")
    c2.metric("High", f"{info.get('dayHigh', 0):,.2f}")
    c3.metric("Low", f"{info.get('dayLow', 0):,.2f}")
    c4.metric("Prev Close", f"{info.get('previousClose', 0):,.2f}")
    c5.metric("52W High", f"{info.get('fiftyTwoWeekHigh', 0):,.2f}")
    c6.metric("52W Low", f"{info.get('fiftyTwoWeekLow', 0):,.2f}")

@st.fragment(run_every=30)
def render_watchlist_data(watchlist_id):
    watchlist_items = db.get_watchlist_items(watchlist_id)
    if not watchlist_items:
        st.info("Watchlist is empty.")
        return

    data = []
    for sym in watchlist_items:
        d = get_stock_data(sym)
        if d:
            data.append(d)
    
    if data:
        df = pd.DataFrame(data)
        st.caption(f"Prices updating... {datetime.now().strftime('%H:%M:%S')}")
        
        for _, row in df.iterrows():
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 1])
                c1.markdown(f"**{row['symbol']}**")
                c1.caption(row['name'])
                c2.write(f"₹{row['price']:,.2f}")
                
                color = "green" if row['change_pct'] >= 0 else "red"
                c3.markdown(f":{color}[{row['change_pct']:+.2f}%]")
                
                if c4.button("🤖 AI Insight", key=f"ai_{row['symbol']}"):
                    with st.spinner("Analyzing market data..."):
                        pred = ai.predict_signal(row['symbol'])
                        st.session_state[f"pred_{row['symbol']}"] = pred
                
                if c5.button("🗑️", key=f"del_{row['symbol']}"):
                    db.remove_from_watchlist(watchlist_id, row['symbol'])
                    st.rerun()
                
                if f"pred_{row['symbol']}" in st.session_state:
                    display_ai_insight(st.session_state[f"pred_{row['symbol']}"])

                st.divider()

def render_watchlist():
    st.title("👀 My Watchlists")
    
    user_id = st.session_state.user_id
    
    watchlists = db.get_watchlists(user_id)
    if not watchlists:
        db.create_watchlist("Default Watchlist", user_id)
        st.rerun()
    
    wl_names = [w['name'] for w in watchlists]
    wl_ids = {w['name']: w['id'] for w in watchlists}
    
    tabs = st.tabs(wl_names + ["➕ New List"])
    
    for name in wl_names:
        with tabs[wl_names.index(name)]:
            current_id = wl_ids[name]
            
            c1, c2 = st.columns([3, 1])
            with c1:
                search_query = st.text_input("Search Stock", placeholder="e.g. Tata Motors", key=f"search_{current_id}")
            
            if f"search_res_{current_id}" not in st.session_state:
                st.session_state[f"search_res_{current_id}"] = {}
                
            if search_query and search_query != st.session_state.get(f"last_search_{current_id}", ""):
                results = search_yahoo(search_query)
                if results:
                    st.session_state[f"search_res_{current_id}"] = {f"{r['symbol']} - {r['name']}": r['symbol'] for r in results}
                else:
                    st.session_state[f"search_res_{current_id}"] = {}
                st.session_state[f"last_search_{current_id}"] = search_query
            elif not search_query:
                st.session_state[f"search_res_{current_id}"] = {}
            
            selected_symbol = None
            if st.session_state[f"search_res_{current_id}"]:
                lbl = st.selectbox("Select", options=list(st.session_state[f"search_res_{current_id}"].keys()), key=f"sel_{current_id}")
                if lbl:
                    selected_symbol = st.session_state[f"search_res_{current_id}"][lbl]
            
            with c2:
                st.write("")
                st.write("")
                if st.button("Add", key=f"add_{current_id}"):
                    if selected_symbol:
                        if db.add_to_watchlist(current_id, selected_symbol):
                            st.success(f"Added {selected_symbol}")
                            st.rerun()
                        else:
                            st.error("Failed")
            
            st.divider()
            render_watchlist_data(current_id)

    with tabs[-1]:
        st.subheader("Create New Watchlist")
        with st.form("new_wl_form"):
            new_name = st.text_input("Watchlist Name", placeholder="e.g. High Growth")
            if st.form_submit_button("Create Watchlist"):
                if new_name:
                    if db.create_watchlist(new_name, user_id):
                        st.success(f"Created '{new_name}'!")
                        st.rerun()
                    else:
                        st.error("Name already exists.")

@st.fragment(run_every=10)
def render_portfolio():
    st.title("💼 Portfolio Manager")
    
    user_id = st.session_state.user_id
    
    portfolios = db.get_portfolios(user_id)
    if not portfolios:
        db.create_portfolio("Default Portfolio", user_id)
        st.rerun()
        
    pf_names = [p['name'] for p in portfolios]
    pf_ids = {p['name']: p['id'] for p in portfolios}
    
    tabs = st.tabs(pf_names + ["➕ New Portfolio"])
    
    for name in pf_names:
        with tabs[pf_names.index(name)]:
            current_id = pf_ids[name]
            
            portfolio_items = db.get_portfolio_holdings(current_id)
            total_invested = 0
            current_value = 0
            portfolio_data = []
            
            for item in portfolio_items:
                quote = get_stock_data(item['symbol'])
                current_price = quote['price'] if quote else float(item['avg_price'])
                
                invested = item['quantity'] * float(item['avg_price'])
                curr_val = item['quantity'] * current_price
                pnl = curr_val - invested
                pnl_pct = (pnl / invested) * 100 if invested else 0
                
                total_invested += invested
                current_value += curr_val
                
                portfolio_data.append({
                    'Symbol': item['symbol'],
                    'Qty': item['quantity'],
                    'Avg Price': float(item['avg_price']),
                    'LTP': current_price,
                    'Invested': invested,
                    'Current': curr_val,
                    'P&L': pnl,
                    'P&L %': pnl_pct
                })

            total_pnl = current_value - total_invested
            total_pnl_pct = (total_pnl / total_invested) * 100 if total_invested else 0

            c1, c2, c3 = st.columns(3)
            c1.metric("Current Value", f"₹{current_value:,.2f}", delta=None)
            c2.metric("Total Invested", f"₹{total_invested:,.2f}")
            c3.metric("Total P&L", f"₹{total_pnl:,.2f}", f"{total_pnl_pct:.2f}%")
            
            st.divider()

            subtab1, subtab2, subtab3 = st.tabs(["📊 Holdings", "➕ Add Transaction", "📜 History"])
            
            with subtab1:
                if portfolio_data:
                    h1, h2, h3, h4, h5, h6, h7, h8, h9 = st.columns([1.5, 1, 1.2, 1.2, 1.2, 1.2, 1.2, 0.5, 0.5])
                    h1.markdown("**Symbol**")
                    h2.markdown("**Qty**")
                    h3.markdown("**Avg Price**")
                    h4.markdown("**LTP**")
                    h5.markdown("**Invested**")
                    h6.markdown("**Current**")
                    h7.markdown("**P&L**")
                    h8.markdown("")
                    h9.markdown("")
                    
                    st.divider()
                    
                    for item in portfolio_data:
                        c1, c2, c3, c4, c5, c6, c7, c8, c9 = st.columns([1.5, 1, 1.2, 1.2, 1.2, 1.2, 1.2, 0.5, 0.5])
                        
                        c1.markdown(f"**{item['Symbol']}**")
                        c2.write(f"{item['Qty']}")
                        c3.write(f"₹{item['Avg Price']:,.2f}")
                        c4.write(f"₹{item['LTP']:,.2f}")
                        c5.write(f"₹{item['Invested']:,.2f}")
                        c6.write(f"₹{item['Current']:,.2f}")
                        
                        pnl_color = "green" if item['P&L'] >= 0 else "red"
                        c7.markdown(f":{pnl_color}[₹{item['P&L']:,.2f} ({item['P&L %']:.2f}%)]")
                        
                        if c8.button("🤖", key=f"ai_port_{current_id}_{item['Symbol']}", help="AI Insight"):
                            with st.spinner("Analyzing..."):
                                pred = ai.predict_signal(item['Symbol'])
                                st.session_state[f"pred_port_{current_id}_{item['Symbol']}"] = pred

                        if c9.button("🗑️", key=f"del_port_{current_id}_{item['Symbol']}", help="Delete from Portfolio"):
                            db.update_portfolio_holding(current_id, item['Symbol'], 0, 0)
                            st.rerun()
                        
                        if f"pred_port_{current_id}_{item['Symbol']}" in st.session_state:
                            display_ai_insight(st.session_state[f"pred_port_{current_id}_{item['Symbol']}"])
                        
                        st.divider()
                else:
                    st.info("Your portfolio is empty. Add a trade to get started!")

            with subtab2:
                st.subheader(f"Record a Trade")
                
                search_q = st.text_input("Search Stock", placeholder="e.g. Infosys", key=f"trade_search_{current_id}")
                
                if f"trade_res_{current_id}" not in st.session_state:
                    st.session_state[f"trade_res_{current_id}"] = {}
                    
                if search_q and search_q != st.session_state.get(f"last_trade_search_{current_id}", ""):
                    res = search_yahoo(search_q)
                    if res:
                        st.session_state[f"trade_res_{current_id}"] = {f"{r['symbol']} - {r['name']}": r['symbol'] for r in res}
                    else:
                        st.session_state[f"trade_res_{current_id}"] = {}
                    st.session_state[f"last_trade_search_{current_id}"] = search_q
                elif not search_q:
                    st.session_state[f"trade_res_{current_id}"] = {}

                trade_symbol = None
                if st.session_state[f"trade_res_{current_id}"]:
                    lbl = st.selectbox("Select Stock", options=list(st.session_state[f"trade_res_{current_id}"].keys()), key=f"trade_sel_{current_id}")
                    if lbl:
                        trade_symbol = st.session_state[f"trade_res_{current_id}"][lbl]
                
                with st.form(f"add_trade_form_{current_id}"):
                    c1, c2 = st.columns(2)
                    action = c1.selectbox("Action", ["BUY", "SELL"])
                    qty = c2.number_input("Quantity", min_value=1, value=1)
                    
                    c3, c4 = st.columns(2)
                    
                    current_ltp = 0.0
                    if trade_symbol:
                        q_data = get_stock_data(trade_symbol)
                        if q_data:
                            current_ltp = q_data['price']
                    
                    price = c3.number_input("Price (₹)", min_value=0.0, value=current_ltp, format="%.2f")
                    
                    date = c4.date_input("Date", value=datetime.now())
                    time = c4.time_input("Time", value=datetime.now())
                    
                    submitted = st.form_submit_button("Submit Transaction")
                    
                    if submitted:
                        if not trade_symbol:
                            st.error("Please select a stock first.")
                        else:
                            dt = datetime.combine(date, time)
                            
                            db.add_transaction(current_id, trade_symbol, action, qty, price, dt)
                            
                            current_holding = next((x for x in portfolio_items if x['symbol'] == trade_symbol), None)
                            current_qty = current_holding['quantity'] if current_holding else 0
                            current_avg = float(current_holding['avg_price']) if current_holding else 0.0
                            
                            if action == "BUY":
                                new_qty = current_qty + qty
                                if new_qty > 0:
                                    new_avg = ((current_qty * current_avg) + (qty * price)) / new_qty
                                else:
                                    new_avg = 0
                                db.update_portfolio_holding(current_id, trade_symbol, new_qty, new_avg)
                                st.success(f"Bought {qty} {trade_symbol} at ₹{price}")
                                
                            elif action == "SELL":
                                if current_qty >= qty:
                                    new_qty = current_qty - qty
                                    db.update_portfolio_holding(current_id, trade_symbol, new_qty, current_avg)
                                    st.success(f"Sold {qty} {trade_symbol} at ₹{price}")
                                else:
                                    st.error(f"Insufficient Quantity! You only have {current_qty}.")
                                    
                            st.rerun()

            with subtab3:
                st.subheader("Transaction History")
                try:
                    history = db.get_transactions(current_id)
                    if history:
                        hdf = pd.DataFrame(history)
                        st.dataframe(
                            hdf[['date', 'symbol', 'type', 'quantity', 'price']].style.format({
                                'price': '₹{:,.2f}',
                                'date': '{:%Y-%m-%d %H:%M}'
                            }),
                            use_container_width=True
                        )
                    else:
                        st.info("No transactions found.")
                except Exception as e:
                    st.error(f"Error fetching history: {e}")

    with tabs[-1]:
        st.subheader("Create New Portfolio")
        with st.form("new_pf_form"):
            new_name = st.text_input("Portfolio Name", placeholder="e.g. Long Term")
            if st.form_submit_button("Create Portfolio"):
                if new_name:
                    if db.create_portfolio(new_name, user_id):
                        st.success(f"Created '{new_name}'!")
                        st.rerun()
                    else:
                        st.error("Name already exists.")


import random
import sms_utils

# --- Authentication UI ---
def render_login():
    # Create a placeholder for the entire login UI
    login_placeholder = st.empty()
    
    with login_placeholder.container():
        # Modern CSS for Login Page
        st.markdown("""
            <style>
            .stApp {
                background: radial-gradient(circle at 10% 20%, rgb(0, 0, 0) 0%, rgb(30, 30, 30) 90.2%);
            }
            /* Target the middle column (2nd column) to apply card style */
            [data-testid="stColumn"]:nth-of-type(2) > div {
                background: rgba(255, 255, 255, 0.03);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 40px;
                border: none;
                box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
            }
            .gradient-text {
                background: linear-gradient(45deg, #FF4B2B, #FF416C);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                font-weight: bold;
                font-size: 3rem;
                text-align: center;
                margin-bottom: 10px;
            }
            .subtitle {
                text-align: center;
                color: #aaa;
                margin-bottom: 30px;
                font-size: 1.1rem;
            }
            /* Remove default form styling */
            div[data-testid="stForm"] {
                background: transparent !important;
                border: none !important;
                padding: 0 !important;
            }
            /* Hide form container border */
            div[data-testid="stForm"] > div {
                border: none !important;
                background: transparent !important;
            }
            </style>
        """, unsafe_allow_html=True)

        # Centered Layout
        c1, c2, c3 = st.columns([1, 2, 1])
        
        with c2:
            st.markdown('<p class="gradient-text">StockMinds</p>', unsafe_allow_html=True)
            st.markdown('<p class="subtitle">Your Gateway to Intelligent Market Analysis</p>', unsafe_allow_html=True)
            
            # Tabs for different auth methods
            tab1, tab2, tab3 = st.tabs(["🔑 Password Login", "📱 Mobile OTP", "📝 Register"])
            
            # --- Tab 1: Password Login (Default) ---
            with tab1:
                st.write("")
                with st.form("login_form"):
                    username = st.text_input("Username or Mobile Number", placeholder="Enter your username or mobile")
                    password = st.text_input("Password", type="password", placeholder="Enter your password")
                    st.write("")
                    submit = st.form_submit_button("🚀 Login", type="primary", use_container_width=True)
                    
                    if submit:
                        user = db.login_user(username, password)
                        if user:
                            st.session_state.user_id = user['id']
                            st.session_state.username = user['username']
                            st.toast(f"Welcome back, {user['username']}!", icon="🚀")
                            
                            # Clear the login UI explicitly
                            login_placeholder.empty()
                            st.rerun()
                            st.stop()  # Prevent any further rendering
                        else:
                            st.error("Invalid username or password")

            # --- Tab 2: Mobile OTP Login ---
            with tab2:
                st.write("")
                # Initialize OTP State
                if 'auth_step' not in st.session_state:
                    st.session_state.auth_step = 'input_mobile' # input_mobile, verify_otp
                if 'auth_mobile' not in st.session_state:
                    st.session_state.auth_mobile = ''
                if 'auth_otp' not in st.session_state:
                    st.session_state.auth_otp = None

                # Step 1: Input Mobile Number
                if st.session_state.auth_step == 'input_mobile':
                    with st.form("mobile_form"):
                        mobile = st.text_input("📱 Mobile Number", placeholder="Enter your 10-digit number", value=st.session_state.auth_mobile)
                        st.write("")
                        send_otp = st.form_submit_button("📩 Send OTP", type="primary", use_container_width=True)
                        
                        if send_otp:
                            if len(mobile) < 10:
                                st.error("Please enter a valid mobile number")
                            else:
                                # Generate OTP
                                otp = random.randint(1000, 9999)
                                st.session_state.auth_otp = str(otp)
                                st.session_state.auth_mobile = mobile
                                st.session_state.auth_step = 'verify_otp'
                                
                                # Attempt to send Real SMS
                                sent, msg = sms_utils.send_sms_otp(mobile, otp)
                                
                                if sent:
                                    st.toast(f"✅ {msg}", icon="📩")
                                    st.session_state.auth_msg = "OTP sent via SMS"
                                else:
                                    st.toast(f"⚠️ {msg}", icon="⚠️")
                                    st.session_state.auth_msg = f"SIMULATION: Your OTP is {otp}"
                                
                                st.rerun()

                # Step 2: Verify OTP
                elif st.session_state.auth_step == 'verify_otp':
                    st.info(f"OTP sent to {st.session_state.auth_mobile}")
                    
                    # Show message based on SMS status
                    if "SIMULATION" in st.session_state.get('auth_msg', ''):
                        st.warning(st.session_state.auth_msg)
                    else:
                        st.success(st.session_state.get('auth_msg', 'Check your phone'))
                    
                    with st.form("otp_form"):
                        otp_input = st.text_input("🔑 Enter OTP", placeholder="Enter 4-digit code")
                        st.write("")
                        verify = st.form_submit_button("✅ Verify & Login", type="primary", use_container_width=True)
                        
                        if verify:
                            if otp_input == st.session_state.auth_otp:
                                # OTP Verified
                                mobile = st.session_state.auth_mobile
                                
                                # Check if user exists
                                user = db.get_user_by_mobile(mobile)
                                
                                if not user:
                                    # Register new user
                                    success, msg = db.create_user_by_mobile(mobile)
                                    if success:
                                        user = db.get_user_by_mobile(mobile)
                                        st.toast("Account created successfully!", icon="✨")
                                    else:
                                        st.error("Registration failed.")
                                        return

                                # Login User
                                st.session_state.user_id = user['id']
                                st.session_state.username = user['mobile_number'] # Use mobile as username
                                st.toast(f"Welcome, {mobile}!", icon="🚀")
                                
                                # Clear Auth State
                                del st.session_state.auth_step
                                del st.session_state.auth_mobile
                                del st.session_state.auth_otp
                                if 'auth_msg' in st.session_state: del st.session_state.auth_msg
                                
                                # Clear the login UI explicitly
                                login_placeholder.empty()
                                st.rerun()
                                st.stop()  # Prevent any further rendering
                            else:
                                st.error("Invalid OTP. Please try again.")
                    
                    if st.button("⬅️ Change Number"):
                        st.session_state.auth_step = 'input_mobile'
                        st.rerun()

            # --- Tab 3: Register (Password + Mobile) ---
            with tab3:
                st.write("")
                with st.form("register_form"):
                    new_user = st.text_input("Choose Username", placeholder="Pick a unique username")
                    mobile = st.text_input("Mobile Number", placeholder="For OTP Login (10 digits)")
                    new_pass = st.text_input("Choose Password", type="password", placeholder="Min 6 characters")
                    confirm_pass = st.text_input("Confirm Password", type="password", placeholder="Re-enter password")
                    st.write("")
                    submit_reg = st.form_submit_button("✨ Create Account", type="primary", use_container_width=True)
                    
                    if submit_reg:
                        if new_pass != confirm_pass:
                            st.error("Passwords do not match")
                        elif len(new_pass) < 6:
                            st.error("Password must be at least 6 characters")
                        elif len(mobile) != 10 or not mobile.isdigit():
                            st.error("Please enter a valid 10-digit mobile number")
                        else:
                            success, msg = db.register_user(new_user, new_pass, mobile)
                            if success:
                                st.success("Account created! Please login.")
                            else:
                                st.error(msg)

# --- Main App Structure ---
def main():
    # Critical: Check authentication FIRST before any rendering
    if "user_id" not in st.session_state:
        render_login()
        st.stop()  # Prevent any further execution
        return

    if "page" not in st.session_state:
        st.session_state.page = "Dashboard"

    # Modern fixed navbar with CSS
    st.markdown("""
        <style>
        [data-testid="stVerticalBlock"] > div:first-child {
            position: sticky;
            top: 0;
            z-index: 999;
            background: #0e1117;
            padding: 0.5rem 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        }
        div.stButton > button {
            background: transparent;
            border: none;
            color: #e0e0e0;
            font-size: 14px;
            font-weight: 500;
            padding: 0.5rem 1rem;
            transition: all 0.2s;
        }
        div.stButton > button:hover {
            color: #ff4b4b;
            background: rgba(255,75,75,0.1);
        }
        div.stButton > button[kind="primary"] {
            color: #ff4b4b;
            font-weight: 600;
            border-bottom: 2px solid #ff4b4b;
        }
        </style>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
    with c1:
        if st.button("📊 Dashboard", type="primary" if st.session_state.page == "Dashboard" else "secondary", use_container_width=True):
            st.session_state.page = "Dashboard"
            st.rerun()
    with c2:
        if st.button("👀 Watchlist", type="primary" if st.session_state.page == "Watchlist" else "secondary", use_container_width=True):
            st.session_state.page = "Watchlist"
            st.rerun()
    with c3:
        if st.button("💼 Portfolio", type="primary" if st.session_state.page == "Portfolio" else "secondary", use_container_width=True):
            st.session_state.page = "Portfolio"
            st.rerun()
    with c4:
        if st.button("🚪 Logout", type="secondary", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    st.divider()
    st.caption(f"Logged in as: **{st.session_state.username}**")
    
    if st.session_state.page == "Dashboard":
        render_dashboard()
    elif st.session_state.page == "Watchlist":
        render_watchlist()
    elif st.session_state.page == "Portfolio":
        render_portfolio()

if __name__ == "__main__":
    main()
