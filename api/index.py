from flask import Flask, render_template, request, jsonify
import yfinance as yf
import pandas as pd
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator
from plotly.subplots import make_subplots
import plotly.graph_objs as go
import os

# Initialize Flask app with default template folder (Flask will look for templates in the 'templates' folder)
app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.config['DEBUG'] = False

# Ensure static/charts directory exists
os.makedirs("static/charts", exist_ok=True)

# Helper functions
def fetch_stock_data(ticker, start_date=None, end_date=None, period="1mo", interval="1d"):
    try:
        if start_date and end_date:
            stock_data = yf.download(ticker, start=start_date, end=end_date, interval=interval)
        else:
            stock_data = yf.download(ticker, period=period, interval=interval)
        
        if stock_data.empty:
            return None, "No data available for the given ticker."
        stock_data.reset_index(inplace=True)
        return stock_data, None
    except Exception as e:
        return None, str(e)

def calculate_indicators(data, indicators):
    try:
        if 'SMA_10' in indicators:
            data['SMA_10'] = SMAIndicator(data['Close'], window=10).sma_indicator()
        if 'EMA_20' in indicators:
            data['EMA_20'] = EMAIndicator(data['Close'], window=20).ema_indicator()
        if 'RSI' in indicators:
            data['RSI'] = RSIIndicator(data['Close'], window=14).rsi()
        if 'MACD' in indicators:
            macd = MACD(data['Close'])
            data['MACD'] = macd.macd()
            data['MACD_signal'] = macd.macd_signal()
        return data
    except Exception as e:
        raise ValueError(f"Error calculating indicators: {e}")

def generate_chart(data, ticker, chart_type, indicators, line_color, chart_theme):
    try:
        # Create subplots
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            row_heights=[0.6, 0.2, 0.2],
            vertical_spacing=0.05,
            subplot_titles=(f"{ticker} Stock Price and Volume", "MACD", "RSI")
        )

        # Choose chart type (Candlestick, Line, Bar)
        if chart_type == 'candlestick':
            fig.add_trace(go.Candlestick(
                x=data['Date'],
                open=data['Open'],
                high=data['High'],
                low=data['Low'],
                close=data['Close'],
                name="Candlestick",
                increasing_line_color='green',
                decreasing_line_color='red'
            ), row=1, col=1)
        elif chart_type == 'line':
            fig.add_trace(go.Scatter(x=data['Date'], y=data['Close'], mode='lines', name='Stock Price', line=dict(color=line_color, width=2)), row=1, col=1)
        elif chart_type == 'bar':
            fig.add_trace(go.Bar(x=data['Date'], y=data['Close'], name='Stock Price'), row=1, col=1)

        # Add selected indicators
        if 'SMA_10' in indicators:
            fig.add_trace(go.Scatter(x=data['Date'], y=data['SMA_10'], mode='lines', name='10-Day SMA', line=dict(color='orange', width=2, dash='dash')), row=1, col=1)
        if 'EMA_20' in indicators:
            fig.add_trace(go.Scatter(x=data['Date'], y=data['EMA_20'], mode='lines', name='20-Day EMA', line=dict(color='blue', width=2, dash='dot')), row=1, col=1)
        if 'SMA_50' in indicators:
            fig.add_trace(go.Scatter(x=data['Date'], y=data['SMA_50'], mode='lines', name='50-Day SMA', line=dict(color='green', width=2)), row=1, col=1)
        if 'SMA_200' in indicators:
            fig.add_trace(go.Scatter(x=data['Date'], y=data['SMA_200'], mode='lines', name='200-Day SMA', line=dict(color='red', width=2)), row=1, col=1)
        if 'RSI' in indicators:
            fig.add_trace(go.Scatter(x=data['Date'], y=data['RSI'], mode='lines', name='RSI', line=dict(color='purple', width=2)), row=3, col=1)
        if 'MACD' in indicators:
            fig.add_trace(go.Scatter(x=data['Date'], y=data['MACD'], mode='lines', name='MACD Line', line=dict(color='red', width=2)), row=2, col=1)
            fig.add_trace(go.Scatter(x=data['Date'], y=data['MACD_signal'], mode='lines', name='MACD Signal', line=dict(color='green', width=2)), row=2, col=1)
            fig.add_trace(go.Bar(x=data['Date'], y=data['MACD_histogram'], name='MACD Histogram', marker_color='rgba(50, 50, 50, 0.5)', opacity=0.6), row=2, col=1)

        # Add Volume bars
        fig.add_trace(go.Bar(
            x=data['Date'],
            y=data['Volume'],
            name='Volume',
            marker_color='rgba(128,128,128,0.5)',
            opacity=0.6
        ), row=1, col=1)

        # Style and layout
        fig.update_layout(
            title=f"{ticker} Stock Analysis",
            xaxis_title="Date",
            yaxis_title="Price",
            template=chart_theme,
            height=None,  # Remove fixed height to make chart responsive
            autosize=True,
            legend=dict(orientation="h", x=0.5, xanchor="center", y=-0.3),
            plot_bgcolor='rgba(255, 255, 255, 0.1)',  # Background color for the plot area
            margin=dict(l=40, r=40, t=40, b=40),  # Adjust margins for better spacing
            font=dict(family="Arial, sans-serif", size=12, color="black"),  # Custom font for better readability
            hovermode="x unified"  # Improve hover effects
        )

        fig.update_yaxes(title_text="Volume", row=1, col=1)
        fig.update_yaxes(title_text="MACD", row=2, col=1)
        fig.update_yaxes(title_text="RSI", row=3, col=1)

        # Save chart
        chart_path = f"static/charts/{ticker}_chart.html"
        fig.write_html(chart_path)
        return chart_path
    except Exception as e:
        raise ValueError(f"Error generating chart: {e}")

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    ticker = request.form.get('ticker')
    period = request.form.get('period', '1mo')
    interval = request.form.get('interval', '1d')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    chart_type = request.form.get('chart_type', 'candlestick')
    line_color = request.form.get('line_color', '#ff6347')
    chart_theme = request.form.get('chart_theme', 'plotly_white')
    indicators = request.form.getlist('indicators')

    if not ticker:
        return jsonify({"error": "Ticker symbol is required."}), 400

    stock_data, error = fetch_stock_data(ticker, start_date, end_date, period, interval)
    if error:
        return jsonify({"error": error}), 500

    try:
        stock_data = calculate_indicators(stock_data, indicators)
        chart_path = generate_chart(stock_data, ticker, chart_type, indicators, line_color, chart_theme)
        return jsonify({"chart_url": chart_path, "success": True})
    except ValueError as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
