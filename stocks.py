import requests
from flask import Flask , render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Float, Date
from form import StockForm
import os
from datetime import datetime
from sqlalchemy.exc import IntegrityError

API_ACCESS_KEY = 'YOUR_API_KEY'
current_year = datetime.now().year

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
Bootstrap5(app)

# CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DB_URI", 'sqlite:///stocks.db')
db = SQLAlchemy()
db.init_app(app)

# Define the Book model
class Stock(db.Model):
    id = Column(Integer, primary_key=True)
    symbol = Column(String(250), unique=True, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Integer)
    exchange = Column(String(250))
    date = Column(Date)

#Create DB Tables
with app.app_context():
    db.create_all()

@app.route("/")
def home():
    result = db.session.execute(db.select(Stock))
    stocks = result.scalars().all()
    return render_template("index.html", stocks_data=stocks, current_year= current_year)

@app.route('/add_stock', methods=['GET', 'POST'])
def add_stock():
    form = StockForm()
    if form.validate_on_submit():
        params = {
            'access_key': API_ACCESS_KEY,
            'symbols': form.symbol.data
        }
        api_result = requests.get('http://api.marketstack.com/v1/eod/latest', params)
        if api_result.status_code == 200:
            try:
                api_response = api_result.json()
                stock_data = api_response['data'][0]
                stock = Stock(
                    symbol=stock_data['symbol'],
                    open=stock_data['open'],
                    high=stock_data['high'],
                    low=stock_data['low'],
                    close=stock_data['close'],
                    volume=int(stock_data['volume']),
                    exchange=stock_data['exchange'],
                    date=datetime.strptime(stock_data['date'], "%Y-%m-%dT%H:%M:%S%z").date()
                )
                db.session.add(stock)
                db.session.commit()
                return redirect(url_for('home'))
            except IntegrityError:
                db.session.rollback()
                return render_template('error.html', message='Stock already exists', current_year= current_year)
            except Exception as e:
                return render_template('error.html', message=f'Error: {str(e)}', current_year= current_year)
        else:
            return render_template('error.html', message='Error fetching stock data', current_year= current_year)
    return render_template('add_stock.html', form=form, current_year= current_year)

@app.route("/delete")
def delete():
    stock_id = request.args.get('id')
    stock_to_delete = db.get_or_404(Stock, stock_id)
    db.session.delete(stock_to_delete)
    db.session.commit()
    return redirect(url_for('home', current_year= current_year))

if __name__ == "__main__":
    app.run(debug=True)
    