import os
import functools
import json
from passlib.hash import sha256_crypt
import requests

from flask import Flask, session, render_template, request, redirect, url_for, jsonify
from flask_session import Session

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import or_, and_

from authlib.client import OAuth2Session
import google.oauth2.credentials
import googleapiclient.discovery
import google_auth

from Models.models import *

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

app.secret_key = os.environ.get("FN_FLASK_SECRET_KEY", default=False)

app.register_blueprint(google_auth.app)

@app.route("/")
def index():
	if google_auth.is_logged_in():
		user_info = google_auth.get_user_info()
		return render_template("main_page.html", name=user_info['given_name'], headline=None)
	if session.get('logged_in') != None and session['logged_in'] == True:
		return render_template("main_page.html", name=session['username'], headline=None)

	session['username'] = None
	session['user_id'] = None
	session['logged_in'] = False
	session['reviews'] = {}
	return render_template("main_page.html", headline="You are not logged in. Please signup/login")

@app.route("/register")
def register():
	return render_template("register.html", message = None)

@app.route("/login")
def login():
	return render_template("login.html", message= None)

@app.route("/logout")
def logout():
	session['logged_in'] = False

	if session['reviews'] != None  and session['username'] != None and session['user_id']!=None:
		for book_title, text in session['reviews'].items():
			if text != None:
				book_obj = Books.query.filter_by(title=book_title).first()
				review = Reviews(user_id=session['user_id'], user_name=session['username'], book_id=book_obj.isbn, text = text)
				db.session.add(review)
		db.session.commit()

	session.clear()
	return redirect(url_for('google_auth.logout'))

@app.route("/register_to_db", methods=['POST'])
def register_to_db():
	name = request.form.get("uname")
	email = request.form.get("email")
	pwd = request.form.get("password")
	cpass = request.form.get("cpass")

	if(cpass != pwd):
		return render_template("register.html", message="Confirm password doesn't match.")

	password = sha256_crypt.encrypt(pwd)

	if(User.query.filter_by(email=email).count()==0):
		user_obj = User(name=name, email=email, password=password)
		db.session.add(user_obj)
		db.session.commit()
		return render_template("main_page.html", headline="reg_suc")
	else:
		return render_template("errorpage.html", message="Email id already used.")

@app.route("/credentials_check", methods=['POST'])
def credentials_check():
	email = request.form.get("email")
	pwd = request.form.get("password")

	query = User.query.filter_by(email=email).first()
	
	if sha256_crypt.verify(pwd, query.password) == True:
		session['username'] = query.name
		session['user_id'] = query.id
		session['logged_in'] = True
		session['reviews'] = {}
		return render_template("main_page.html", name = session['username'] , headline="")
	else:
		session['logged_in'] = False
		return render_template("login.html", message="Invalid password or username.")

@app.route("/search", methods = ['POST'])
def search():
	search_text =request.form.get("search_text")
		
	results = []
	results = Books.query.filter(or_(Books.isbn.like("%"+search_text+"%"), 
		Books.title.like("%"+search_text+"%"), Books.author.like("%"+search_text+"%"))).all()
	if len(results) == 0 :
		return render_template("main_page.html", name = session['username'] , headline="", results = False)
	return render_template("main_page.html", name = session['username'] , headline="", results = results)

@app.route("/book_page/<string:item_id>/", methods=['GET', 'POST'])
def book_page(item_id):
	book_obj = Books.query.filter_by(isbn=item_id).first()

	res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "Yiqys5PbZAAl9fwxJbnMA", "isbns": book_obj.isbn})
	if res.status_code == 200:
		data = res.json()
		value = data['books']

		finalMap = {}
		for d in value:
			finalMap.update(d)
		work_ratings_count = finalMap['work_ratings_count']
		average_rating = finalMap['average_rating']


	if Reviews.query.filter_by(book_id=book_obj.isbn).count() != 0:
		results = Reviews.query.filter_by(book_id=book_obj.isbn).all()
	else:
		results = None

	if book_obj.title not in session['reviews']:
		session['reviews'][book_obj.title] = None

	return render_template("book_page.html", item = book_obj, reviews_own = session['reviews'][book_obj.title]  , reviews_others = results, username = session['username'], work_ratings_count=work_ratings_count, average_rating= average_rating)

@app.route("/add_review/<string:item_id>/", methods=['GET', 'POST'])
def add_review(item_id):
	text = request.form.get("my_review")
	book_obj = Books.query.filter_by(isbn=item_id).first()

	if session.get('logged_in') is False:
		return render_template("errorpage.html", message="Login to add review")

	if book_obj.title in session['reviews']:
		if session['reviews'][book_obj.title] !=None:
			return render_template("errorpage.html", message="Users should not be able to submit multiple reviews for the same book.")
	
	existing_reviews = Reviews.query.filter(and_(Reviews.user_id==session['user_id'], Reviews.book_id==book_obj.isbn)).count()
	
	if existing_reviews!=0 :
		return render_template("errorpage.html", message="Current user has already reviewed this book")

	session['reviews'][book_obj.title] = text
	return redirect(url_for("book_page", item_id = book_obj.isbn))

@app.route('/api/<string:isbn>', methods=['GET'])
def api_build(isbn):
	res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "Yiqys5PbZAAl9fwxJbnMA", "isbns": isbn})
	print(res)
	if res.status_code == 200:
		data = res.json()
		value = data['books']

		finalMap = {}
		for d in value:
			finalMap.update(d)
		work_ratings_count = finalMap['work_ratings_count']
		average_rating = finalMap['average_rating']

		book_obj = Books.query.filter_by(isbn=isbn).first()

		return jsonify({
			"title" : book_obj.title,
			"author": book_obj.author,
			"year"  : book_obj.year,
			"isbn" : book_obj.isbn,
			"review_count": work_ratings_count,
			"average_score" : average_rating })
	else:
		return render_template("errorpage.html", message="Error in isbn no")

#{
#     "title": "Memory",
#     "author": "Doug Lloyd",
#     "year": 2015,
#     "isbn": "1632168146",
#     "review_count": 28,
#     "average_score": 5.0
# }