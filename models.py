from flask_sqlalchemy import SQLAlchemy
import pandas as pd
from flask_login import UserMixin
from sklearn.metrics.pairwise import cosine_similarity

db = SQLAlchemy()
class user(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), default='user')
    name = db.Column(db.String(100), nullable=False)  # Add this line

  

class UserBookRating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    rating = db.Column(db.Float, nullable=False)

def init_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()  # Create tables

def get_recommendations(user_id, num_recommendations=5):
    # This is a simple collaborative filtering recommendation system
    ratings = pd.read_sql_query(db.session.query(UserBookRating).statement, db.session.bind)
    
    if ratings.empty:
        return []

    user_ratings = ratings.pivot(index='user_id', columns='book_id', values='rating').fillna(0)
    user_similarity = cosine_similarity(user_ratings)
    user_similarity_df = pd.DataFrame(user_similarity, index=user_ratings.index, columns=user_ratings.index)

    similar_users = user_similarity_df[user_id].sort_values(ascending=False).index[1:num_recommendations + 1]
    recommended_books = []

    for similar_user in similar_users:
        books_rated_by_similar_user = ratings[ratings['user_id'] == similar_user]
        recommended_books += list(books_rated_by_similar_user['book_id'])
    
    recommended_books = list(set(recommended_books))  # Unique books
    return Book.query.filter(Book.id.in_(recommended_books)).all()[:num_recommendations]
class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    
    user = db.relationship('User', backref='ratings')
    book = db.relationship('Book', backref='ratings')
# models.py



class Course(db.Model):
    __tablename__ = 'courses'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)

class Books(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    authors = db.Column(db.String(100), nullable=False)
    genre = db.Column(db.String(50), nullable=False)