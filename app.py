from flask import Flask, render_template, request, flash
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objs as go
import plotly
import json
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

###########################################
# Global Data Definitions and Helper Functions
###########################################

# Cache for stock info (e.g. sector, trailingPE)
stock_info_cache = {}

def get_stock_info(symbol):
    """
    Return the ticker info for a given symbol. Uses a simple cache to avoid redundant calls.
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

def load_index_data():
    """
    Read all CSV files in the "static/index_lists" directory.
    Each CSV should contain at least columns "Symbol" and "GICS Sector". 
    Returns a dictionary where keys are file names and values are DataFrames.
    """
    index_data = {}
    csv_dir = os.path.join("static", "index_lists")
    if not os.path.isdir(csv_dir):
        print("Directory 'static/index_lists' not found.")
        return index_data
    for file in os.listdir(csv_dir):
        if file.endswith(".csv"):
            path = os.path.join(csv_dir, file)
            try:
                df = pd.read_csv(path)
                index_data[file] = df
            except Exception as e:
                print(f"Error loading {file}: {e}")
    return index_data

# Load index CSV data on startup.
index_data = load_index_data()

###########################################
# Analytical Functions
###########################################

def sharpe_ratio_analysis(user_symbols, selected_index_csv):
    """
    1. For the user-supplied tickers, download historical (adjusted) price data from 01/01/2010,
       compute daily returns, and then simulate 25,000 random portfolios.
    2. Determine the target sector using the first user ticker (via yfinance info).
    3. Using the selected benchmark CSV (from index_data), filter the stocks with the same "GICS Sector".
    4. Download historical data for these benchmark stocks and compute each stock’s annualized return and volatility.
    5. Build a Plotly scatter plot with three sets of data:
         • User portfolio simulation (colored by Sharpe ratio),
         • A red star for the maximum Sharpe ratio portfolio,
         • Benchmark stocks from the selected index (plotted as green diamonds).
    """
    # --- User Portfolio Simulation ---
    raw_data = yf.download(user_symbols, start="2010-01-01", auto_adjust=True)
    if raw_data.empty:
        raise ValueError("No price data retrieved for the provided tickers.")

    # Extract adjusted "Close" prices.
    if isinstance(raw_data.columns, pd.MultiIndex):
        if "Close" in raw_data.columns.levels[0]:
            data = raw_data["Close"]
        else:
            raise KeyError("'Close' data not found in multi-index DataFrame.")
    else:
        if "Close" in raw_data.columns:
            data = raw_data["Close"]
        else:
            raise KeyError("'Close' data not found in DataFrame.")
    data.sort_index(inplace=True)
    returns = data.pct_change().dropna()
    if returns.empty:
        raise ValueError("Not enough data to compute returns. Please check the ticker symbols or data period.")

    mean_daily_returns = returns.mean()
    cov_matrix = returns.cov()
    trading_days = 252
    num_portfolios = 25000
    num_assets = len(user_symbols)
    results = np.zeros((3, num_portfolios))  # Rows: [annual return, annual volatility, Sharpe Ratio]

    for i in range(num_portfolios):
        weights = np.random.random(num_assets)
        weights /= np.sum(weights)
        portfolio_return = np.sum(mean_daily_returns * weights) * trading_days
        portfolio_std = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights))) * np.sqrt(trading_days)
        results[0, i] = portfolio_return
        results[1, i] = portfolio_std
        results[2, i] = portfolio_return / portfolio_std if portfolio_std != 0 else 0

    max_sharpe_idx = np.argmax(results[2])
    best_return = results[0, max_sharpe_idx]
    best_std = results[1, max_sharpe_idx]

    # --- Benchmark Data from Selected Index ---
    # Determine target sector from the first user ticker.
    target_info = get_stock_info(user_symbols[0])
    target_sector = target_info.get("sector")
    if not target_sector:
        raise ValueError(f"Sector information not available for {user_symbols[0]}.")

    # Retrieve benchmark universe from the selected index CSV.
    benchmark_df = index_data.get(selected_index_csv)
    if benchmark_df is None:
        raise ValueError("Selected index data not available.")
    benchmark_stocks = benchmark_df[benchmark_df["GICS Sector"] == target_sector]["Symbol"].unique().tolist()
    if not benchmark_stocks:
        raise ValueError(f"No benchmark stocks found for sector {target_sector}.")

    # Download historical data for each benchmark stock.
    bench_data = yf.download(benchmark_stocks, start="2010-01-01", auto_adjust=True)
    if bench_data.empty:
        raise ValueError("No price data retrieved for benchmark stocks.")
    if isinstance(bench_data.columns, pd.MultiIndex):
        if "Close" in bench_data.columns.levels[0]:
            bench_prices = bench_data["Close"]
        else:
            raise KeyError("'Close' data not found in benchmark multi-index DataFrame.")
    else:
        if "Close" in bench_data.columns:
            bench_prices = bench_data["Close"]
        else:
            raise KeyError("'Close' data not found in benchmark DataFrame.")
    bench_prices.sort_index(inplace=True)
    bench_returns = bench_prices.pct_change().dropna()

    # Compute annualized performance for each benchmark stock.
    benchmark_metrics = []
    for symbol in bench_prices.columns:
        if symbol not in bench_returns:
            continue
        series = bench_returns[symbol]
        ann_return = series.mean() * trading_days
        ann_vol = series.std() * np.sqrt(trading_days)
        benchmark_metrics.append((symbol, ann_vol, ann_return))

    if benchmark_metrics:
        bench_vols = [m[1] for m in benchmark_metrics]
        bench_returns_arr = [m[2] for m in benchmark_metrics]
        bench_symbols = [m[0] for m in benchmark_metrics]
        bench_trace = go.Scatter(
            x=bench_vols,
            y=bench_returns_arr,
            mode='markers+text',
            marker=dict(symbol='diamond', color='green', size=10),
            text=bench_symbols,
            textposition='top center',
            name='Sector Benchmarks',
            hovertemplate='Ticker: %{text}<br>Volatility: %{x:.2f}<br>Return: %{y:.2f}<extra></extra>'
        )
    else:
        bench_trace = None

    # --- Build Plotly Figure ---
    sim_trace = go.Scatter(
        x=results[1],
        y=results[0],
        mode='markers',
        marker=dict(
            size=5,
            color=results[2],
            colorscale='RdYlBu',
            showscale=True,
            colorbar=dict(title="Sharpe Ratio")
        ),
        text=[f"Sharpe Ratio: {r:.2f}" for r in results[2]],
        name='User Portfolio Simulation'
    )
    best_trace = go.Scatter(
        x=[best_std],
        y=[best_return],
        mode='markers',
        marker=dict(color='red', size=12, symbol='star'),
        name='Max Sharpe Portfolio'
    )
    traces = [sim_trace, best_trace]
    if bench_trace:
        traces.append(bench_trace)
    layout = go.Layout(
        title="Sharpe Ratio Analysis: User Portfolio vs. Sector Benchmarks",
        xaxis=dict(title="Annualized Volatility"),
        yaxis=dict(title="Annualized Return"),
        hovermode='closest'
    )
    fig = go.Figure(data=traces, layout=layout)
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

def pe_scatterplot_analysis(user_symbol, selected_index_csv):
    """
    1. Use the user-provided ticker (user_symbol) to determine the target sector.
    2. Using the selected index CSV DataFrame from index_data, filter for all stocks in that sector.
    3. For each benchmark stock, fetch trailing P/E (using cached yfinance info).
    4. Build a Plotly scatter plot of trailing P/E values with the user ticker highlighted in red.
    """
    user_symbol = user_symbol.upper().strip()
    info = get_stock_info(user_symbol)
    target_sector = info.get("sector")
    if not target_sector:
        raise ValueError(f"Sector information not available for {user_symbol}.")
    benchmark_df = index_data.get(selected_index_csv)
    if benchmark_df is None:
        raise ValueError("Selected index data not available.")
    bench_symbols = benchmark_df[benchmark_df["GICS Sector"] == target_sector]["Symbol"].unique().tolist()
    if not bench_symbols:
        raise ValueError(f"No benchmark stocks found for sector {target_sector}.")

    symbols_list = []
    pe_values = []
    colors = []  # Highlight the user ticker in red, others in blue.
    for symbol in bench_symbols:
        stock_info = get_stock_info(symbol)
        trailing_pe = stock_info.get("trailingPE")
        if trailing_pe is None:
            continue
        symbols_list.append(symbol)
        pe_values.append(trailing_pe)
        colors.append('red' if symbol == user_symbol else 'blue')

    if not symbols_list:
        raise ValueError(f"No trailing P/E data available for benchmark stocks in sector {target_sector}.")
    trace = go.Scatter(
        x=symbols_list,
        y=pe_values,
        mode='markers+text',
        marker=dict(size=10, color=colors),
        text=symbols_list,
        textposition="top center",
        hovertemplate="Ticker: %{text}<br>Trailing P/E: %{y}<extra></extra>"
    )
    layout = go.Layout(
        title=f"P/E Scatter Plot for {target_sector} Sector (Benchmark: {selected_index_csv})",
        xaxis=dict(title="Ticker"),
        yaxis=dict(title="Trailing P/E Ratio")
    )
    fig = go.Figure(data=[trace], layout=layout)
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

###########################################
# Flask Route
###########################################

@app.route('/', methods=["GET", "POST"])
def index():
    graphJSON = None
    symbols = ""
    view = "sharpe"  # default analytic view
    selected_index = None
    # Build the drop-down options from loaded index CSVs.
    index_options = sorted(index_data.keys())
    
    if request.method == "POST":
        symbols_text = request.form.get("symbols", "")
        view = request.form.get("view", "sharpe")
        selected_index = request.form.get("index_choice", index_options[0] if index_options else None)
        symbols_list = [s.strip().upper() for s in symbols_text.split(",") if s.strip()]
        symbols = ",".join(symbols_list)
        
        if symbols_list:
            try:
                if view == "sharpe":
                    graphJSON = sharpe_ratio_analysis(symbols_list, selected_index)
                elif view == "pe":
                    graphJSON = pe_scatterplot_analysis(symbols_list[0], selected_index)
            except (ValueError, KeyError) as e:
                flash(str(e))
        else:
            flash("Please enter at least one ticker symbol.")
    
    return render_template(
        "index.html",
        graphJSON=graphJSON,
        symbols=symbols,
        view=view,
        index_options=index_options,
        selected_index=selected_index
    )

if __name__ == '__main__':
    app.run(debug=True)
