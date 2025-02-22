from flask import Flask, render_template

app = Flask(__name__) 

# Pass the required route to the decorator. 
@app.route("/") #Page that loads at fist opening the website
def home(): 
	return render_template("Home.html")



@app.route("/Page_1") #2nd page that the button redirects to
def index(): 
	return render_template("2nd page.html")



app.run(debug=True) 