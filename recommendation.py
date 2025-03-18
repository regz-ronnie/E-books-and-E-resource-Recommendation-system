import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
import pickle

# Load datasets
books = pd.read_csv('books.csv')
users = pd.read_csv('users.csv')
ratings = pd.read_csv('ratings.csv')

# Check for duplicates and missing values in ratings
ratings = ratings.drop_duplicates(subset=['user_id', 'book_id'])
ratings['rating'] = pd.to_numeric(ratings['rating'], errors='coerce')
ratings.dropna(subset=['rating'], inplace=True)

# Popularity-Based Recommender System
ratings_with_name = ratings.merge(books, on='book_id')

# Group by title to compute the number and average of ratings
num_rating_df = ratings_with_name.groupby('title').count()['rating'].reset_index()
num_rating_df.rename(columns={'rating': 'num_ratings'}, inplace=True)

avg_rating_df = ratings_with_name.groupby('title').mean(numeric_only=True)['rating'].reset_index()
avg_rating_df.rename(columns={'rating': 'avg_rating'}, inplace=True)

# Merge number and average ratings
popular_df = num_rating_df.merge(avg_rating_df, on='title')

# Adjust the threshold for filtering (e.g., number of ratings)
popular_df = popular_df[popular_df['num_ratings'] <= 10].sort_values('avg_rating', ascending=False)

# Merge with books for additional details
popular_df = popular_df.merge(books, on='title').drop_duplicates('title')[['title', 'authors', 'image_url', 'num_ratings', 'avg_rating']]

if popular_df.empty:
    print("No popular books found. Adjust thresholds or check the dataset.")
else:
    print(f"Popular books found: {popular_df.shape[0]}")
    print(popular_df.head())

# Collaborative Filtering-Based Recommender System
# Active users: Users who rated at least 5 books
active_users = ratings.groupby('user_id').count()['rating'] >= 2
active_users = active_users[active_users].index

filtered_rating = ratings[ratings['user_id'].isin(active_users)]

# Popular books: Books with at least 3 ratings
popular_books = filtered_rating.groupby('book_id').count()['rating'] >= 2
popular_books = popular_books[popular_books].index

final_ratings = filtered_rating[filtered_rating['book_id'].isin(popular_books)]

# Create pivot table for collaborative filtering
pt = final_ratings.pivot_table(index='book_id', columns='user_id', values='rating', fill_value=0)

if pt.empty:
    print("Pivot table is empty. No collaborative filtering can be performed.")
else:
    print(f"Pivot table shape: {pt.shape}")

    # Debugging: Check if the book is in the pivot table
    book_name = 'Programming in Python'.strip().lower()  # Normalize input
    books['title'] = books['title'].str.strip().str.lower()  # Normalize book titles
    if book_name not in books['title'].values:
        print(f"Book '{book_name}' not found in books dataset.")
    else:
        book_id = books[books['title'] == book_name]['book_id'].values[0]
        print(f"Book '{book_name}' found with book_id: {book_id}")

        # Ensure the book ID is in the pivot table index
        if book_id in pt.index:
            print(f"Book ID {book_id} found in the pivot table.")
        else:
            print(f"Book ID {book_id} not found in the pivot table.")

    similarity_scores = cosine_similarity(pt)

    # Recommendation function
    def recommend(book_name):
        book_name = book_name.strip().lower()

        if book_name not in books['title'].values:
            return f"Book '{book_name}' not found in the dataset."

        book_id = books[books['title'] == book_name]['book_id'].values[0]

        if book_id not in pt.index:
            return f"Book '{book_name}' not found in the pivot table."

        index = list(pt.index).index(book_id)
        similar_items = sorted(list(enumerate(similarity_scores[index])), key=lambda x: x[1], reverse=True)[1:6]

        data = []
        for item_index, score in similar_items:
            similar_book_id = pt.index[item_index]
            temp_df = books[books['book_id'] == similar_book_id]
            if not temp_df.empty:
                item = temp_df[['title', 'authors', 'image_url']].drop_duplicates().values.flatten().tolist()
                if item not in data:
                    data.append(item)

        if not data:
            return f"No recommendations found for '{book_name}'."
        return data

    # Test the recommendation function
    print("\nRecommendations for 'Programming in Python':", recommend('Programming in Python'))

    # Save data structures for later use
    pickle.dump(popular_df, open('popular.pkl', 'wb'))
    pickle.dump(pt, open('pt.pkl', 'wb'))
    pickle.dump(books.drop_duplicates('title'), open('books.pkl', 'wb'))
    pickle.dump(similarity_scores, open('similarity_scores.pkl', 'wb'))
