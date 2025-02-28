from flask import Flask, render_template
import requests
#import alchemy

app = Flask(__name__) 

API_KEY= "2f28c228-2dba-4ff3-897e-e6da7359ce76"

headers = {
    "Accepts": "application/json",
    "X-CMC_PRO_API_KEY": API_KEY,
}

url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
params = {"symbol": "DOGE"}


# Pass the required route to the decorator. 
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


if __name__ == "__main__":
    app.run(debug=True) #launch the website