
# Sector Oriented Market Research Web App

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](https://github.com/yourusername/stock-analysis-app)  
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Synopsis

**Stock Analysis App** a simple web app that offers advanced stock analytics beyond traditional candlesticks. The app allows users to input their list of ticker symbols and compare them with sector peers using unique charts such as Sharpe Ratio simulations, P/E scatterplots, and innovative bubble charts 

---

## Quickstart

1. **Clone the Repository**

   ```bash
   git clone https://github.com/yourusername/stock-analysis-app.git
   cd stock-analysis-app
   ```

2. **Create & Activate a Virtual Environment**

   ```bash
   python3 -m venv venv
   source venv/bin/activate    # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Application**

   ```bash
   python app.py
   ```

5. **Open in Browser**

   Visit [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

---

## Chart Descriptions & How to Interpret Them

### 1. Sharpe Ratio Simulation
- **Description:**  
  Simulates portfolio performance by computing simulated daily price returns based on users’ ticker inputs.  
- **Interpretation:**  
  Use this view to see estimated portfolio returns and volatility over a fixed period (currently simulated over 30 days). Although currently a placeholder, it sets the groundwork for detailed risk-adjusted performance analysis.

### 2. P/E Scatterplot
- **Description:**  
  Displays stocks using trailing P/E ratios on the x-axis and current price on the y-axis. Bubbles represent the stock’s share of the total market cap within the sector.
- **Interpretation:**  
  Identify stocks that are potentially undervalued or overvalued relative to their peers. User-specified tickers are highlighted in orange, making them easy to compare within their sector.

### 3. Trailing P/E vs. Earnings Growth (Bubble Chart)
- **Description:**  
  Plots trailing P/E ratios (x-axis) against earnings growth (y-axis) with bubble sizes representing each stock’s percentage share of the sector’s total market cap.
- **Interpretation:**  
  Look for companies that combine attractive valuation multiples with strong earnings momentum. The larger the bubble, the more dominant the stock is in the sector.

### 4. Price-to-Book vs. ROE (Bubble Chart)
- **Description:**  
  Compares stocks on a balance-sheet basis by plotting Price-to-Book ratios (x-axis) against Return on Equity (y-axis). Bubble size again reflects the stock’s share of the total market cap.
- **Interpretation:**  
  This chart helps investors identify companies with solid fundamentals. Stocks with lower P/B and higher ROE may represent undervalued opportunities with strong asset efficiency. As with other charts, user-listed tickers are highlighted for quick reference.

> **Note:** Clicking on any bubble will open that company’s Yahoo Finance page (e.g., [https://finance.yahoo.com/quote/HSY/](https://finance.yahoo.com/quote/HSY/)) in a new tab.

---

## File/Folder Structure

```
Stock_Analysis_App/
├── app.py                  # Main Flask application with all routes and logic.
├── requirements.txt        # Python dependencies.
├── README.md               # Project documentation.
├── LICENSE                 # License file (MIT).
├── templates/
│   ├── base.html           # Base layout template (includes navigation, message window).
│   └── index.html          # Main page extending base.html for displaying charts.
└── static/
    ├── css/
    │   └── style.css       # Custom stylesheet (includes analysis area size adjustments).
    ├── js/
    │   └── script.js       # Custom JavaScript for Plotly events and DOM interactions.
    ├── index_lists/        # CSV files for index lists.
    │   ├── SP500_Index.csv
    │   └── Russell_1000_Index.csv
    └── stock_snapshots/    # JSON snapshots of stock data from yfinance.
         └── snapshot_YYYYMMDD-HHMM.json
```

---

## Input Files

| **File/Folder**            | **Description**                                                                                      | **Example/File Name**         |
|----------------------------|------------------------------------------------------------------------------------------------------|-------------------------------|
| `static/index_lists/`      | CSV files containing index lists (e.g., S&P 500). Columns include Symbol, GICS Sector, Sub-Industry, etc. | `Russell_1000_Index.csv`, `SP500_Index.csv`   |
| `static/stock_snapshots/`  | JSON snapshots of stock data downloaded via yfinance. Contains key financial data for each ticker.   | `snapshot_20250414-2329.json`  |

---

## Logic Flow

1. **Startup:**  
   - The app loads CSV index lists from `static/index_lists/` and caches them.
   - Upon startup (or when the user clicks “Fetch Updated Data”), stock data is fetched via yfinance and stored locally as JSON snapshots in `static/stock_snapshots/`.

2. **User Interaction:**  
   - The user enters ticker symbols (comma-separated) and selects an analytic view from the top navigation panel.
   - A GET request is issued with input parameters for tickers and view selection.

3. **Data Processing & Visualization:**  
   - The selected snapshot JSON file is loaded into a pandas DataFrame.
   - Based on the chosen analytic view (e.g., P/E Scatter or bubble charts), corresponding functions compute metrics (e.g., total market cap, bubble size percentage).
   - Plotly generates interactive visuals where hover tooltips display detailed data (including company name and formatted market cap) and custom data that enables click events.

4. **Front End Rendering & Interactivity:**  
   - Jinja2 templates render the complete page including the navigation controls, message window, and analysis area.
   - Custom JavaScript (using Plotly events) listens for clicks on the plotted bubbles to redirect the user to Yahoo Finance.

---

## Front End Details

- **HTML & Templates:**  
  Uses Jinja2 with a modular template design (`base.html` and `index.html`) for dynamic rendering.
  
- **CSS:**  
  Utilizes Bootstrap via CDN for responsive styling. Custom styles in `static/css/style.css` set the analysis area height and adjust the overall look and feel.

- **JavaScript:**  
  Leverages Plotly’s interactivity and a custom script (`static/js/script.js`) to handle window resizing, auto-dismissing messages, and redirection on bubble clicks.

---

## To-Do List

- [ ] **Historical Data Storage:**  
  Enhance the Sharpe Ratio analysis to use pre-saved historical price data.
- [ ] **Error Handling:**  
  Improve data validation and error messaging for missing or inconsistent data.
- [ ] **Unit Testing:**  
  Add unit tests for core functions (data processing, chart generation).
- [ ] **UI Enhancements:**  
  Refine the front-end components for better mobile responsiveness and usability.
- [ ] **Documentation:**  
  Expand on usage examples and developer guides.

---

## Contributing

Contributions are warmly welcomed! To contribute:

1. **Fork the Repository**  
2. **Create a Feature Branch:**  
   Use a descriptive name (e.g., `feature/add-historical-data`).
3. **Make Your Changes**  
4. **Submit a Pull Request**

Please follow a [feature-branch workflow](https://www.atlassian.com/git/tutorials/comparing-workflows/feature-branch-workflow) and ensure your code is well documented with tests where applicable.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

We hope this tool serves as a valuable resource for investors seeking deeper, less conventional stock analyses. Happy investing and coding!

---

Feel free to adjust any of the sections to better fit your project’s evolving scope and style. Enjoy building and contributing to the **Stock Analysis App**!
