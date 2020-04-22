import os
import csv
from flask import Flask, render_template, request
from Models.models import *

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

def add_books():
	count = 0
	with open('books.csv', 'r') as f:
	  	reader = csv.reader(f)
	  	next(reader)
	  	for isbn, title, author, year in reader:
	  		books_obj = Books(isbn = isbn, title = title, author = author, year = year)
	  		db.session.add(books_obj)
	  		count=count+1
	  	print("No of rows",count)
	  	db.session.commit()

def create_tables():
	db.create_all()

def main():
	create_tables()

if __name__ == "__main__":
	with app.app_context():
		main()