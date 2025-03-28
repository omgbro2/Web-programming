import pandas as pd
from flask import Flask, render_template, Response, request
import requests
import csv
import io
import json
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import numpy as np
from matplotlib.ticker import FormatStrFormatter
import sqlite3
import time
import matplotlib.dates as mdates
from flask import request
from PIL import Image, ImageDraw
#import alchemy

app = Flask(__name__) 

API_KEY= "2f28c228-2dba-4ff3-897e-e6da7359ce76"

headers = {
    "Accepts": "application/json",
    "X-CMC_PRO_API_KEY": API_KEY,
}

url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
params = {"symbol": "DOGE"}

def collect_dogecoin_data():
    while True:
        try:
            response = requests.get(url, headers=headers, params=params)
            data = response.json()
            price = data['data']['DOGE']['quote']['USD']['price']
            volume = data['data']['DOGE']['quote']['USD']['volume_24h']
            current_time = int(time.time())
            
            conn = sqlite3.connect('dogecoin_data.db')
            c = conn.cursor()
            
            # Check if we already have data for this minute
            c.execute("SELECT 1 FROM price_history WHERE timestamp > ?", (current_time - 60,))
            if not c.fetchone():
                c.execute("INSERT INTO price_history VALUES (?, ?, ?)", 
                         (current_time, price, volume))
                conn.commit()
                print(f"Added new data point at {datetime.now()}: ${price:.6f}")
            conn.close()
            
        except Exception as e:
            print(f"Error collecting data: {e}")
        
        time.sleep(60)  # Check every minute

#Pass the required route to the decorator.
@app.route("/") #Page that loads at fist opening the website
def home(): 
    return render_template("Home.html")

@app.route("/Page_1") #2nd page that the button redirects to
def index(): 

    response = requests.get(url, headers=headers, params=params)
    data = response.json()

    dogecoin_data = data['data']['DOGE']['quote']['USD']
    price = dogecoin_data['price']
    volume_24h = dogecoin_data['volume_24h']
    market_cap = dogecoin_data['market_cap']

    return render_template("2nd page.html", price=price, volume_24h=volume_24h, market_cap=market_cap)

@app.route("/download_csv")
def download_csv():
    #dabūnam data par 50 crypto currencies
    crypto_list = "BTC,ETH,DOGE,BNB,XRP,ADA,SOL,DOT,MATIC,LTC,LINK,TRX,AVAX,XLM,ETC,ATOM,FIL,VET,ICP,HBAR,NEAR,GRT,MANA,SAND,THETA,AXS,XTZ,EOS,CAKE,AAVE,FTM,MIOTA,RUNE,MKR,GALA,KSM,COMP,ENJ,BAT,ZEC,DASH,CHZ,XEM,STX,QTUM,ONE,HOT,ZIL,WAVES,ANKR"
    params = {"symbol": crypto_list}

    response = requests.get(url, headers=headers, params=params)
    data = response.json()["data"]

    output = io.StringIO()
    writer = csv.writer(output)

    # Get headers from the first coin
    first_coin = list(data.keys())[0]
    headers_list = list(data[first_coin].keys()) + list(data[first_coin]['quote']['USD'].keys())

    # Write CSV header
    writer.writerow(["Symbol"] + headers_list)

    # Write data for each cryptocurrency
    for symbol, coin_data in list(data.items())[:50]:  # Limit to 50 coins
        writer.writerow(
            [symbol]
            + [coin_data.get(key, "N/A") for key in coin_data.keys()]
            + [coin_data["quote"]["USD"].get(key, "N/A") for key in coin_data["quote"]["USD"].keys()]
        )

    output.seek(0)
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=crypto_data.csv"}
    )

@app.route("/dogecoin_volume_histogram.png")
def dogecoin_volume_histogram():
    # Define markets including crypto-only exchanges
    markets = [
        {"id": "binance", "name": "Binance"},
        {"id": "coinbase", "name": "Coinbase"},
        {"id": "kraken", "name": "Kraken"},
        {"id": "huobi", "name": "Huobi"},
        {"id": "okex", "name": "OKX"},
        {"id": "bitfinex", "name": "Bitfinex"},
        {"id": "bittrex", "name": "Bittrex"},
        {"id": "kucoin", "name": "KuCoin"},  # Added crypto-only exchange
        {"id": "gate", "name": "Gate.io"},    # Added crypto-only exchange
        {"id": "mexc", "name": "MEXC"}       # Added crypto-only exchange
    ]
    
    market_volumes = {}
    
    for market in markets:
        try:
            url = f"https://api.coingecko.com/api/v3/exchanges/{market['id']}/tickers"
            params = {
                "coin_ids": "dogecoin"
            }
            response = requests.get(url, params=params)
            data = response.json()
            
            # Find any DOGE trading pair and sum all volumes
            total_volume = 0
            for ticker in data['tickers']:
                if ticker['base'] == 'DOGE':
                    total_volume += float(ticker['converted_volume']['usd'])
            
            market_volumes[market['name']] = total_volume
            
        except Exception as e:
            print(f"Error fetching data for {market['name']}: {e}")
            market_volumes[market['name']] = 0
    
    # Filter out markets with zero volume
    market_volumes = {k: v for k, v in market_volumes.items() if v > 0}
    
    if not market_volumes:
        return Response("No volume data available", status=404)
    
    # Create histogram
    plt.style.use('dark_background')
    plt.figure(figsize=(14, 7), facecolor='none')
    ax = plt.gca()
    ax.set_facecolor('none')
    
    # Convert to millions and sort by volume
    volumes_millions = [v/1000000 for v in market_volumes.values()]
    sorted_markets = sorted(market_volumes.keys(), 
                          key=lambda x: market_volumes[x], 
                          reverse=True)
    sorted_volumes = [market_volumes[m]/1000000 for m in sorted_markets]
    
    bars = plt.bar(sorted_markets, sorted_volumes, color='#c98d00', edgecolor='white')
    
    # Customize appearance
    plt.title('Dogecoin 24h Trading Volume (Last 30 Days)', color='white', pad=20)
    plt.xlabel('Exchange', color='white')
    plt.ylabel('Volume (Millions USD)', color='white')
    
    ax.tick_params(colors='white', rotation=45)
    plt.grid(True, alpha=0.2, color='white', axis='y')
    
    # Add value labels
    for bar in bars:
        height = bar.get_height()
        if height > 0:  # Only label bars with value
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}M',
                    ha='center', va='bottom',
                    color='white',
                    fontweight='bold')
    
    plt.tight_layout()
    
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', transparent=True, dpi=100)
    buffer.seek(0)
    plt.close()

    return Response(buffer.getvalue(), mimetype='image/png')

@app.route("/dogecoin_price_chart.png")
def dogecoin_price_chart():
    time_range = request.args.get('range', 'week')
    
    # Calculate time ranges
    now = time.time()
    ranges = {
        'hour': now - 3600,
        'day': now - 86400,
        'week': now - 604800,
        'month': now - 2592000,
        'year': now - 31536000
    }
    start_time = ranges.get(time_range, ranges['week'])
    
    # Fetch data from database
    conn = sqlite3.connect('dogecoin_data.db')
    c = conn.cursor()
    c.execute("""
        SELECT timestamp, price 
        FROM price_history 
        WHERE timestamp > ? 
        ORDER BY timestamp
    """, (start_time,))
    data = c.fetchall()
    conn.close()
    
    if not data:
        return generate_error_image("No data available yet")
    
    timestamps = [datetime.fromtimestamp(x[0]) for x in data]
    prices = [x[1] for x in data]
    
    # Verify we have varying data
    if len(set(prices)) == 1:
        return generate_error_image("Data appears static - waiting for variation")
    
    # Create plot with proper scaling
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(12, 6), facecolor='none')
    ax.set_facecolor('none')
    
    ax.plot(timestamps, prices, color='#c98d00', linewidth=2)
    ax.set_title(f'Dogecoin Price - Last {time_range.capitalize()}', color='white')
    ax.set_ylabel('Price (USD)', color='white')
    ax.tick_params(colors='white')
    plt.xticks(rotation=45)
    plt.grid(alpha=0.3)
    
    # Dynamic date formatting
    if len(data) > 24:  # More than 24 data points
        locator = mdates.AutoDateLocator()
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(mdates.AutoDateFormatter(locator))
    else:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    
    plt.tight_layout()
    
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=100, transparent=True)
    buffer.seek(0)
    plt.close()
    
    return Response(buffer.getvalue(), mimetype='image/png')

def generate_error_image(message):
    img = Image.new('RGBA', (800, 400), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((50, 180), message, fill='white')
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return Response(buffer.getvalue(), mimetype='image/png')

@app.route("/debug_data")
def debug_data():
    conn = sqlite3.connect('dogecoin_data.db')
    c = conn.cursor()
    c.execute("SELECT timestamp, price FROM price_history ORDER BY timestamp DESC LIMIT 10")
    data = c.fetchall()
    conn.close()
    
    return {
        "count": len(data),
        "latest": [{"time": datetime.fromtimestamp(x[0]), "price": x[1]} for x in data]
    }

# Start data collection thread
import threading
data_thread = threading.Thread(target=collect_dogecoin_data, daemon=True)
data_thread.start()

if __name__ == "__main__":
    app.run(debug=True) #launch the website
