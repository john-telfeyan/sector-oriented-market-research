import os
import json
import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
import pandas as pd
import yfinance as yf
import plotly
import plotly.graph_objs as go

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Replace with your secure secret key


# Global cache for stock info
stock_info_cache = {}

# Dictionary to hold CSV index data (lists of stocks per sector)
index_data = {}

# ------------------------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------------------------

def load_index_csvs():
    """
    Loads all CSV files from static/index_lists into a dictionary.
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

# Pre-load the index CSVs at startup.
index_data = load_index_csvs()

def is_snapshot_outdated():
    """
    Checks the most recent snapshot file in static/stock_snapshots.
    Returns a tuple (outdated: bool, latest_snapshot_filename: str or None).
    """
    snapshot_folder = os.path.join(app.root_path, 'static', 'stock_snapshots')
    snapshot_files = [f for f in os.listdir(snapshot_folder)
                      if f.startswith('snapshot_') and f.endswith('.json')]
    if not snapshot_files:
        return True, None  # No snapshot available.
    snapshot_files.sort(reverse=True)  # Latest first based on filename pattern.
    latest_snapshot = snapshot_files[0]
    try:
        timestamp_str = latest_snapshot.replace("snapshot_", "").replace(".json", "")
        snapshot_time = datetime.datetime.strptime(timestamp_str, "%Y%m%d-%H%M")
    except Exception as e:
        print(f"Error parsing snapshot filename: {e}")
        return True, latest_snapshot
    now = datetime.datetime.utcnow()
    # Consider outdated if more than 4 days old.
    outdated = (now - snapshot_time).days > 4
    return outdated, latest_snapshot

def load_snapshot_df():
    """
    Loads the most recent snapshot from static/stock_snapshots into a pandas DataFrame.
    The snapshot JSON has stock tickers as keys.
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
    # Create DataFrame indexed by ticker symbols.
    df = pd.DataFrame.from_dict(data, orient='index')
    return df

def get_stock_info(symbol):
    """
    Fetches the ticker info using yfinance and caches the result.
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

def generate_sharpe_chart(tickers, snapshot_df):
    """
    Generates a Plotly line chart simulating a Sharpe ratio analysis.
    (In production you would load and use stored historical price data.)
    """
    # Check for missing tickers in snapshot data.
    for ticker in tickers:
        if ticker not in snapshot_df.index:
            flash(f"Ticker {ticker} not found in snapshot data.", "error")
    data = []
    # For each ticker, simulate a 30-day “historical” price line.
    for idx, ticker in enumerate(tickers):
        # Use the current price as a base if available; otherwise default to 100.
        if ticker in snapshot_df.index and pd.notnull(snapshot_df.loc[ticker].get("regularMarketPrice")):
            base_price = snapshot_df.loc[ticker]["regularMarketPrice"]
        else:
            base_price = 100
        x_vals = list(range(30))
        # Simple simulation of price (replace with real historical series)
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
    User-listed tickers are highlighted in orange.
    """
    sectors = set()
    for ticker in tickers:
        if ticker not in snapshot_df.index:
            flash(f"Ticker {ticker} not found in snapshot data.", "error")
        else:
            sector = snapshot_df.loc[ticker].get("sector")
            if pd.isnull(sector):
                flash(f"Ticker {ticker} is missing sector info.", "error")
            else:
                sectors.add(sector)
    if not sectors:
        return None  # No valid sector information found.

    # Filter snapshot_df to include only stocks in the given sector(s)
    filtered_df = snapshot_df[snapshot_df["sector"].isin(sectors)]
    # Ensure we have values for trailingPE and current price (regularMarketPrice)
    filtered_df = filtered_df[filtered_df["trailingPE"].notna() & filtered_df["regularMarketPrice"].notna()]

    # Separate user-provided tickers for special styling
    user_stocks_df = filtered_df[filtered_df.index.isin(tickers)]
    sector_stocks_df = filtered_df[~filtered_df.index.isin(tickers)]  # Exclude user stocks

    # Plot all sector stocks (default blue)
    sector_trace = go.Scatter(
        x=sector_stocks_df["trailingPE"],
        y=sector_stocks_df["regularMarketPrice"],
        mode="markers",
        marker=dict(size=12, color="rgba(93, 164, 214, 0.7)", line=dict(width=1)),
        text=sector_stocks_df.apply(
            lambda row: f"Symbol: {row.name}<br>Price: {row['regularMarketPrice']}<br>P/E: {row['trailingPE']}",
            axis=1,
        ),
        hoverinfo="text",
        name="Sector Stocks",
    )

    # Plot user-provided tickers (highlighted orange)
    user_trace = go.Scatter(
        x=user_stocks_df["trailingPE"],
        y=user_stocks_df["regularMarketPrice"],
        mode="markers",
        marker=dict(size=14, color="rgba(242, 142, 43, 0.9)", line=dict(width=1)),
        text=user_stocks_df.apply(
            lambda row: f"Symbol: {row.name}<br>Price: {row['regularMarketPrice']}<br>P/E: {row['trailingPE']}",
            axis=1,
        ),
        hoverinfo="text",
        name="User Stocks (Highlighted)",
    )

    sectors_list = ", ".join(list(sectors))
    layout = go.Layout(
        title=f"P/E Scatter for Sector(s): {sectors_list}",
        xaxis=dict(title="Trailing P/E Ratio"),
        yaxis=dict(title="Current Price"),
    )

    fig = go.Figure(data=[sector_trace, user_trace], layout=layout)
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


# ------------------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------------------

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Check if the "Fetch Updated Data" button was pressed.
        if request.form.get("fetch_data"):
            return redirect(url_for('fetch_data'))
            
        tickers_input = request.form.get('tickers', '')
        compare_index = request.form.get('compare_index', '')
        view = request.form.get('view', 'sharpe')
        # Parse comma-separated tickers.
        tickers = [t.strip().upper() for t in tickers_input.split(',') if t.strip()]
        if not tickers:
            flash("Please enter at least one ticker symbol (comma-separated).", "error")
            return redirect(url_for('index'))
        # Use GET parameters for bookmarking.
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

    return render_template(
        "index.html",
        tickers=",".join(tickers),
        compare_index=compare_index,
        view=view,
        graphJSON=graphJSON,
        index_list=list(index_data.keys()),
        snapshot_outdated=snapshot_outdated,
        latest_snapshot=latest_snapshot
    )

@app.route('/fetch_data', methods=['POST'])
def fetch_data():
    """
    Fetch updated data by reading all tickers from the index CSVs (union) and
    updating the snapshot using yfinance. (This process could be extended to include
    fetching and storing historical data over time.)
    """
    # Build a set of tickers from all CSV files in static/index_lists.
    all_tickers = set()
    for csv_name, df in index_data.items():
        if "Symbol" in df.columns:
            tickers = df["Symbol"].dropna().unique().tolist()
            all_tickers.update([t.strip().upper() for t in tickers])
    
    global stock_info_cache
    stock_info_cache = {}  # clear the cache
    for ticker in all_tickers:
        info = get_stock_info(ticker)
        # Only include if a sector is found (filters out mutual funds and others)
        if info and "sector" in info:
            stock_info_cache[ticker] = info
        else:
            print(f"Ticker {ticker} skipped due to missing sector info.")
    
    # Write snapshot to a new file.
    now = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M")
    snapshot_filename = f"snapshot_{now}.json"
    snapshot_path = os.path.join(app.root_path, 'static', 'stock_snapshots', snapshot_filename)
    with open(snapshot_path, "w") as f:
        json.dump(stock_info_cache, f)
    
    flash("Data updated successfully.", "success")
    return redirect(url_for('index'))

# ------------------------------------------------------------------------------
# Run the App
# ------------------------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True)
