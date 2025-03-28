import pandas as pd
from flask import Flask, render_template, Response, request
import requests
import csv
import io
import json
import matplotlib
matplotlib.use('Agg')  # MUST BE BEFORE pyplot import
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import numpy as np
from matplotlib.ticker import FormatStrFormatter
import sqlite3
import time
import matplotlib.dates as mdates
from PIL import Image, ImageDraw, ImageFont
import threading
import atexit
import os
import socket
from werkzeug.serving import run_simple

app = Flask(__name__)

# Configure environment
os.environ['MPLBACKEND'] = 'Agg'  # Ensure non-GUI backend

API_KEY = "2f28c228-2dba-4ff3-897e-e6da7359ce76"
headers = {
    "Accepts": "application/json",
    "X-CMC_PRO_API_KEY": API_KEY,
}
url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
params = {"symbol": "DOGE"}

# Database setup
def init_db():
    conn = sqlite3.connect('dogecoin_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS price_history
                 (timestamp INTEGER PRIMARY KEY, price REAL, volume REAL)''')
    conn.commit()
    conn.close()
init_db()

# Cleanup function
@atexit.register
def cleanup():
    plt.close('all')

def get_local_ip():
    """Get the local IP address for network access"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def collect_dogecoin_data():
    while True:
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            data = response.json()
            price = data['data']['DOGE']['quote']['USD']['price']
            volume = data['data']['DOGE']['quote']['USD']['volume_24h']
            current_time = int(time.time())
            
            with sqlite3.connect('dogecoin_data.db') as conn:
                c = conn.cursor()
                c.execute("""
                    INSERT OR REPLACE INTO price_history (timestamp, price, volume)
                    VALUES (?, ?, ?)
                """, (current_time, price, volume))
                print(f"Updated data: {datetime.fromtimestamp(current_time)} - ${price:.6f}")
        except Exception as e:
            print(f"Data collection error: {e}")
        time.sleep(60)  # Collect every minute

def generate_chart_safe(figsize, facecolor):
    """Thread-safe chart generation"""
    plt.switch_backend('Agg')
    fig, ax = plt.subplots(figsize=figsize, facecolor=facecolor)
    return fig, ax

def generate_error_image(message):
    """Thread-safe error image generation"""
    try:
        img = Image.new('RGBA', (800, 400), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            font = ImageFont.load_default()
        d.text((50, 180), message, fill='white', font=font)
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer
    except Exception as e:
        print(f"Error image failed: {e}")
        return None

@app.route("/")
def home():
    return render_template("Home.html")

@app.route("/Page_1")
def index():
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    dogecoin_data = data['data']['DOGE']['quote']['USD']
    return render_template("2nd page.html", 
                         price=dogecoin_data['price'],
                         volume_24h=dogecoin_data['volume_24h'],
                         market_cap=dogecoin_data['market_cap'])

@app.route("/download_csv")
def download_csv():
    crypto_list = "BTC,ETH,DOGE,BNB,XRP,ADA,SOL,DOT,MATIC,LTC,LINK,TRX,AVAX,XLM,ETC,ATOM,FIL,VET,ICP,HBAR,NEAR,GRT,MANA,SAND,THETA,AXS,XTZ,EOS,CAKE,AAVE,FTM,MIOTA,RUNE,MKR,GALA,KSM,COMP,ENJ,BAT,ZEC,DASH,CHZ,XEM,STX,QTUM,ONE,HOT,ZIL,WAVES,ANKR"
    response = requests.get(url, headers=headers, params={"symbol": crypto_list})
    data = response.json()["data"]
    
    output = io.StringIO()
    writer = csv.writer(output)
    first_coin = list(data.keys())[0]
    headers_list = list(data[first_coin].keys()) + list(data[first_coin]['quote']['USD'].keys())
    writer.writerow(["Symbol"] + headers_list)
    
    for symbol, coin_data in list(data.items())[:50]:
        writer.writerow(
            [symbol]
            + [coin_data.get(key, "N/A") for key in coin_data.keys()]
            + [coin_data["quote"]["USD"].get(key, "N/A") for key in coin_data["quote"]["USD"].keys()]
        )
    
    output.seek(0)
    return Response(output, mimetype="text/csv",
                   headers={"Content-Disposition": "attachment;filename=crypto_data.csv"})

@app.route("/dogecoin_volume_histogram.png")
def dogecoin_volume_histogram():
    markets = [
        {"id": "binance", "name": "Binance"},
        {"id": "kucoin", "name": "KuCoin"},
        {"id": "bybit", "name": "Bybit"},
        {"id": "huobi", "name": "Huobi"},
        {"id": "okex", "name": "OKX"},
        {"id": "gate", "name": "Gate.io"},
        {"id": "mexc", "name": "MEXC"},
        {"id": "bitget", "name": "Bitget"},
        {"id": "bitmart", "name": "BitMart"},
        {"id": "lbank", "name": "LBank"}
    ]
    
    market_volumes = {}
    for market in markets:
        try:
            response = requests.get(
                f"https://api.coingecko.com/api/v3/exchanges/{market['id']}/tickers",
                params={"coin_ids": "dogecoin"},
                timeout=5
            )
            data = response.json()
            market_volumes[market['name']] = sum(
                float(t['converted_volume']['usd'])
                for t in data.get('tickers', [])
                if t['base'] == 'DOGE' and t.get('converted_volume', {}).get('usd', 0) > 0
            )
        except Exception as e:
            print(f"Skipping {market['name']}: {e}")
            continue
    
    if not market_volumes:
        buffer = generate_error_image("No volume data available")
        return Response(buffer.getvalue(), mimetype='image/png') if buffer else Response("Error", status=500)
    
    try:
        fig, ax = generate_chart_safe((14, 7), 'none')
        ax.set_facecolor('none')
        
        sorted_markets = sorted(market_volumes.items(), key=lambda x: x[1], reverse=True)
        markets = [m[0] for m in sorted_markets]
        volumes = [m[1]/1e6 for m in sorted_markets]  # Convert to millions
        
        bars = ax.bar(markets, volumes, color='#c98d00', edgecolor='white')
        ax.set_title('Dogecoin 24h Trading Volume', color='white')
        ax.set_ylabel('Volume (Millions USD)', color='white')
        ax.tick_params(colors='white', rotation=45)
        plt.grid(axis='y', alpha=0.3)
        
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, height,
                   f'{height:.1f}M', ha='center', va='bottom',
                   color='white', fontweight='bold')
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=100, transparent=True)
        plt.close(fig)
        buffer.seek(0)
        return Response(buffer.getvalue(), mimetype='image/png')
    except Exception as e:
        print(f"Chart error: {e}")
        buffer = generate_error_image("Chart generation failed")
        return Response(buffer.getvalue(), mimetype='image/png') if buffer else Response("Error", status=500)

@app.route("/dogecoin_price_chart.png")
def dogecoin_price_chart():
    time_range = request.args.get('range', 'week')
    ranges = {
        'hour': 3600, 'day': 86400, 'week': 604800,
        'month': 2592000, 'year': 31536000
    }
    start_time = time.time() - ranges.get(time_range, ranges['week'])
    
    try:
        with sqlite3.connect('dogecoin_data.db') as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("""
                SELECT timestamp, price 
                FROM price_history 
                WHERE timestamp > ? 
                ORDER BY timestamp
            """, (start_time,))
            data = c.fetchall()
        
        if not data:
            buffer = generate_error_image("No data available yet")
            return Response(buffer.getvalue(), mimetype='image/png') if buffer else Response("Error", status=500)
        
        timestamps = [datetime.fromtimestamp(row['timestamp']) for row in data]
        prices = [row['price'] for row in data]
        
        # Ensure we have enough data points
        if len(prices) < 2:
            buffer = generate_error_image("Collecting more data...")
            return Response(buffer.getvalue(), mimetype='image/png') if buffer else Response("Error", status=500)
        
        fig, ax = generate_chart_safe((12, 6), 'none')
        ax.set_facecolor('none')
        ax.plot(timestamps, prices, color='#c98d00', linewidth=2)
        
        ax.set_title(f'Dogecoin Price - Last {time_range.capitalize()}', color='white')
        ax.set_ylabel('Price (USD)', color='white')
        ax.tick_params(colors='white')
        plt.xticks(rotation=45)
        plt.grid(alpha=0.3)
        
        if len(data) > 24:
            locator = mdates.AutoDateLocator()
            ax.xaxis.set_major_locator(locator)
            ax.xaxis.set_major_formatter(mdates.AutoDateFormatter(locator))
        else:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        
        plt.tight_layout()
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=100, transparent=True)
        plt.close(fig)
        buffer.seek(0)
        return Response(buffer.getvalue(), mimetype='image/png')
    except Exception as e:
        print(f"Price chart error: {e}")
        buffer = generate_error_image("Error loading price data")
        return Response(buffer.getvalue(), mimetype='image/png') if buffer else Response("Error", status=500)

@app.route("/debug_data")
def debug_data():
    with sqlite3.connect('dogecoin_data.db') as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""
            SELECT timestamp, price 
            FROM price_history 
            ORDER BY timestamp DESC 
            LIMIT 10
        """)
        data = c.fetchall()
    return {
        "count": len(data),
        "latest": [{"time": datetime.fromtimestamp(row['timestamp']), "price": row['price']} for row in data]
    }

# Start data collection
data_thread = threading.Thread(target=collect_dogecoin_data, daemon=True)
data_thread.start()

if __name__ == "__main__":
    # Get local IP address
    local_ip = get_local_ip()
    print(f"\nAccess the application at:")
    print(f"Local: http://localhost:5000")
    print(f"Network: http://{local_ip}:5000\n")
    
    # Run with better production-ready settings
    run_simple(
        hostname='0.0.0.0', 
        port=5000, 
        application=app, 
        threaded=True,
        processes=1,
        use_reloader=True,
        use_debugger=True
    )
