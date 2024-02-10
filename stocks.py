import requests
from flask import Flask , render_template, redirect, url_for, request, flash
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey
from form import StockForm
import os
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required

API_ACCESS_KEY = 'UR OWN KEY'
current_year = datetime.now().year

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
Bootstrap5(app)

# CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DB_URI", 'sqlite:///stocks.db')
db = SQLAlchemy()
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)

#Create a user_loader callback
@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)

# Define the Stock model
class Stock(db.Model):
    __tablename__ = 'stocks'
    id = Column(Integer, primary_key=True)
    symbol = Column(String(250), unique=True, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Integer)
    exchange = Column(String(250))
    date = Column(Date)

    # Define the foreign key constraint for the user_id column
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    # Define the relationship with the User table
    user = db.relationship('User', back_populates='stocks')

# TODO: Create a User table for all your registered users. 
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = Column(Integer, primary_key = True)
    email = Column(String(100), unique= True)
    password = Column(String(100))
    # Should add repeat password?
    fname = Column(String(100))
    lname = Column(String(100))
    stocks = db.relationship('Stock', back_populates='user')

#Create DB Tables
with app.app_context():
    db.create_all()

@app.route("/")
def home():
    if current_user.is_authenticated:
        result = db.session.execute(db.select(Stock).where(Stock.user_id == current_user.id))
        stocks = result.scalars().all()
        return render_template("index.html", stocks_data=stocks, current_year= current_year, user_name = current_user.fname)
    return redirect(url_for('login'))
    

@app.route('/register', methods= ['GET', 'POST'])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        result = db.session.execute(db.select(User).where(User.email == email))
        user = result.scalar()

        if user:
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))
        
        #HASH AND SALT PASSWORD 
        hash_and_salted_password = generate_password_hash(
            request.form.get("password"),
            method='pbkdf2:sha256',
            salt_length=8
        )

        new_user = User(
            email = request.form.get("email"),
            fname =request.form.get("fname"),
            lname =request.form.get("lname"),
            password =hash_and_salted_password,
        )
    
        db.session.add(new_user)
        db.session.commit()

        # Log in and authenticate user after adding details to database.
        login_user(new_user)

        return redirect(url_for('home', user_name = new_user.fname))
    return render_template("register.html")


@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')

       
        result = db.session.execute(db.select(User).where(User.email == email))
        user = result.scalar()
        
        if not user:
            flash("That email does not exist")
            return redirect(url_for('login'))
        elif not check_password_hash(user.password, password):
            flash("Incorrect password try again")
        else:
            login_user(user)
            return redirect(url_for('home', user_name = current_user.fname))
        
    return render_template("login.html")

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/add_stock', methods=['GET', 'POST'])
@login_required
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
                    date=datetime.strptime(stock_data['date'], "%Y-%m-%dT%H:%M:%S%z").date(),
                    user_id= current_user.id 
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
    app.run(port= 5001, debug=True)
    