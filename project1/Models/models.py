from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, Column, Integer, String, Sequence, Float,PrimaryKeyConstraint, ForeignKey

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, Sequence('user_id_seq'), primary_key=True)
    name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=False)
    password = db.Column(db.String, nullable=False)


class Books(db.Model):
    __tablename__ = "books"
    isbn = db.Column(db.String, primary_key=True)
    title = db.Column(db.String, nullable=False)
    author = db.Column(db.String, nullable=False)
    year = db.Column(db.Integer, nullable=False)

class Reviews(db.Model):
      __tablename__ = "reviews"
      id = db.Column(db.Integer, Sequence('review_id_seq'), primary_key=True)
      user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, primary_key=True)
      user_name = db.Column(db.String, nullable=False)
      book_id = db.Column(db.String, db.ForeignKey("books.isbn"), nullable= False, primary_key=True)
      text = db.Column(db.String, nullable=False)