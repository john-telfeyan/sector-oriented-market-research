import os
import json
import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
import pandas as pd
import yfinance as yf
import plotly
import plotly.graph_objs as go

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Replace with your secure key.

# Global cache for stock info and global index CSV data
stock_info_cache = {}
index_data = {}

def load_index_csvs():
    """
    Load all CSV files from static/index_lists into a dictionary.
    Keys are CSV filenames.
    """
    index_folder = os.path.join(app.root_path, 'static', 'index_lists')
    csv_files = [f for f in os.listdir(index_folder) if f.endswith('.csv')]
    data = {}
    for csv_file in csv_files:
        csv_path = os.path.join(index_folder, csv_file)
        try:
            df = pd.read_csv(csv_path)
            data[csv_file] = df
        except Exception as e:
            print(f"Error loading {csv_file}: {e}")
    return data

# Pre-load the index CSV files at startup.
index_data = load_index_csvs()

def is_snapshot_outdated():
    """
    Check the most recent snapshot file in static/stock_snapshots.
    Returns (outdated: bool, latest_snapshot_filename: str or None).
    """
    snapshot_folder = os.path.join(app.root_path, 'static', 'stock_snapshots')
    snapshot_files = [f for f in os.listdir(snapshot_folder)
                      if f.startswith('snapshot_') and f.endswith('.json')]
    if not snapshot_files:
        return True, None
    snapshot_files.sort(reverse=True)
    latest_snapshot = snapshot_files[0]
    try:
        timestamp_str = latest_snapshot.replace("snapshot_", "").replace(".json", "")
        snapshot_time = datetime.datetime.strptime(timestamp_str, "%Y%m%d-%H%M")
    except Exception as e:
        print(f"Error parsing snapshot filename: {e}")
        return True, latest_snapshot
    now = datetime.datetime.utcnow()
    outdated = (now - snapshot_time).days > 4
    return outdated, latest_snapshot

def load_snapshot_df():
    """
    Loads the most recent snapshot from static/stock_snapshots into a pandas DataFrame.
    The JSON structure is assumed to have tickers as keys.
    """
    snapshot_folder = os.path.join(app.root_path, 'static', 'stock_snapshots')
    snapshot_files = [f for f in os.listdir(snapshot_folder)
                      if f.startswith('snapshot_') and f.endswith('.json')]
    if not snapshot_files:
        return pd.DataFrame()
    snapshot_files.sort(reverse=True)
    latest_snapshot = snapshot_files[0]
    snapshot_path = os.path.join(snapshot_folder, latest_snapshot)
    with open(snapshot_path, "r") as f:
        data = json.load(f)
    df = pd.DataFrame.from_dict(data, orient='index')
    return df

def get_stock_info(symbol):
    """
    Fetches ticker info from yfinance and caches it.
    """
    symbol = symbol.upper().strip()
    if symbol in stock_info_cache:
        return stock_info_cache[symbol]
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        stock_info_cache[symbol] = info
        return info
    except Exception as e:
        print(f"Error fetching info for {symbol}: {e}")
        return {}

def format_market_cap(market_cap):
    """
    Convert a raw market cap number into a human-readable string.
    """
    try:
        market_cap = float(market_cap)
    except (ValueError, TypeError):
        return "N/A"
    if market_cap >= 1e12:
        return f"{market_cap/1e12:.2f}T"
    elif market_cap >= 1e9:
        return f"{market_cap/1e9:.2f}B"
    elif market_cap >= 1e6:
        return f"{market_cap/1e6:.2f}M"
    elif market_cap >= 1e3:
        return f"{market_cap/1e3:.2f}K"
    else:
        return str(market_cap)

# ----- Analytics Functions -----

def generate_sharpe_chart(tickers, snapshot_df):
    """
    A placeholder for Sharpe Ratio analysis (using simulated historical data).
    """
    for ticker in tickers:
        if ticker not in snapshot_df.index:
            flash(f"Ticker {ticker} not found in snapshot data.", "error")
    data = []
    for idx, ticker in enumerate(tickers):
        if ticker in snapshot_df.index and pd.notnull(snapshot_df.loc[ticker].get("regularMarketPrice")):
            base_price = snapshot_df.loc[ticker]["regularMarketPrice"]
        else:
            base_price = 100
        x_vals = list(range(30))
        y_vals = [base_price * (1 + 0.01 * i) for i in range(30)]
        trace = go.Scatter(
            x=x_vals,
            y=y_vals,
            mode='lines+markers',
            name=ticker
        )
        data.append(trace)
    layout = go.Layout(
        title="Portfolio Simulation: Sharpe Ratio Analysis",
        xaxis=dict(title="Time (Days)"),
        yaxis=dict(title="Simulated Price")
    )
    fig = go.Figure(data=data, layout=layout)
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

def generate_pe_scatter_chart(tickers, snapshot_df):
    """
    Generates a P/E scatter plot.
    Bubbles are sized as a percentage share of total market cap for the sector.
    Hover info now includes:
      - Stock symbol
      - Company name (using longName or shortName)
      - Price, P/E, and human-readable market cap
    Clicking on a bubble (via customdata) will send the user to Yahoo Finance.
    """
    sectors = set()
    for ticker in tickers:
        if ticker not in snapshot_df.index:
            flash(f"Ticker {ticker} not found in snapshot data.", "error")
        else:
            sec = snapshot_df.loc[ticker].get("sector")
            if pd.isnull(sec):
                flash(f"Ticker {ticker} is missing sector info.", "error")
            else:
                sectors.add(sec)
    if not sectors:
        return None

    filtered_df = snapshot_df[snapshot_df["sector"].isin(sectors)]
    filtered_df = filtered_df[
        filtered_df["trailingPE"].notna() & 
        filtered_df["regularMarketPrice"].notna() & 
        filtered_df["marketCap"].notna()
    ]
    total_market_cap = filtered_df["marketCap"].sum()
    calc_size = lambda x: max(10, (x / total_market_cap * 100) * 2)

    user_df = filtered_df[filtered_df.index.isin(tickers)]
    sector_df = filtered_df[~filtered_df.index.isin(tickers)]

    def build_hover_text(row):
        company = row.get('longName', row.get('shortName', 'N/A'))
        return (
            f"Symbol: {row.name}<br>"
            f"Company: {company}<br>"
            f"Price: {row['regularMarketPrice']}<br>"
            f"P/E: {row['trailingPE']}<br>"
            f"Market Cap: {format_market_cap(row['marketCap'])}"
        )

    sector_trace = go.Scatter(
        x=sector_df["trailingPE"],
        y=sector_df["regularMarketPrice"],
        mode='markers',
        marker=dict(
            size=sector_df["marketCap"].apply(calc_size),
            color='rgba(93, 164, 214, 0.7)',
            line=dict(width=1)
        ),
        text=sector_df.apply(build_hover_text, axis=1),
        hoverinfo='text',
        customdata=sector_df.index.tolist(),
        name="Sector Stocks"
    )
    user_trace = go.Scatter(
        x=user_df["trailingPE"],
        y=user_df["regularMarketPrice"],
        mode='markers',
        marker=dict(
            size=user_df["marketCap"].apply(calc_size),
            color='rgba(242, 142, 43, 0.9)',
            line=dict(width=1)
        ),
        text=user_df.apply(build_hover_text, axis=1),
        hoverinfo='text',
        customdata=user_df.index.tolist(),
        name="User Stocks (Highlighted)"
    )
    sectors_list = ", ".join(list(sectors))
    layout = go.Layout(
        title=f"P/E Scatter for Sector(s): {sectors_list}",
        xaxis=dict(title="Trailing P/E Ratio"),
        yaxis=dict(title="Current Price")
    )
    fig = go.Figure(data=[sector_trace, user_trace], layout=layout)
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

def generate_trailingPE_vs_earningsGrowth_chart(tickers, snapshot_df):
    """
    Generates a bubble chart with:
      - X-Axis: Trailing P/E
      - Y-Axis: Earnings Growth
      - Bubble size: Percentage share of total market cap in the sector
      - Hover text includes company name and formatted market cap
    Clicking a bubble will link to the stock’s Yahoo Finance page.
    """
    sectors = set()
    for ticker in tickers:
        if ticker not in snapshot_df.index:
            flash(f"Ticker {ticker} not found in snapshot data.", "error")
        else:
            sec = snapshot_df.loc[ticker].get("sector")
            if pd.isnull(sec):
                flash(f"Ticker {ticker} is missing sector info.", "error")
            else:
                sectors.add(sec)
    if not sectors:
        return None

    filtered_df = snapshot_df[snapshot_df["sector"].isin(sectors)]
    filtered_df = filtered_df[
        filtered_df["trailingPE"].notna() & 
        filtered_df["earningsGrowth"].notna() & 
        filtered_df["marketCap"].notna()
    ]
    total_market_cap = filtered_df["marketCap"].sum()
    calc_size = lambda x: max(10, (x / total_market_cap * 100) * 2)

    user_df = filtered_df[filtered_df.index.isin(tickers)]
    sector_df = filtered_df[~filtered_df.index.isin(tickers)]

    def build_hover_text(row):
        company = row.get('longName', row.get('shortName', 'N/A'))
        return (
            f"Symbol: {row.name}<br>"
            f"Company: {company}<br>"
            f"Trailing P/E: {row['trailingPE']}<br>"
            f"Earnings Growth: {row['earningsGrowth']}<br>"
            f"Market Cap: {format_market_cap(row['marketCap'])}"
        )

    sector_trace = go.Scatter(
        x=sector_df["trailingPE"],
        y=sector_df["earningsGrowth"],
        mode='markers',
        marker=dict(
            size=sector_df["marketCap"].apply(calc_size),
            color="rgba(93, 164, 214, 0.7)",
            line=dict(width=1)
        ),
        text=sector_df.apply(build_hover_text, axis=1),
        hoverinfo='text',
        customdata=sector_df.index.tolist(),
        name="Sector Stocks"
    )
    user_trace = go.Scatter(
        x=user_df["trailingPE"],
        y=user_df["earningsGrowth"],
        mode='markers',
        marker=dict(
            size=user_df["marketCap"].apply(calc_size),
            color="rgba(242, 142, 43, 0.9)",
            line=dict(width=1)
        ),
        text=user_df.apply(build_hover_text, axis=1),
        hoverinfo='text',
        customdata=user_df.index.tolist(),
        name="User Stocks (Highlighted)"
    )
    sectors_list = ", ".join(list(sectors))
    layout = go.Layout(
        title=f"Trailing P/E vs. Earnings Growth for Sector(s): {sectors_list}",
        xaxis=dict(title="Trailing P/E Ratio"),
        yaxis=dict(title="Earnings Growth")
    )
    fig = go.Figure(data=[sector_trace, user_trace], layout=layout)
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

def generate_priceToBook_vs_ROE_chart(tickers, snapshot_df):
    """
    Generates a bubble chart with:
      - X-Axis: Price-to-Book Ratio
      - Y-Axis: Return on Equity
      - Bubble size: Percentage share of total market cap in the sector
      - Hover text includes company name and formatted market cap
    Clicking a bubble redirects to Yahoo Finance.
    """
    sectors = set()
    for ticker in tickers:
        if ticker not in snapshot_df.index:
            flash(f"Ticker {ticker} not found in snapshot data.", "error")
        else:
            sec = snapshot_df.loc[ticker].get("sector")
            if pd.isnull(sec):
                flash(f"Ticker {ticker} is missing sector info.", "error")
            else:
                sectors.add(sec)
    if not sectors:
        return None

    filtered_df = snapshot_df[snapshot_df["sector"].isin(sectors)]
    filtered_df = filtered_df[
        filtered_df["priceToBook"].notna() & 
        filtered_df["returnOnEquity"].notna() & 
        filtered_df["marketCap"].notna()
    ]
    total_market_cap = filtered_df["marketCap"].sum()
    calc_size = lambda x: max(10, (x / total_market_cap * 100) * 2)

    user_df = filtered_df[filtered_df.index.isin(tickers)]
    sector_df = filtered_df[~filtered_df.index.isin(tickers)]

    def build_hover_text(row):
        company = row.get('longName', row.get('shortName', 'N/A'))
        return (
            f"Symbol: {row.name}<br>"
            f"Company: {company}<br>"
            f"Price-to-Book: {row['priceToBook']}<br>"
            f"ROE: {row['returnOnEquity']}<br>"
            f"Market Cap: {format_market_cap(row['marketCap'])}"
        )

    sector_trace = go.Scatter(
        x=sector_df["priceToBook"],
        y=sector_df["returnOnEquity"],
        mode='markers',
        marker=dict(
            size=sector_df["marketCap"].apply(calc_size),
            color="rgba(93, 164, 214, 0.7)",
            line=dict(width=1)
        ),
        text=sector_df.apply(build_hover_text, axis=1),
        hoverinfo='text',
        customdata=sector_df.index.tolist(),
        name="Sector Stocks"
    )
    user_trace = go.Scatter(
        x=user_df["priceToBook"],
        y=user_df["returnOnEquity"],
        mode='markers',
        marker=dict(
            size=user_df["marketCap"].apply(calc_size),
            color="rgba(242, 142, 43, 0.9)",
            line=dict(width=1)
        ),
        text=user_df.apply(build_hover_text, axis=1),
        hoverinfo='text',
        customdata=user_df.index.tolist(),
        name="User Stocks (Highlighted)"
    )
    sectors_list = ", ".join(list(sectors))
    layout = go.Layout(
        title=f"Price-to-Book vs. ROE for Sector(s): {sectors_list}",
        xaxis=dict(title="Price-to-Book Ratio"),
        yaxis=dict(title="Return on Equity")
    )
    fig = go.Figure(data=[sector_trace, user_trace], layout=layout)
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

# ----- Routes -----

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # If "Fetch Updated Data" was pressed, redirect accordingly.
        if request.form.get("fetch_data"):
            return redirect(url_for('fetch_data'))
        tickers_input = request.form.get('tickers', '')
        compare_index = request.form.get('compare_index', '')
        view = request.form.get('view', 'sharpe')
        tickers = [t.strip().upper() for t in tickers_input.split(',') if t.strip()]
        if not tickers:
            flash("Please enter at least one ticker symbol (comma-separated).", "error")
            return redirect(url_for('index'))
        return redirect(url_for('index', tickers=",".join(tickers),
                                compare_index=compare_index, view=view))
    
    # GET request processing.
    tickers_str = request.args.get('tickers', '')
    tickers = [t.strip().upper() for t in tickers_str.split(',') if t.strip()]
    compare_index = request.args.get('compare_index', '')
    view = request.args.get('view', 'sharpe')

    snapshot_outdated, latest_snapshot = is_snapshot_outdated()
    snapshot_df = load_snapshot_df()
    graphJSON = None
    if tickers:
        if view == 'sharpe':
            graphJSON = generate_sharpe_chart(tickers, snapshot_df)
        elif view == 'pe':
            graphJSON = generate_pe_scatter_chart(tickers, snapshot_df)
        elif view == 'pe_growth':
            graphJSON = generate_trailingPE_vs_earningsGrowth_chart(tickers, snapshot_df)
        elif view == 'pb_roe':
            graphJSON = generate_priceToBook_vs_ROE_chart(tickers, snapshot_df)
    
    return render_template("index.html",
                           tickers=",".join(tickers),
                           compare_index=compare_index,
                           view=view,
                           graphJSON=graphJSON,
                           index_list=list(index_data.keys()),
                           snapshot_outdated=snapshot_outdated,
                           latest_snapshot=latest_snapshot)

@app.route('/fetch_data', methods=['POST'])
def fetch_data():
    """
    Fetch updated data by reading all tickers from the index CSVs and updating the snapshot.
    """
    all_tickers = set()
    for csv_name, df in index_data.items():
        if "Symbol" in df.columns:
            tickers = df["Symbol"].dropna().unique().tolist()
            all_tickers.update([t.strip().upper() for t in tickers])
    
    global stock_info_cache
    stock_info_cache = {}
    for ticker in all_tickers:
        info = get_stock_info(ticker)
        if info and "sector" in info:
            stock_info_cache[ticker] = info
        else:
            print(f"Ticker {ticker} skipped due to missing sector info.")
    
    now = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M")
    snapshot_filename = f"snapshot_{now}.json"
    snapshot_path = os.path.join(app.root_path, 'static', 'stock_snapshots', snapshot_filename)
    with open(snapshot_path, "w") as f:
        json.dump(stock_info_cache, f)
    
    flash("Data updated successfully.", "success")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
