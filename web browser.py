import pandas as pd
from flask import Flask, render_template, Response
import requests
import csv
import io
import json
#import alchemy

app = Flask(__name__) 

API_KEY= "2f28c228-2dba-4ff3-897e-e6da7359ce76"

headers = {
    "Accepts": "application/json",
    "X-CMC_PRO_API_KEY": API_KEY,
}

url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
params = {"symbol": "DOGE"}


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
    
    #dabūnam datus par 50 crypto currencies
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

if __name__ == "__main__":
    app.run(debug=True) #launch the website
