from flask import Flask, render_template, redirect, url_for, flash, request, session,g
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from db import get_db_connection
import smtplib
import secrets
import os
import MySQLdb

from email.mime.text import MIMEText
from functools import wraps

app = Flask(__name__)
app.secret_key = 'secret_key'
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Set the allowed file extensions for uploads
ALLOWED_EXTENSIONS = {'pdf', 'epub', 'txt'}
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# User class for flask-login integration
class User:
    def __init__(self, id, email, password, name, role, department):
        self.id = id
        self.email = email
        self.password = password
        self.name = name
        self.role = role
        self.department = department

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def get_id(self):
        return str(self.id)
@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # First, check in the 'admin' table
    cursor.execute('SELECT id, email, password, name, role, department FROM admin WHERE id = %s', (user_id,))
    user = cursor.fetchone()

    if not user:
        # If not found, check in the 'users' table
        cursor.execute('SELECT id, email, password, name, role, department FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()

    conn.close()

    if user:
        # Ensure all attributes are passed correctly
        return User(id=user[0], email=user[1], password=user[2], name=user[3], role=user[4], department=user[5])
    return None


import smtplib
from email.mime.text import MIMEText

# Function to send the confirmation email
def send_confirmation_email(recipient_email, token):
    # SMTP server configuration
    smtp_server = 'smtp.gmail.com'
    port = 587  # TLS port

    # Hardcoded Gmail credentials (Replace with your own Gmail account details)
    sender_email = 'ronalkipro18@gmail.com'  # Replace with your Gmail email address
    sender_password = 'dwdb hprw nhbe qhhf'  # Replace with your Gmail app password or regular password

    if not sender_email or not sender_password:
        print("Error: Gmail credentials are not set.")
        return

    # Construct the email content
    confirmation_link = f'http://127.0.0.1:5000/confirm/{token}'  # Change to production URL
    email_body = f'Please confirm your account by clicking the link: {confirmation_link}'
    
    msg = MIMEText(email_body)
    msg['Subject'] = 'Confirm Your Account'
    msg['From'] = sender_email
    msg['To'] = recipient_email

    # Send the email
    try:
        with smtplib.SMTP(smtp_server, port) as server:
            server.starttls()  # Start TLS encryption
            server.login(sender_email, sender_password)  # Login to the SMTP server
            server.send_message(msg)  # Send the email
            print("Confirmation email sent successfully.")
            return "Email sent successfully"
    except Exception as e:
        print(f"Error sending email: {e}")
        return f"Error: {str(e)}"

# Example usage
if __name__ == "__main__":
    recipient_email = 'ronalkipro18@gmail.com'  # Replace with the recipient's email address
    token = 'sample_token_123'  # Replace with the actual token
    conf_email = send_confirmation_email(recipient_email, token)
    print("Confirmation email status:", conf_email)

# Check if a file is allowed
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Decorator for admin access
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for('browse_books'))  # Redirect to student dashboard if not admin
        return f(*args, **kwargs)
    return decorated_function

# Routes

@app.route('/')
def home():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch statistics
    cursor.execute("SELECT COUNT(*) AS books_count FROM books")
    books_count = cursor.fetchone()['books_count']

    cursor.execute("SELECT COUNT(*) AS users_count FROM users")
    users_count = cursor.fetchone()['users_count']

    cursor.execute("SELECT SUM(count) AS downloads_count FROM downloads")
    downloads_count = cursor.fetchone()['downloads_count'] or 0

    # Close the connection
    cursor.close()
    conn.close()

    # Render the template with statistics
    return render_template('home.html', 
                           books_count=books_count, 
                           users_count=users_count, 
                           downloads_count=downloads_count)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Get form inputs
        name = request.form['name'].strip()
        email = request.form['email'].strip()
        password = request.form['password'].strip()
        role = request.form['role'].strip()
        department = request.form['department'].strip()

        # Validation
        if not name or not email or not password or not role or not department:
            flash('All fields are required.', 'danger')
            return render_template('register.html')

        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'danger')
            return render_template('register.html')

        if '@' not in email or '.' not in email:
            flash('Invalid email address.', 'danger')
            return render_template('register.html')

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # Check for duplicate email
            cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
            if cursor.fetchone():
                flash('Email is already registered. Please log in.', 'warning')
                return redirect(url_for('login'))

            # Hash password and generate token
            hashed_password = generate_password_hash(password)
            token = secrets.token_urlsafe(16)

            # Insert user into the database
            cursor.execute(
                'INSERT INTO users (name, email, password, role, department, confirmed, confirmation_token) '
                'VALUES (%s, %s, %s, %s, %s, %s, %s)',
                (name, email, hashed_password, role, department, False, token)
            )
            conn.commit()

            # Send confirmation email
            send_confirmation_email(email, token)
            flash('Registration successful! Check your email to confirm your account.', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            conn.rollback()
            flash(f'Registration failed: {str(e)}', 'danger')

        finally:
            conn.close()

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check in the admin table
        cursor.execute('SELECT id, email, password, name, role, department FROM admin WHERE email = %s', (email,))
        admin = cursor.fetchone()

        if admin and admin[2] == password:  # Direct password comparison for admin (no hash)
            print("Admin login successful")
            user_obj = User(id=admin[0], email=admin[1], password=admin[2], name=admin[3], role=admin[4], department=admin[5])
            login_user(user_obj)
                
            session['user_id'] = user_obj.id  # Store user id in session
            session['user_name'] = user_obj.name  # Store user name in session
            session['role'] = user_obj.role  # Store role in session
            flash('Admin login successful!', 'success')
            return redirect(url_for('admin_dashboard'))  # Ensure this route exists

        # Check in the users table
        cursor.execute('SELECT id, email, password, name, role, department FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()

        if user and check_password_hash(user[2], password):  # Validate hashed password for users
            print("User login successful")
            user_obj = User(id=user[0], email=user[1], password=user[2], name=user[3], role=user[4], department=user[5])
            login_user(user_obj)
                
            session['user_id'] = user_obj.id  # Store user id in session
            session['user_name'] = user_obj.name  # Store user name in session
            session['role'] = user_obj.role  # Store role in session
            flash('Login successful!', 'success')
            if user[4] == 'student':  # Correct role index after query
                return redirect(url_for('browse_books'))
            elif user[4] == 'lecturer':  # Correct role index after query
                return redirect(url_for('lecturer_dashboard'))
            else:
                flash('Unrecognized role. Please contact support.', 'warning')
                return redirect(url_for('login'))

        flash('Invalid email or password.', 'danger')
        conn.close()
        return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/books')
@login_required
def books():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM books')
    books = cursor.fetchall()
    conn.close()
    return render_template('books.html', books=books)

@app.route('/book/new', methods=['GET', 'POST'])
@admin_required
@login_required
def new_book():
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['authors']
        book_url = request.form['book_url']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO books (title, authors, book_url) VALUES (%s, %s, %s)', (title, author, book_url))
            conn.commit()
            flash('Book created successfully!', 'success')
            return redirect(url_for('books'))
        except Exception as e:
            conn.rollback()
            flash(f'Failed to create book: {str(e)}', 'danger')
        finally:
            conn.close()
    return render_template('book_form.html')

@app.route('/book/<int:book_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_book(book_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM books WHERE id = %s', (book_id,))
    book = cursor.fetchone()

    if not book:
        flash('Book not found!', 'danger')
        return redirect(url_for('books'))

    if request.method == 'POST':
        # Safely get form values using .get() and handle missing fields
        title = request.form.get('title')
        authors = request.form.get('authors')
        genre = request.form.get('book_url')

        # Basic validation to check if the required fields are filled
        if not title or not authors or not genre:
            flash('All fields are required!', 'danger')
            return render_template('book_form.html', book=book)

        try:
            # Update the book details in the database
            cursor.execute(
                'UPDATE books SET title = %s, authors = %s, book_url = %s WHERE id = %s',
                (title, authors, genre, book_id)
            )
            conn.commit()
            flash('Book updated successfully!', 'success')
            return redirect(url_for('books'))
        except Exception as e:
            conn.rollback()
            flash(f'Failed to update book: {str(e)}', 'danger')

    conn.close()
    return render_template('book_form.html', book=book)


@app.route('/book/<int:book_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_book(book_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM books WHERE id = %s', (book_id,))
        conn.commit()
        flash('Book deleted successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Failed to delete book: {str(e)}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('books'))

import mysql.connector

def get_db_connection():
    connection = mysql.connector.connect(
        host="localhost",
        user="root",  # Use your MySQL username
        password="",  # Use your MySQL password
        database="mkudb"  # Your database name
    )
    return connection
@app.route('/recommendations')
@login_required
@admin_required
def recommendations():
    conn = get_db_connection()
    
    # Use context manager to handle cursor automatically
    with conn.cursor(dictionary=True) as cursor:
        # Get most popular books based on average ratings, rating count, and favorite count
        cursor.execute('''
            SELECT books.id, books.title, 
                   AVG(ratings.rating) AS avg_rating, 
                   COUNT(ratings.id) AS rating_count,
                   IFNULL(COUNT(favorites.id), 0) AS favorite_count
            FROM books
            LEFT JOIN ratings ON books.id = ratings.book_id
            LEFT JOIN favorites ON books.id = favorites.book_id
            GROUP BY books.id
            ORDER BY avg_rating DESC
            LIMIT 5
        ''')
        popular_books = cursor.fetchall()

        # Get most rated books (top 5 by number of ratings)
        cursor.execute('''
            SELECT books.id, books.title, 
                   AVG(ratings.rating) AS avg_rating, 
                   COUNT(ratings.id) AS rating_count,
                   IFNULL(COUNT(favorites.id), 0) AS favorite_count
            FROM books
            LEFT JOIN ratings ON books.id = ratings.book_id
            LEFT JOIN favorites ON books.id = favorites.book_id
            GROUP BY books.id
            ORDER BY rating_count DESC
            LIMIT 5
        ''')
        most_rated_books = cursor.fetchall()

        # Get most favorited books (top 5 by number of favorites)
        cursor.execute('''
            SELECT books.id, books.title, 
                   AVG(ratings.rating) AS avg_rating, 
                   COUNT(ratings.id) AS rating_count,
                   IFNULL(COUNT(favorites.id), 0) AS favorite_count
            FROM books
            LEFT JOIN ratings ON books.id = ratings.book_id
            LEFT JOIN favorites ON books.id = favorites.book_id
            GROUP BY books.id
            ORDER BY favorite_count DESC
            LIMIT 5
        ''')
        most_favorited_books = cursor.fetchall()

    # Close connection (optional, since we are using the 'with' block for cursor)
    conn.close()

    return render_template('recommendations.html', 
                           popular_books=popular_books, 
                           most_rated_books=most_rated_books, 
                           most_favorited_books=most_favorited_books)


import os

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/upload', methods=['GET', 'POST'])
@login_required
@admin_required
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)

        file = request.files['file']
        title = request.form['title']
        authors = request.form['authors']
        id = request.form['id']

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                cursor.execute(
                    'INSERT INTO books (id,title, authors , file_path) VALUES (%s, %s, %s, %s)',
                    (id,title, authors, filename)
                )
                conn.commit()
                flash('File uploaded and book entry created!', 'success')
            except Exception as e:
                conn.rollback()
                flash(f'Failed to upload file and create entry: {str(e)}', 'danger')
            finally:
                conn.close()
            return redirect(url_for('manage_books'))
        else:
            flash('Allowed file types are pdf, epub, txt.', 'danger')
    return render_template('upload.html')
@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    # Connect to the MySQL database
    conn = get_db_connection()
    if conn is None:
        return "Failed to connect to the database."

    cursor = conn.cursor()

    # Query for total users count
    cursor.execute('SELECT COUNT(*) AS user_count FROM users')
    user_count = cursor.fetchone()[0]

    # Query for total books count
    cursor.execute('SELECT COUNT(*) AS book_count FROM books')
    book_count = cursor.fetchone()[0]

    # Query for active users count
    cursor.execute('SELECT COUNT(*) AS active_users FROM users WHERE is_active = TRUE')
    active_users = cursor.fetchone()[0]

    # Query for unread messages count
    cursor.execute("SELECT COUNT(*) FROM messages WHERE status = 'unread'")
    unread_count = cursor.fetchone()[0]

    # Close the cursor and connection
    cursor.close()
    conn.close()

    # Messages for display (optional)
    user_message = "Total registered users on the platform."
    book_message = "Total books available in the catalog."
    active_message = "Currently active users engaging with the platform."

    # Pass counts and messages to the admin dashboard template
    return render_template(
        'admin_dashboard.html',
        user_count=user_count,
        book_count=book_count,
        active_users=active_users,
        unread_count=unread_count,
        user_message=user_message,
        book_message=book_message,
        active_message=active_message
    )

@app.route('/about')
def about():
    return render_template('about.html')
@app.route('/contact')
def contact():
    return render_template('contact.html')
@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')
@app.route('/manage_users')
@login_required
def manage_users():
    # Fetch all users except admins from the database
    conn = get_db_connection()  # Get the database connection
    cursor = conn.cursor()
    
    # Query to fetch all users, excluding those with the 'Admin' role
    cursor.execute('SELECT id, email, name, role, department FROM users WHERE role != "Admin"')
    
    users = cursor.fetchall()  # Fetch all users excluding admin
    conn.close()  # Always close the connection after use
    
    return render_template('manage_users.html', users=users)


    return render_template('manage_users.html', users=users)
@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    # Fetch the user data based on the user_id
    cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
    user = cursor.fetchone()

    if request.method == 'POST':
        # Handle form submission (e.g., update user data)
        name = request.form['name']
        email = request.form['email']
        role = request.form['role']
        cursor.execute('UPDATE users SET name = %s, email = %s, role = %s WHERE id = %s',
                       (name, email, role, user_id))
        connection.commit()
        return redirect(url_for('manage_users'))

    cursor.close()
    connection.close()

    # Render the edit_user.html template with user data
    return render_template('edit_user.html', user=user)

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    # Perform delete query
    try:
        cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
        connection.commit()  # Commit the transaction
    except MySQLdb.connector.Error as err:
        print(f"Error: {err}")
    finally:
        cursor.close()
        connection.close()  # Close cursor and connection

    return redirect(url_for('manage_users'))


@app.route('/manage_books', methods=['GET', 'POST'])
@login_required
def manage_books():
    page = request.args.get('page', 1, type=int)  # Get the current page number
    search = request.args.get('search', '')  # Default search query (GET request)

    # Handle POST requests for search functionality
    if request.method == 'POST':
        search = request.form.get('search', '')  # Get the search term from the form

    # Get the database connection
    conn = get_db_connection()
    cursor = conn.cursor()

    # Query the database with search and pagination
    if search:
        cursor.execute(
            'SELECT * FROM books WHERE title LIKE %s OR authors LIKE %s LIMIT 10 OFFSET %s',
            ('%' + search + '%', '%' + search + '%', (page - 1) * 10)
        )
    else:
        cursor.execute('SELECT * FROM books LIMIT 10 OFFSET %s', ((page - 1) * 10,))

    books = cursor.fetchall()
    conn.close()

    # Get total number of books for pagination
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM books')
    total_books = cursor.fetchone()[0]
    conn.close()

    # Calculate number of pages
    pages = (total_books // 10) + (1 if total_books % 10 > 0 else 0)

    return render_template(
        'manage_books.html', 
        books=books, 
        pages=pages, 
        current_page=page, 
        search=search
    )

#AIzaSyDgJwDoh8-N0WGB8m1pdDb4uS_dz-CSIV4
import requests
from flask import flash, render_template, request, send_file
from flask_login import login_required, current_user
from fpdf import FPDF
from urllib3.exceptions import NewConnectionError, NameResolutionError
import os

# Your Google Books API URL
GOOGLE_BOOKS_API_URL = "https://www.googleapis.com/books/v1/volumes"
API_KEY = "AIzaSyDgJwDoh8-N0WGB8m1pdDb4uS_dz-CSIV4"  # Replace this with your actual API key

@app.route('/browse_books', methods=['GET'])
@login_required
def browse_books():
    search_query = request.args.get('search', 'python')
    max_results = 40
    current_page = int(request.args.get('page', 1))
    pdf_filename = None  # Ensure pdf_filename is initialized

    try:
        # Make the request to the Google Books API with API key
        response = requests.get(f"{GOOGLE_BOOKS_API_URL}?q={search_query}&maxResults={max_results}&key=AIzaSyDgJwDoh8-N0WGB8m1pdDb4uS_dz-CSIV4")
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx, 5xx)
        books_data = response.json()

        books = []
        for index, item in enumerate(books_data.get('items', [])):
            volume_info = item.get('volumeInfo', {})
            title = volume_info.get('title', 'No title available')
            authors = volume_info.get('authors', ['No authors available'])
            image_url = volume_info.get('imageLinks', {}).get('thumbnail', '')
            book_url = volume_info.get('infoLink', '')

            # Fetch database connection
            conn = get_db_connection()
            cursor = conn.cursor(buffered=True)
            
            
            # Check if the book already exists in the database by its URL
            cursor.execute("SELECT id FROM books WHERE book_url = %s", (book_url,))
            book_in_db = cursor.fetchone()
            
            # If the book doesn't exist, insert it
            if not book_in_db:
                cursor.execute("INSERT INTO books (title, authors, image_url, book_url) VALUES (%s, %s, %s, %s)",
                               (title, ', '.join(authors), image_url, book_url))
                conn.commit()
                book_id = cursor.lastrowid  # Get the ID of the inserted book
            else:
                book_id = book_in_db[0]  # Use the existing book ID
            
            # Check if the book is already a favorite for the current user
            cursor.execute("SELECT * FROM favorites WHERE user_id = %s AND book_id = %s", (current_user.id, book_id))
            is_favorite = cursor.fetchone() is not None
            
            # Close cursor after the operations
            cursor.close()

            # Create book dictionary and add it to the list
            book = {
                'id': book_id,  # Use the book's ID from the database
                'title': title,
                'authors': authors,
                'image_url': image_url,
                'book_url': book_url,
                'is_favorite': is_favorite
            }
            books.append(book)

        # Calculate the number of pages for pagination
        total_books = len(books_data.get('items', []))
        pages = (total_books // max_results) + (1 if total_books % max_results > 0 else 0)

        # Generate PDF from book data if requested
        if request.args.get('pdf', 'false') == 'true':
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()

            # Add content to the PDF
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(200, 10, txt=f"Book Search Results for '{search_query}'", ln=True)

            # Add books to the PDF
            for book in books:
                pdf.ln(10)  # Add a new line
                pdf.cell(200, 10, txt=f"Title: {book['title']}", ln=True)
                pdf.cell(200, 10, txt=f"Authors: {', '.join(book['authors'])}", ln=True)
                pdf.cell(200, 10, txt=f"Book URL: {book['book_url']}", ln=True)

            # Set the filename for the PDF
            pdf_filename = f'books_search_results_{search_query}.pdf'
            pdf.output(os.path.join('static', pdf_filename))  # Save the PDF to the 'static' folder

    except requests.exceptions.RequestException as e:
        # Catch all exceptions related to the API request
        flash(f"An error occurred while fetching books: {e}", 'danger')
        books = []
        pages = 1
    except requests.exceptions.HTTPError as e:
        # Handle HTTP-specific errors
        flash(f"HTTP error occurred: {e}", 'danger')
        books = []
        pages = 1
    except requests.exceptions.Timeout:
        # Handle timeout errors
        flash("The request timed out. Please try again later.", 'danger')
        books = []
        pages = 1
    except requests.exceptions.TooManyRedirects:
        # Handle too many redirects error
        flash("Too many redirects occurred. Check the URL or try again later.", 'danger')
        books = []
        pages = 1
    except (NewConnectionError, NameResolutionError) as e:
        # Handle DNS resolution or connection issues
        flash("Failed to resolve the domain or connect to the API. Please check your network connection and try again.", 'danger')
        books = []
        pages = 1
    except Exception as e:
        # Catch any other exceptions
        flash(f"An unexpected error occurred: {e}", 'danger')
        books = []
        pages = 1

    # If PDF was generated, send it for download
    if pdf_filename:
        return send_file(os.path.join('static', pdf_filename), as_attachment=True)

    return render_template('browse_books.html', books=books, search_query=search_query, current_page=current_page, pages=pages)

@app.route('/toggle_favorite', methods=['POST'])
@login_required
def toggle_favorite():
    book_id = request.form.get('book_id')

    # Fetch database connection
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the book is already in the user's favorites
    cursor.execute("SELECT * FROM favorites WHERE user_id = %s AND book_id = %s", (current_user.id, book_id))
    favorite = cursor.fetchone()

    if favorite:
        # If the book is already a favorite, remove it from favorites
        cursor.execute("DELETE FROM favorites WHERE user_id = %s AND book_id = %s", (current_user.id, book_id))
        flash("Book removed from favorites", "info")
    else:
        # Otherwise, add it to favorites
        cursor.execute("INSERT INTO favorites (user_id, book_id) VALUES (%s, %s)", (current_user.id, book_id))
        flash("Book added to favorites", "success")

    conn.commit()
    cursor.close()

    # Redirect back to the referring page or to the browse_books page
    return redirect(request.referrer or url_for('browse_books'))


@app.route('/book_details/<int:book_id>', methods=['GET'])
def book_details(book_id):
    # Fetch book details from the database
    conn = get_db_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)  # Use DictCursor to get results as a dictionary
    cursor.execute('SELECT * FROM books WHERE id = %s', (book_id,))
    book = cursor.fetchone()
    conn.close()

    if book:
        return render_template('book_details.html', book=book)
    else:
        return "Book not found", 404  # You can also render a custom 404 page here
@app.route('/report', methods=['GET'])
def report():
    conn = get_db_connection()
    if conn is None:
        return "Error: Unable to connect to the database", 500

    cursor = conn.cursor()
    
    # Basic counts
    cursor.execute("SELECT COUNT(*) FROM books")
    total_books = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM ratings")
    total_reviews = cursor.fetchone()[0]
    
    # Role-based user count
    cursor.execute("SELECT role, COUNT(*) FROM users GROUP BY role")
    users_per_role = cursor.fetchall()  # [(role, count), ...]

    # Top-rated books (by average rating)
    cursor.execute("""
        SELECT book_id, AVG(rating) AS avg_rating 
        FROM ratings 
        GROUP BY book_id 
        ORDER BY avg_rating DESC 
        LIMIT 5
    """)
    top_rated_books = cursor.fetchall()  # [(book_id, avg_rating), ...]

    # Most reviewed books
    cursor.execute("""
        SELECT book_id, COUNT(*) AS review_count 
        FROM ratings 
        GROUP BY book_id 
        ORDER BY review_count DESC 
        LIMIT 5
    """)
    most_reviewed_books = cursor.fetchall()  # [(book_id, review_count), ...]

    # Average rating distribution
    cursor.execute("""
        SELECT rating, COUNT(*) AS count 
        FROM ratings 
        GROUP BY rating 
        ORDER BY rating
    """)
    rating_distribution = cursor.fetchall()  # [(rating, count), ...]

    # Most favorited books
    cursor.execute("""
        SELECT book_id, COUNT(*) AS favorite_count 
        FROM favorites 
        GROUP BY book_id 
        ORDER BY favorite_count DESC 
        LIMIT 5
    """)
    most_favorited_books = cursor.fetchall()  # [(book_id, favorite_count), ...]

    # Active users by number of ratings
    cursor.execute("""
        SELECT user_id, COUNT(*) AS activity_count 
        FROM ratings 
        GROUP BY user_id 
        ORDER BY activity_count DESC 
        LIMIT 5
    """)
    active_users = cursor.fetchall()  # [(user_id, activity_count), ...]

    cursor.close()
    conn.close()

    # Render the report template with the analytical data
    return render_template(
        'report.html',
        total_books=total_books,
        total_users=total_users,
        total_reviews=total_reviews,
        users_per_role=users_per_role,
        top_rated_books=top_rated_books,
        most_reviewed_books=most_reviewed_books,
        rating_distribution=rating_distribution,
        most_favorited_books=most_favorited_books,
        active_users=active_users
    )



@app.route('/settings')
def settings():
    return render_template('settings.html')
@app.route('/student_settings')
@login_required  # Optional: use if you want only logged-in users to access this page
def student_settings():
    return render_template('student_settings.html', current_user=current_user)
@app.route('/download_book/<int:book_id>')
@login_required
def download_book(book_id):
    # Check if the user is a student
    if current_user.role != 'student':
        flash("Access denied. Only students can download the books.", 'danger')
        return redirect(url_for('home'))  # Redirect to home or any other page
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT title, pdf_file_path FROM books WHERE id = %s', (book_id,))
    book = cursor.fetchone()
    conn.close()
    
    if book:
        title, pdf_file_path = book
        # Check if the file exists
        if os.path.exists(pdf_file_path):
            return send_file(pdf_file_path, as_attachment=True, download_name=f"{title}.pdf", mimetype="application/pdf")
        else:
            flash("PDF file for this book is not available.", 'danger')
    else:
        flash("Book not found.", 'danger')
    
    return redirect('/student_books')  # Redirect back to the student's book page if not found
@app.route('/profile')
@login_required
def profile():
    # Establish a connection to the database
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Check if the current user is an admin
        cursor.execute("SELECT COUNT(*) FROM admin WHERE id = %s", (current_user.id,))
        is_admin = cursor.fetchone()[0] > 0

        if is_admin:
            # Query the admin table for profile information
            cursor.execute("SELECT id, name, email,department FROM admin WHERE id = %s", (current_user.id,))
            admin_data = cursor.fetchone()
            user = {'id': admin_data[0], 'name': admin_data[1], 'email': admin_data[2],'department': admin_data[3]} if admin_data else None

            # Admins may not have favorite books or reading history
            favorite_books = []
            reading_history = []

        else:
            # Query the users table for profile information
            cursor.execute("SELECT id, name, email, department FROM users WHERE id = %s", (current_user.id,))
            user_data = cursor.fetchone()
            user = {'id': user_data[0], 'name': user_data[1], 'email': user_data[2], 'department': user_data[3]} if user_data else None

            # Query to get the user's favorite books
            cursor.execute("""
                SELECT 
                    books.title, 
                    books.authors, 
                    books.created_at, 
                    books.id, 
                    books.image_url, 
                    books.description
                FROM books 
                JOIN favorites ON books.id = favorites.book_id 
                WHERE favorites.user_id = %s
            """, (current_user.id,))
            favorite_books = cursor.fetchall()

            # Format the favorite books data
            favorite_books = [
                {
                    'title': book[0],
                    'authors': book[1],
                    'created_at': book[2].strftime('%B %d, %Y') if book[2] else 'N/A',
                    'id': book[3],
                    'image_url': book[4] if book[4] else 'default_image_url.jpg',
                    'description': book[5] if book[5] else 'No description available'
                }
                for book in favorite_books
            ]

            # Query to get the user's reading history
            cursor.execute("""
                SELECT books.title, books.authors, reading_history.date_accessed 
                FROM reading_history 
                JOIN books ON reading_history.book_id = books.id 
                WHERE reading_history.user_id = %s
                ORDER BY reading_history.date_accessed DESC
            """, (current_user.id,))
            reading_history = cursor.fetchall()

            # Format the reading history data
            reading_history = [
                {
                    'title': history[0],
                    'authors': history[1],
                    'date_accessed': history[2].strftime('%B %d, %Y') if history[2] else 'N/A'
                }
                for history in reading_history
            ]

    except Exception as e:
        # Handle any database errors
        flash(f"An error occurred: {e}", 'danger')
        user, favorite_books, reading_history = None, [], []

    finally:
        # Close the cursor and connection
        cursor.close()
        conn.close()

    # Render the profile template and pass the fetched data
    return render_template(
        'profile.html', 
        user=user, 
        favorite_books=favorite_books, 
        reading_history=reading_history
    )


@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    new_name = request.form.get('name')
    new_email = request.form.get('email')

    if new_name and new_email:
        # Establish a connection to the database
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # Update user information in the database
            cursor.execute("UPDATE users SET name = %s, email = %s WHERE id = %s", (new_name, new_email, current_user.id))
            conn.commit()
            flash('Profile updated successfully!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Failed to update profile: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()

    else:
        flash('Both name and email are required!', 'danger')
    
    return redirect(url_for('profile'))

@app.route('/update_password', methods=['POST'])
@login_required
def update_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Verify current password
    cursor.execute("SELECT password FROM users WHERE id = %s", (current_user.id,))
    stored_password = cursor.fetchone()

    if stored_password and check_password_hash(stored_password[0], current_password):
        hashed_new_password = generate_password_hash(new_password)

        try:
            # Update password in the database
            cursor.execute("UPDATE users SET password = %s WHERE id = %s", (hashed_new_password, current_user.id))
            conn.commit()
            flash('Password updated successfully!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Failed to update password: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()
    else:
        flash('Current password is incorrect!', 'danger')

    return redirect(url_for('profile'))

@app.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Delete user from the database
        cursor.execute("DELETE FROM users WHERE id = %s", (current_user.id,))
        conn.commit()
        flash('Account deleted successfully!', 'info')
        
        # Log out the user
        # Optionally use Flask-Login to log the user out:
        # logout_user()

    except Exception as e:
        conn.rollback()
        flash(f'Failed to delete account: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('logout'))
import requests

# Define the function to fetch books from Google Books API
def fetch_books_from_google(query, start_index=0, max_results=10):
    api_url = f"https://www.googleapis.com/books/v1/volumes?q={query}&startIndex={start_index}&maxResults={max_results}"
    response = requests.get(api_url)
    data = response.json()
    
    books = []
    for item in data.get('items', []):
        volume_info = item.get('volumeInfo', {})
        book = {
            'title': volume_info.get('title'),
            'authors': ', '.join(volume_info.get('authors', [])),
            'published_date': volume_info.get('publishedDate'),
            'genre': ', '.join(volume_info.get('categories', [])),
            'image_url': volume_info.get('imageLinks', {}).get('thumbnail'),
            'description': volume_info.get('description'),
        }
        books.append(book)
    
    return books
def save_books_to_db(books):
    connection = get_db_connection()
    cursor = connection.cursor()

    for book in books:
        query = """
            INSERT INTO books (title, authors, published_date, genre, image_url, description)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        data = (book['title'], book['authors'], book['published_date'], book['genre'], book['image_url'], book['description'])
        cursor.execute(query, data)

    connection.commit()
    cursor.close()
    connection.close()

@app.route('/rate_book', methods=['POST'])
@login_required
def rate_book():
    book_id = request.form.get('book_id')
    rating = request.form.get('rating')
    user_id = current_user.id  # Assuming current_user is set up through Flask-Login

    if not book_id or not rating:
        flash("Book ID and rating are required.", "danger")
        return redirect(url_for('browse_books'))
    
    # Get database connection
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if the user has already rated this book
        cursor.execute(
            "SELECT * FROM ratings WHERE user_id = %s AND book_id = %s",
            (user_id, book_id)
        )
        existing_rating = cursor.fetchone()

        if existing_rating:
            flash("You have already rated this book.", "warning")
        else:
            # Save the new rating if it doesn't exist
            cursor.execute(
                "INSERT INTO ratings (book_id, user_id, rating) VALUES (%s, %s, %s)",
                (book_id, user_id, rating)
            )
            conn.commit()
            flash("Rating submitted successfully!", "success")
    
    except Exception as e:
        flash(f"An error occurred: {e}", "danger")
    
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('browse_books'))
import requests
from flask import render_template, flash, redirect, url_for, send_file
from werkzeug.utils import secure_filename
import os

# Assuming that you have a Google Books API key
GOOGLE_BOOKS_API_URL = "https://www.googleapis.com/books/v1/volumes"

@app.route('/read/<book_title>')
@login_required
def read_book(book_title):
    # Prepare the Google Books API request
    params = {
        'q': book_title,
        'maxResults': 1
    }

    try:
        # Send request to Google Books API
        response = requests.get(GOOGLE_BOOKS_API_URL, params=params)
        response.raise_for_status()  # Raise an error for bad responses

        # Parse the API response JSON
        data = response.json()
        
        # Check if there are any books returned
        if 'items' not in data:
            flash('Book not found.', 'danger')
            return redirect(url_for('base'))

        # Get the first book from the response
        book = data['items'][0]
        
        # Get the book URL or PDF download link (if available)
        book_info = book.get('volumeInfo', {})
        book_title = book_info.get('title', 'Unknown Title')
        book_url = book_info.get('previewLink', '')  # URL to book preview (if available)
        pdf_link = None

        # Check if the book has a PDF link (Google Books API sometimes provides PDF download links)
        if 'accessInfo' in book and 'pdf' in book['accessInfo']['viewability']:
            pdf_link = book['accessInfo'].get('pdf', {}).get('downloadLink', None)

        # If PDF link is available, download the PDF and serve it
        if pdf_link:
            # Download the PDF file to serve it directly (you may want to cache it on your server)
            pdf_response = requests.get(pdf_link)
            pdf_response.raise_for_status()  # Check if the PDF download is successful
            return send_file(
                pdf_response.content,
                as_attachment=True,
                download_name=f"{book_title}.pdf",
                mimetype="application/pdf"
            )

        # If no PDF available, provide a download link to the book preview URL
        elif book_url:
            flash('Currently, we can only read PDF files directly. Click below to view the book preview.', 'info')
            return render_template('download_book.html', book_url=book_url, book_title=book_title)
        else:
            flash('No preview or download link available for this book.', 'danger')
            return redirect(url_for('browse_books'))

    except requests.exceptions.RequestException as e:
        flash(f"An error occurred while fetching the book: {e}", 'danger')
        return redirect(url_for('base'))



@app.route('/upload_profile_picture', methods=['POST'])
@login_required
def upload_profile_picture():
    if 'file' not in request.files:
        flash('No file part', 'danger')
        return redirect(request.url)
    
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(request.url)
    
    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    
    # Update database with the file path
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET profile_picture = %s WHERE id = %s', (file_path, current_user.id))
    conn.commit()
    cursor.close()
    conn.close()

    flash('Profile picture uploaded successfully!', 'success')
    return redirect(url_for('profile'))
from flask import request, redirect, url_for, flash
import os
import MySQLdb

@app.route('/upload_book', methods=['POST'])
@admin_required
def upload_book():
    # Get form data
    title = request.form['title']
    author = request.form['author']
    description = request.form.get('description', '')
    
    # Handle cover image upload
    cover_image = request.files.get('cover_image')
    cover_image_filename = None
    if cover_image:
        cover_image_filename = os.path.join('static/images', cover_image.filename)
        cover_image.save(cover_image_filename)
    
    # Handle book file upload
    book_file = request.files.get('book_file')
    book_filename = None
    if book_file:
        # Ensure the 'static/books' directory exists
        books_directory = os.path.join('static', 'books')
        if not os.path.exists(books_directory):
            os.makedirs(books_directory)  # Create the directory if it doesn't exist
        
        # Save the uploaded file in the 'static/books' directory
        book_filename = os.path.join(books_directory, book_file.filename)
        book_file.save(book_filename)
    
    # Establish DB connection
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Insert book data into the database
    try:
        cursor.execute("""
            INSERT INTO books (title, authors, description, image_url, pdf_file_path)
            VALUES (%s, %s, %s, %s, %s)
        """, (title, author, description, cover_image_filename, book_filename))
        
        conn.commit()  # Commit the transaction
        
        flash('Book uploaded successfully!')
        return redirect(url_for('book_library'))
    except Exception as e:
        conn.rollback()  # Rollback in case of error
        flash(f"Error uploading book: {str(e)}")
        return redirect(url_for('book_library'))
    finally:
        cursor.close()
        conn.close()
@app.route('/book_library')
def book_library():
    # Assuming you're using a MySQL database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM books")  # Adjust your query to match your table
    books = cursor.fetchall()  # This should return a list of book records
    cursor.close()
    conn.close()
    
    return render_template('book_library.html', books=books)

@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        role = request.form['role']
        department = request.form['department']
        password = request.form['password']

        # Hash the password before storing it
        hashed_password = generate_password_hash(password)

        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Insert the new user into the appropriate table (users or admin, depending on the role)
        if role == 'Admin':
            cursor.execute('INSERT INTO admin (name, email, password, role, department) VALUES (%s, %s, %s, %s, %s)', 
                           (name, email, hashed_password, role, department))
        else:
            cursor.execute('INSERT INTO users (name, email, password, role, department) VALUES (%s, %s, %s, %s, %s)', 
                           (name, email, hashed_password, role, department))

        conn.commit()
        conn.close()

        flash('User added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))  # Or another page as appropriate

    return render_template('add_user.html')

@app.route('/student_books', methods=['GET'])
@login_required
def student_books():
    # Only allow access if the user is a student
    if current_user.role != 'student':
        flash("Access denied. This page is only for students.", 'danger')
        return redirect(url_for('home'))  # Redirect to home or any other page
    
    # Get the search term from the query parameters
    search_term = request.args.get('search', '').strip()

    # Build the query
    query = 'SELECT * FROM books WHERE pdf_file_path IS NOT NULL AND pdf_file_path != ""'
    
    # Add search conditions if a search term is provided
    if search_term:
        query += " AND (title LIKE %s OR authors LIKE %s)"
        search_term = f"%{search_term}%"
    
    conn = get_db_connection()
    cursor = conn.cursor()

    # Execute the query with the search term
    cursor.execute(query, (search_term, search_term) if search_term else ())
    books = cursor.fetchall()
    conn.close()

    return render_template('student_books.html', books=books)

@app.route('/view_pdf/<int:book_id>')
@login_required
def view_pdf(book_id):
    # Check if the user is a student
    if current_user.role != 'student':
        flash("Access denied. Only students can view the books.", 'danger')
        return redirect(url_for('home'))  # Redirect to home or any other page

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT title, pdf_file_path FROM books WHERE id = %s', (book_id,))
    book = cursor.fetchone()
    conn.close()
    
    if book:
        title, pdf_file_path = book
        # Check if the file exists
        if os.path.exists(pdf_file_path):
            return send_file(pdf_file_path, mimetype="application/pdf")
        else:
            flash("PDF file for this book is not available.", 'danger')
    else:
        flash("Book not found.", 'danger')
    
    return redirect('/student_books')  # Redirect back to the student's book page if not found
from flask import Flask, request, jsonify
from flask_login import login_required, current_user, login_user
import MySQLdb
from datetime import datetime

# Route for booking a book
@app.route('/book/<int:book_id>', methods=['POST'])
@login_required  # Ensure that the user is logged in
def book_book(book_id):
    # Get a database connection
    conn = get_db_connection()
    
    cursor = conn.cursor()

    # Check if the book exists
    cursor.execute("SELECT * FROM books WHERE id = %s", (book_id,))
    book = cursor.fetchone()

    if not book:
        return jsonify({'success': False, 'message': 'Book not found.'})

    # Check if the student has already booked the book
    cursor.execute("SELECT * FROM bookings WHERE book_id = %s AND student_id = %s AND status = 'booked'", (book_id, current_user.id))
    existing_booking = cursor.fetchone()

    if existing_booking:
        return jsonify({'success': False, 'message': 'You have already booked this book.'})

    # Create a new booking
    booking_date = datetime.utcnow()
    cursor.execute(
        "INSERT INTO bookings (student_id, book_id, booking_date, status) VALUES (%s, %s, %s, 'booked')",
        (current_user.id, book_id, booking_date)
    )
    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({'success': True, 'message': 'Book successfully booked.'})

# Route for admin to monitor bookings
@app.route('/admin/bookings')
@login_required
@admin_required# Ensure that the user is logged in
def admin_bookings():
   
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch all bookings for admin monitoring
    cursor.execute("SELECT b.id, u.name, bk.title, b.booking_date, b.status "
                   "FROM bookings b "
                   "JOIN users u ON b.student_id = u.id "
                   "JOIN books bk ON b.book_id = bk.id")
    bookings = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('admin_bookings.html', bookings=bookings)
@app.route('/cancel_booking/<int:booking_id>', methods=['POST'])
def cancel_booking(booking_id):
    con = get_db_connection()
    cursor = con.cursor()

    try:
        # Check if the booking exists and its status is not already 'Canceled'
        cursor.execute("SELECT * FROM bookings WHERE id = %s", (booking_id,))
        booking = cursor.fetchone()
        
        if not booking:
            return jsonify(success=False, message="Booking not found"), 404

        if booking['status'] == 'Canceled':
            return jsonify(success=False, message="Booking is already canceled"), 400
        
        # Update the status to 'Canceled'
        cursor.execute("UPDATE bookings SET status = 'Canceled' WHERE id = %s", (booking_id,))
        con.commit()

        return jsonify(success=True, message="Booking successfully canceled")
    
    except Exception as e:
        con.rollback()  # Rollback transaction in case of error
        return jsonify(success=False, error=str(e)), 500
    
    finally:
        cursor.close()  # Ensure the cursor is closed after execution
        con.close()  # Ensure the database connection is closed after execution

from flask import request, redirect, url_for, flash
@app.route('/update_booking/<int:booking_id>', methods=['POST'])
def update_booking(booking_id):
    new_status = request.form['new_status']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE bookings SET status = %s WHERE id = %s", (new_status, booking_id))
        conn.commit()

        # If the booking is accepted, allow the student to access the book
        if new_status == 'Accepted':
            flash('Booking successfully accepted. Student can now access the book.', 'success')
        else:
            flash('Booking status updated.', 'info')
    except Exception as e:
        conn.rollback()
        flash('Error updating the booking. ' + str(e), 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('admin_bookings'))
@app.route('/access_book/<int:booking_id>', methods=['GET'])
def access_book(booking_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT status, book_id FROM bookings WHERE id = %s", (booking_id,))
        booking = cursor.fetchone()

        if booking and booking[0] == 'Accepted':
            # Allow access to the book
            book_id = booking[1]
            cursor.execute("SELECT title, author FROM books WHERE id = %s", (book_id,))
            book = cursor.fetchone()
            if book:
                # Book found, display or allow download (customize this part as needed)
                flash(f'You are allowed to access the book "{book[0]}" by {book[1]}', 'success')
                return render_template('book_access.html', book=book)
            else:
                flash('Book not found.', 'error')
        else:
            flash('Booking is not accepted. You cannot access the book.', 'error')
    except Exception as e:
        flash('Error accessing the book. ' + str(e), 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('student_books'))  # Redirect to user dashboard if access is denied

#### Delete Booking Route:
@app.route('/delete_booking/<int:booking_id>', methods=['POST'])
def delete_booking(booking_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM bookings WHERE id = %s", (booking_id,))
        conn.commit()
        flash('Booking successfully deleted.', 'success')
    except Exception as e:
        conn.rollback()
        flash('Error deleting the booking. ' + str(e), 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('admin_bookings'))

from flask import Flask, render_template, request
import logging
import pickle
import numpy as np
from flask_login import login_required

# Configure logging
logging.basicConfig(filename='app.log', level=logging.INFO)

# Load data with error handling
try:
    popular_df = pickle.load(open('popular.pkl', 'rb'))
    pt = pickle.load(open('pt.pkl', 'rb'))
    books = pickle.load(open('books.pkl', 'rb'))
    similarity_scores = pickle.load(open('similarity_scores.pkl', 'rb'))
    logging.info("Pickle files loaded successfully.")
except Exception as e:
    logging.error(f"Error loading pickle files: {e}")
    popular_df = pt = books = similarity_scores = None

@app.route('/index')
@login_required
def index():
    try:
        if popular_df is not None:
            return render_template('index.html',
                                   book_name=list(popular_df['title'].values),
                                   author=list(popular_df['authors'].values),
                                   image=list(popular_df['image_url'].values),
                                   votes=list(popular_df['num_ratings'].values),
                                   rating=list(popular_df['avg_rating'].values)
                                   )
        else:
            logging.error("Popular dataframe is None.")
            return "Error loading popular books data", 500
    except Exception as e:
        logging.error(f"Error rendering index: {e}")
        return "An error occurred while processing your request", 500


@app.route('/recommend')
@login_required
def recommend_ui():
    return render_template('recommend.html')


@app.route('/recommend_books', methods=['GET', 'POST'])
@login_required
def recommend():
    try:
        user_input = request.form.get('user_input')

        # Normalize the user input and book titles for consistent matching
        user_input = user_input.strip().lower()

        # Check if user_input is valid
        if user_input not in [title.lower() for title in books['title'].values]:
            logging.warning(f"Invalid user input: {user_input}")
            return render_template('recommend.html', data=[], message="Book not found in the dataset.")

        # Get the corresponding book ID from the dataset
        book_id = books[books['title'].str.lower() == user_input]['book_id'].values[0]

        # Check if the book is present in the pivot table
        if book_id not in pt.index:
            logging.warning(f"Book ID {book_id} not found in the pivot table.")
            return render_template('recommend.html', data=[], message="Book not found in the pivot table.")

        index = list(pt.index).index(book_id)

        # Get similar items using cosine similarity
        similar_items = sorted(list(enumerate(similarity_scores[index])), key=lambda x: x[1], reverse=True)[1:6]

        data = []
        for i in similar_items:
            item = []
            temp_df = books[books['book_id'] == pt.index[i[0]]]

            # Extract book details, avoiding duplicates
            item.extend(temp_df['title'].drop_duplicates().values.tolist())
            item.extend(temp_df['authors'].drop_duplicates().values.tolist())
            item.extend(temp_df['image_url'].drop_duplicates().values.tolist())

            # Ensure item contains expected values
            data.append(item)

        logging.info(f"Recommendation data: {data}")
        return render_template('recommend.html', data=data)

    except Exception as e:
        logging.error(f"Error during recommendation: {e}")
        return render_template('recommend.html', data=[], message="An error occurred while processing your request.")

from flask_mail import Message, Mail
# Flask-Mail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'ronalkipro18@gmail.com'  # Use your Gmail address
app.config['MAIL_PASSWORD'] = 'dwdb hprw nhbe qhhf'  # Use your Gmail app password (if 2FA enabled)
mail = Mail(app)


# Route to handle contact form submission
@app.route('/submit_contact', methods=['POST'])
def submit_contact():
    # Get form data
    name = request.form['name']
    email = request.form['email']
    subject = request.form['subject']
    message = request.form['message']

    # Get DB connection
    conn = get_db_connection()
    if conn is None:
        return "Failed to connect to the database."

    cursor = conn.cursor()

    # Insert message into the database
    try:
        query = "INSERT INTO messages (name, email, subject, message) VALUES (%s, %s, %s, %s)"
        cursor.execute(query, (name, email, subject, message))
        conn.commit()
    except Exception as e:
        return f"An error occurred while inserting into the database: {e}"

    # Close the connection
    cursor.close()
    conn.close()

    # Send email to admin (optional)
    admin_email = 'ronalkipro18@gmail.com'
    msg = Message(
        subject=f"Contact Us Message: {subject}",
        recipients=[admin_email],
        sender=email,  # Set sender as the email from the form
        body=f"Message from {name} ({email})\n\nSubject: {subject}\n\nMessage:\n{message}"
    )

    try:
        mail.send(msg)
        return redirect(url_for('thank_you'))  # Redirect to thank-you page after submission
    except Exception as e:
        return f"An error occurred while sending the message: {str(e)}"

# Route for thank you page (after successful submission)
@app.route('/thank_you')
def thank_you():
    return "Thank you for your message! We will get back to you soon."

@app.route('/send_message', methods=['POST'])
def send_message():
    if request.method == 'POST':
        # Get form data
        name = request.form['name']
        email = request.form['email']
        message_content = request.form['message']

        # Send the message to the admin via email
        msg = Message('New Message from ' + name,
                      recipients=['ronalkipro18@gmail.com'])  # Replace with admin's email
        msg.body = f"Message from {name} ({email}):\n\n{message_content}"
        
        try:
            mail.send(msg)
            return redirect(url_for('success'))  # Redirect to a success page after sending
        except Exception as e:
            return f"An error occurred: {str(e)}"
    return render_template('send_message_form.html')


@app.route('/success')
def success():
    return "Message sent successfully to the admin!"
@app.route('/update_student_profile', methods=['POST'])
def update_student_profile():
    print("Profile update route accessed.")
    return "Profile Updated", 200
@app.route('/student_change_password', methods=['POST'])
def student_change_password():
    print("Password change route accessed.")
    return "Password changed successfully", 200
@app.route('/update_student_account_settings', methods=['POST'])
def update_student_account_settings():
    print("Route accessed")
    return "Success", 200
@app.route('/update_course_notifications', methods=['POST'])
def update_course_notifications():
    # Logic to update course notifications
    return "Course notifications updated successfully", 200
@app.route('/change_password', methods=['POST'])
def change_password():
    # Logic for handling the password change
    return "Password changed successfully", 200
@app.route('/update_account_settings', methods=['POST'])
def update_account_settings():
    # Logic to handle account settings update
    return "Account settings updated successfully", 200

@app.route('/deactivate_account', methods=['POST'])
@login_required
def deactivate_account():
    try:
        # Establish the database connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch the current user from the 'users' table
        cursor.execute('SELECT id, is_active FROM users WHERE id = %s', (current_user.id,))
        user = cursor.fetchone()

        if user:
            # Mark the user as inactive
            cursor.execute('UPDATE users SET is_active = %s WHERE id = %s', (False, current_user.id))
            conn.commit()

            # Log the user out after deactivation
            logout_user()

            flash("Your account has been deactivated successfully.", "success")
            return redirect(url_for('login'))  # Redirect to login page
        else:
            flash("Account not found.", "danger")
            return redirect(url_for('settings'))  # Redirect back to settings page
    except Exception as e:
        flash(f"An error occurred while deactivating the account: {str(e)}", "danger")
        return redirect(url_for('settings'))  # Handle exceptions and go back to settings page
    finally:
        # Close the database connection
        cursor.close()
        conn.close()


@app.route('/admin/messages')
def admin_messages():
    # Get DB connection
    conn = get_db_connection()
    if conn is None:
        return "Failed to connect to the database."

    cursor = conn.cursor()

    # Fetch all messages
    query = "SELECT id, name, email, subject, message, status, created_at FROM messages ORDER BY created_at DESC"
    cursor.execute(query)
    messages = cursor.fetchall()

    # Close the connection
    cursor.close()
    conn.close()

    return render_template('admin_messages.html', messages=messages)
@app.route('/admin/messages/mark_read/<int:message_id>', methods=['POST'])
def mark_message_read(message_id):
    conn = get_db_connection()
    if conn is None:
        return "Failed to connect to the database."

    cursor = conn.cursor()

    # Update the status of the message to 'read'
    query = "UPDATE messages SET status = 'read' WHERE id = %s"
    cursor.execute(query, (message_id,))
    conn.commit()

    cursor.close()
    conn.close()

    return redirect(url_for('admin_messages'))
@app.route('/accept_terms', methods=['POST'])
def accept_terms():
    # Logic to update user acceptance in the database
    flash("You have successfully accepted the terms.", "success")
    return redirect(url_for('browse_books'))

@app.route('/admin/admin_profile')
@login_required
def admin_profile():
    # Check if the current user is an admin
    if current_user.role != 'admin':
        return redirect(url_for('home'))  # Redirect non-admins to home
    departments = ['Computer Science', 'Mathematics', 'Physics', 'Engineering']
    return render_template('admin_profile.html ',departments=departments )  # Render the Admin Profile page
@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    # Your logic for editing the profile goes here
    return render_template('edit_profile.html')
@app.route('/admin/notifications', methods=['GET', 'POST'])
def admin_notifications():
    if request.method == 'POST':
        title = request.form['title']
        message = request.form['message']
        icon = request.form['icon']
        
        # Insert the notification into the Notifications table
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "INSERT INTO notifications (title, message, icon) VALUES (%s, %s, %s)"
        cursor.execute(query, (title, message, icon))
        conn.commit()
        
        # Retrieve the ID of the newly inserted notification
        notification_id = cursor.lastrowid
        
        # Insert the notification for all users in the UserNotifications table
        cursor.execute("SELECT id FROM users")
        users = cursor.fetchall()
        for user in users:
            cursor.execute("INSERT INTO user_notifications (user_id, notification_id) VALUES (%s, %s)", (user[0], notification_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Notification created successfully!', 'success')
        return redirect(url_for('admin_notifications'))

    # Retrieve all notifications
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notifications")
    notifications = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('admin_notifications.html', notifications=notifications)
@app.route('/user/notifications')
@login_required
def user_notifications():
    # Retrieve all notifications
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT n.id, n.title, n.message, n.icon, n.created_at 
        FROM notifications n
        ORDER BY n.created_at DESC
    """
    cursor.execute(query)
    notifications = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('user_notifications.html', notifications=notifications)

@app.route('/mark_as_read/<int:notification_id>')
def mark_as_read(notification_id):
    user_id = 1  # Replace with the current user ID after authentication
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE user_notifications 
        SET is_read = 1 
        WHERE user_id = %s AND notification_id = %s
    """, (user_id, notification_id))
    conn.commit()
    cursor.close()
    conn.close()
    
    return redirect(url_for('user_notifications'))
@app.context_processor

def inject_unread_notifications():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Count unread notifications for the logged-in user
    user_id = 1  # Replace with the actual logged-in user ID
    query = """
        SELECT COUNT(*) 
        FROM notifications 
        WHERE id NOT IN (
            SELECT notification_id 
            FROM user_notifications 
            WHERE user_id = %s
        )
    """
    cursor.execute(query, (user_id,))
    unread_notifications_count = cursor.fetchone()[0]
    cursor.close()
    conn.close()

    return {'unread_notifications_count': unread_notifications_count}
@app.before_request
def before_request():
    user_id = session.get('user_id')  # Retrieve user_id from session
    print(f"User ID from session: {user_id}")  # Debugging the session
    if user_id:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name, role, department FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            g.user = user  # Store user data in g
        else:
            g.user = None
    else:
        g.user = None  # No user logged in, set g.user to None
    print(f"User Data: {g.user}")  # Debugging the user data

@app.route('/search_books')
def search_books():
    # Code for handling book search
    return render_template('search_books.html')

@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    if 'user_id' not in session:  # Check if user is logged in
        flash('You need to be logged in to submit feedback.', 'danger')
        return redirect(url_for('login'))  # Redirect to login if not logged in

    if request.method == 'POST':
        feedback_text = request.form['feedback']  # Get the feedback from the form
        user_id = session['user_id']  # Get the user_id from session

        # Insert feedback into the database
        try:
            conn = get_db_connection()  # Get the connection to MySQL
            cursor = conn.cursor()

            # Insert feedback into the feedback table
            query = "INSERT INTO feedback (user_id, feedback_text) VALUES (%s, %s)"
            cursor.execute(query, (user_id, feedback_text))
            conn.commit()  # Commit the transaction

            # Flash a success message
            flash('Thank you for your feedback!', 'success')

        except mysql.connector.Error as err:
            # If there's an error, flash an error message
            flash(f'Error submitting feedback: {err}', 'danger')
        
        finally:
            # Ensure the connection is closed
            cursor.close()
            conn.close()

        # Redirect the user to the homepage (or any other page)
        return redirect(url_for('home'))  # Change 'home' to your desired route
    
    # If not a POST request, render the feedback form
    return render_template('feedback.html')

@app.route('/statistics')
def statistics():
    try:
        # Establish the database connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch the count of books
        cursor.execute('SELECT COUNT(*) FROM books')
        books_count = cursor.fetchone()[0]  # Fetch the first column of the first row

        # Fetch the count of registered users
        cursor.execute('SELECT COUNT(*) FROM users')
        users_count = cursor.fetchone()[0]

        # Fetch the count of downloads (assuming you have a 'downloads' table or field in the 'books' table)
        cursor.execute('SELECT SUM(download_count) FROM books')
        downloads_count = cursor.fetchone()[0] or 0  # Default to 0 if no downloads are found

        # Close the database connection
        cursor.close()
        conn.close()

        # Render the template with the fetched data
        return render_template('statistics.html', books_count=books_count, users_count=users_count, downloads_count=downloads_count)
    
    except Exception as e:
        # Handle errors (optional)
        return f"An error occurred: {str(e)}"

if __name__ == '__main__':
    app.run(debug=True)
