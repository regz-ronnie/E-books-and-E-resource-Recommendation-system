import MySQLdb

def get_db_connection():
    db = MySQLdb.connect(
        host='localhost',
        user='root',          # Replace with your MySQL username
        password='',          # Replace with your MySQL password
        database='mkudb'      # Replace with your database name
    )
    return db

def execute_query(query, params=None):
    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute(query, params or ())
        result = cursor.fetchall()  # or cursor.fetchone() for single row
        db.commit()  # For write queries (INSERT, UPDATE, DELETE)
        return result
    except Exception as e:
        db.rollback()  # In case of error, rollback any changes
        print(f"Error executing query: {e}")
    finally:
        cursor.close()
        db.close()

# Example usage
query = "SELECT * FROM books"
books = execute_query(query)

