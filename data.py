import pandas as pd
import MySQLdb

# Connect to MySQL Database
def connect_to_db():
    return MySQLdb.connect(host="localhost", user="root", password="", db="mkudb")

# Fetch data from the database and store as CSV files
def fetch_data():
    conn = connect_to_db()
    cursor = conn.cursor()
    
    # Query to fetch books
    books_query = """
    SELECT id AS book_id, title, authors, book_url, image_url, description, created_at, pdf_file_path, epub_file_path, mobi_file_path
    FROM books
    """
    books_df = query_and_save_to_csv(cursor, books_query, "books.csv")
    
    # Query to fetch users
    users_query = """
    SELECT id AS user_id, username, email, password, name, role, department, confirmed, confirmation_token, is_active
    FROM users
    """
    users_df = query_and_save_to_csv(cursor, users_query, "users.csv")
    
    # Query to fetch ratings
    ratings_query = """
    SELECT id, user_id, book_id, rating, created_at, updated_at, google_id, book_title
    FROM ratings
    """
    ratings_df = query_and_save_to_csv(cursor, ratings_query, "ratings.csv")
    
    cursor.close()
    conn.close()
    return books_df, users_df, ratings_df

# Function to query the database and save results to a CSV file
def query_and_save_to_csv(cursor, query, filename):
    cursor.execute(query)
    result = cursor.fetchall()
    df = pd.DataFrame(result, columns=[desc[0] for desc in cursor.description])
    df.to_csv(filename, index=False)  # Save to CSV file
    print(f"Data saved to {filename}")
    return df

# Run the function to fetch data and save to CSV files
if __name__ == "__main__":
    fetch_data()  # Fetch data and save it into books.csv, users.csv, and ratings.csv
