Book Recommender System
Overview
This project implements a book recommender system using two approaches:

Popularity-Based Recommender: Recommends books based on the most popular books (i.e., books with the highest average ratings and a significant number of ratings).

Collaborative Filtering Recommender: Recommends books based on users’ ratings of similar books, using cosine similarity to identify similar books.

Purpose
The system uses a dataset of books, ratings, and users to provide personalized recommendations. By using collaborative filtering techniques, it suggests books to a user based on books they may like, based on others' preferences. Additionally, a popularity-based approach is used to recommend books that are generally well-liked by a broader audience.

Dataset
The system uses the following datasets:

Books Dataset (books.csv): Contains information about books such as book_id, title, authors, and image_url.

Users Dataset (users.csv): Contains information about users, such as user_id and other user-specific details (if any).

Ratings Dataset (ratings.csv): Contains user ratings for books, including user_id, book_id, and rating.

How It Works
Popularity-Based Recommender
The system filters books that have a significant number of ratings (in this case, at least 250 ratings).
It computes the average rating for each book.
It sorts the books by average rating, selecting the top 50 books.
It then merges this data with the book details (title, authors, image URLs) to display more relevant information.
Collaborative Filtering Recommender
User and Book Filtering: It filters users who have rated more than 200 books and selects books that have more than 50 ratings.
Pivot Table: A pivot table is created, where books are rows and users are columns, with ratings as values.
Cosine Similarity: The system calculates the cosine similarity between books based on users’ ratings. This measure helps to identify similar books based on user preferences.
Book Recommendation: For a given book, the system finds other books with the highest similarity scores and suggests them to the user.
Recommendation Function
The function recommend(book_name) provides book recommendations for a given book title:

It checks if the book exists in the dataset.
It finds the corresponding book in the pivot table, calculates similarity scores for other books, and returns the top similar books with details such as title, author, and image URL.
Pickling Data
To ensure faster future use and avoid recalculating the recommendations each time, the following objects are saved to disk using Python’s pickle module:

popular_df: DataFrame containing popular books based on ratings.
pt: Pivot table of books and users, used for collaborative filtering.
books.pkl: Cleaned and de-duplicated books dataset.
similarity_scores.pkl: Array containing the cosine similarity scores between books.
Installation and Setup
Requirements
To run this recommender system, you need the following libraries installed:

numpy
pandas
sklearn
pickle (part of the Python standard library)
You can install the required libraries using pip if they are not already installed:

bash
Copy code
pip install numpy pandas scikit-learn
File Structure
Ensure the following files are in the working directory:

books.csv: Contains the book data.
users.csv: Contains user data.
ratings.csv: Contains the ratings given by users to books.
app.py (or your script): Contains the recommender system logic and function.
Running the Code
Prepare the Data: Ensure that you have the books.csv, users.csv, and ratings.csv files ready and properly formatted.

Run the Script: Execute the script (e.g., python app.py) to generate recommendations.

Test the Recommendation Function: To test the system for a specific book, simply call the recommend(book_name) function with a book title. For example:


print(recommend('2024'))
This will print the top 4 books similar to "1984" based on user ratings and preferences.

Saving and Loading Data
The recommendation data is saved as pickle files (popular.pkl, pt.pkl, books.pkl, and similarity_scores.pkl) for later use. These files allow you to load pre-computed data to save time.

To load the pickle files, use:

python
Copy code
popular_df = pickle.load(open('popular.pkl', 'rb'))
pt = pickle.load(open('pt.pkl', 'rb'))
books = pickle.load(open('books.pkl', 'rb'))
similarity_scores = pickle.load(open('similarity_scores.pkl', 'rb'))
Example Output
Here is an example of the output for a recommendation query:

python
Copy code
Recommendations for '1984': [['Brave New World', 'Aldous Huxley', 'url1'], 
                             ['Animal Farm', 'George Orwell', 'url2'], 
                             ['Fahrenheit 451', 'Ray Bradbury', 'url3'], 
                             ['The Handmaid\'s Tale', 'Margaret Atwood', 'url4']]
This output represents a list of recommended books with their titles, authors, and image URLs.

Conclusion
This book recommender system provides both popularity-based and collaborative filtering-based recommendations to users. It uses basic machine learning concepts like cosine similarity to find similar books based on user ratings. By saving pre-processed data using pickle, the system ensures efficiency in providing book recommendations without having to recalculate every time.