import os
import requests
from flask import Flask, jsonify, request, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, current_user, logout_user, login_required
from flask_cors import CORS
from functools import wraps
import jwt
import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'do not enter')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
API_KEY = os.getenv('API_KEY', '2b7e0491c60441cdab6cc467a1f2ae0f')
CORS(app)

# Initialize extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # Redirects to 'login' page if not logged in
login_manager.login_message_category = 'info'

# Sample data for posts (could be replaced with a database model later)
POSTS = [
    {"id": 1, "title": "First post", "content": "This is the first post.", "comments": ["Great post!", "Thanks for sharing."]},
    {"id": 2, "title": "Second post", "content": "This is the second post.", "comments": ["Nice post."]},
    {"id": 3, "title": "Flask tutorial", "content": "Learn Flask with this tutorial.", "comments": []},
    {"id": 4, "title": "Advanced Flask", "content": "Delve deeper into Flask.", "comments": ["Very helpful!"]},
]

USERS = {}

# Pagination function
def paginate_posts(posts, page, per_page):
    start = (page - 1) * per_page
    end = start + per_page
    return posts[start:end]

# Authorization decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')

        if not token:
            return jsonify({'error': 'Token is missing!'}), 403

        try:
            jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        except:
            return jsonify({'error': 'Token is invalid!'}), 403

        return f(*args, **kwargs)
    return decorated

# Rate limiting dictionary (user-specific rate limits)
rate_limits = {}

# Rate limiting decorator
def rate_limit(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = request.remote_addr  # Assuming IP-based rate limiting for simplicity
        current_time = datetime.datetime.now()

        if user not in rate_limits:
            rate_limits[user] = {'last_request': current_time, 'request_count': 0}

        # Calculate the time difference from the last request
        time_diff = (current_time - rate_limits[user]['last_request']).seconds
        if time_diff < 60:
            # If within a minute, increment the request count
            rate_limits[user]['request_count'] += 1
        else:
            # Reset the count after a minute
            rate_limits[user]['request_count'] = 1

        rate_limits[user]['last_request'] = current_time

        if rate_limits[user]['request_count'] > 10:  # Limit to 10 requests per minute
            return jsonify({"error": "Rate limit exceeded. Try again later."}), 429

        return f(*args, **kwargs)
    return decorated_function

# User model for Flask-Login
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Route to register a new user
@app.route('/api/register', methods=['POST'])
def register_user():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    if username in USERS:
        return jsonify({"error": "User already exists"}), 400

    USERS[username] = password
    return jsonify({"message": "User registered successfully"}), 201

# Route to login a user and generate a token
@app.route('/api/login', methods=['POST'])
def login_user():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if USERS.get(username) != password:
        return jsonify({"error": "Invalid credentials"}), 401

    token = jwt.encode({'user': username, 'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)},
                       app.config['SECRET_KEY'], algorithm="HS256")
    return jsonify({'token': token}), 200

# Route to get all posts with optional sorting and pagination
@app.route('/api/posts', methods=['GET'])
@token_required
@rate_limit
def get_posts():
    sort_field = request.args.get('sort')
    direction = request.args.get('direction', 'asc')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 5))

    # Validate the sort field
    if sort_field and sort_field not in ['title', 'content']:
        return jsonify({"error": "Invalid sort field. Must be 'title' or 'content'."}), 400

    # Validate the direction
    if direction not in ['asc', 'desc']:
        return jsonify({"error": "Invalid direction. Must be 'asc' or 'desc'."}), 400

    # If a valid sort field is provided, sort the posts accordingly
    sorted_posts = POSTS
    if sort_field:
        reverse = True if direction == 'desc' else False
        sorted_posts = sorted(POSTS, key=lambda post: post[sort_field].lower(), reverse=reverse)

    # Paginate the posts
    paginated_posts = paginate_posts(sorted_posts, page, per_page)

    return jsonify(paginated_posts), 200

# Route to add a new post
@app.route('/api/posts', methods=['POST'])
@token_required
@rate_limit
def add_post():
    data = request.json
    if not data.get('title') or not data.get('content'):
        return jsonify({"error": "Title and content are required"}), 400

    new_id = max(post['id'] for post in POSTS) + 1 if POSTS else 1
    new_post = {
        "id": new_id,
        "title": data['title'],
        "content": data['content'],
        "comments": []  # Initialize with empty comments
    }
    POSTS.append(new_post)
    return jsonify(new_post), 201

# Route to delete a post by id
@app.route('/api/posts/<int:id>', methods=['DELETE'])
@token_required
@rate_limit
def delete_post(id):
    global POSTS
    post = next((post for post in POSTS if post['id'] == id), None)
    if post is None:
        return jsonify({"error": "Post not found"}), 404

    POSTS = [post for post in POSTS if post['id'] != id]
    return jsonify({"message": f"Post with id {id} has been deleted successfully."}), 200

# Route to update a post by id
@app.route('/api/posts/<int:id>', methods=['PUT'])
@token_required
@rate_limit
def update_post(id):
    data = request.json
    post = next((post for post in POSTS if post['id'] == id), None)
    if post is None:
        return jsonify({"error": "Post not found"}), 404

    post['title'] = data.get('title', post['title'])
    post['content'] = data.get('content', post['content'])
    return jsonify(post), 200

# Route to search for posts by title or content
@app.route('/api/posts/search', methods=['GET'])
@token_required
@rate_limit
def search_posts():
    title_query = request.args.get('title', '').lower()
    content_query = request.args.get('content', '').lower()

    matching_posts = [
        post for post in POSTS
        if (title_query in post['title'].lower()) or (content_query in post['content'].lower())
    ]

    return jsonify(matching_posts), 200

# Route to add a comment to a post
@app.route('/api/posts/<int:id>/comments', methods=['POST'])
@token_required
@rate_limit
def add_comment(id):
    data = request.json
    comment = data.get('comment')
    post = next((post for post in POSTS if post['id'] == id), None)

    if post is None:
        return jsonify({"error": "Post not found"}), 404

    if not comment:
        return jsonify({"error": "Comment is required"}), 400

    post['comments'].append(comment)
    return jsonify({"message": "Comment added successfully", "post": post}), 201

# Route to fetch data from an external API using API key
@app.route('/api/external_data', methods=['GET'])
def fetch_external_data():
    url = 'https://api.example.com/data'  # Replace with the actual external API endpoint
    headers = {
        'Authorization': f'Bearer {API_KEY}'
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return jsonify(response.json()), 200
    else:
        return jsonify({"error": "Failed to fetch data from external API"}), response.status_code

# Web routes for registration, login, and account management
@app.route('/')
@app.route('/home')
def home():
    return render_template('home.html')  # Assuming a home.html template exists

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, email=email, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')  # Assuming a register.html template exists

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html')  # Assuming a login.html template exists

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/account')
@login_required
def account():
    return render_template('account.html')  # Assuming an account.html template exists

# Initialize the database
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5004, debug=True)
