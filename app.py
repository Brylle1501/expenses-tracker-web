import os
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, render_template, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# ---------------------------------------------------------
# Application Initialization & Configuration
# ---------------------------------------------------------
app = Flask(__name__)

# Base directory for local SQLite storage
basedir = os.path.abspath(os.path.dirname(__file__))

# Database URI (supports DATABASE_URL for Postgres on Vercel/cloud, or SQLite locally)
database_url = os.environ.get('DATABASE_URL')
if database_url:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif database_url.startswith("postgresql://") and not database_url.startswith("postgresql+"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)

# Handle Vercel serverless environment (read-only filesystem, writable /tmp only)
if os.environ.get('VERCEL'):
    default_sqlite_uri = "sqlite:////tmp/finance_todo.db"
else:
    default_sqlite_uri = f"sqlite:///{os.path.join(basedir, 'finance_todo.db')}"

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or default_sqlite_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_SORT_KEYS'] = False

# Secure Session Configuration
app.secret_key = os.environ.get('SECRET_KEY', 'apex-secure-production-key-2026-v2')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Initialize SQLAlchemy
db = SQLAlchemy(app)


# ---------------------------------------------------------
# Database Models (With User Authentication & Isolation)
# ---------------------------------------------------------
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships with cascade deletion
    tasks = db.relationship('Task', backref='user', cascade='all, delete-orphan', lazy=True)
    expenses = db.relationship('Expense', backref='user', cascade='all, delete-orphan', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }


class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    completed = db.Column(db.Boolean, default=False, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'completed': self.completed,
            'user_id': self.user_id
        }


class Expense(db.Model):
    __tablename__ = 'expenses'

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'description': self.description,
            'amount': round(self.amount, 2),
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'user_id': self.user_id
        }


# Auto-create tables on startup
with app.app_context():
    db.create_all()


# ---------------------------------------------------------
# Authentication Guard Decorator
# ---------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Unauthorized', 'message': 'Authentication required.'}), 401
        current_user = db.session.get(User, user_id)
        if not current_user:
            session.pop('user_id', None)
            return jsonify({'error': 'Unauthorized', 'message': 'Session expired. Please log in again.'}), 401
        return f(current_user, *args, **kwargs)
    return decorated_function


# ---------------------------------------------------------
# Web Routes
# ---------------------------------------------------------
@app.route('/')
def index():
    """Render the single-page mobile-first dashboard."""
    return render_template('index.html')


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify backend connectivity."""
    return jsonify({'status': 'ok', 'timestamp': datetime.utcnow().isoformat()}), 200


# ---------------------------------------------------------
# Authentication REST API Endpoints
# ---------------------------------------------------------
@app.route('/api/register', methods=['POST'])
def register():
    """Register a new user account and initiate session."""
    data = request.get_json(silent=True) or {}
    username = str(data.get('username', '')).strip()
    password = str(data.get('password', ''))

    if not username or len(username) < 3:
        return jsonify({'error': 'Username must be at least 3 characters long.'}), 400

    if not password or len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters long.'}), 400

    # Check for existing username (case-insensitive)
    existing_user = User.query.filter(db.func.lower(User.username) == username.lower()).first()
    if existing_user:
        return jsonify({'error': 'Username is already taken. Please choose another.'}), 409

    try:
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        # Automatically log in the user upon registration
        session.permanent = True
        session['user_id'] = new_user.id

        return jsonify({
            'message': 'Account created successfully.',
            'user': new_user.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Registration failed', 'details': str(e)}), 500


@app.route('/api/login', methods=['POST'])
def login():
    """Authenticate user credentials and initiate session."""
    data = request.get_json(silent=True) or {}
    username = str(data.get('username', '')).strip()
    password = str(data.get('password', ''))

    if not username or not password:
        return jsonify({'error': 'Please provide both username and password.'}), 400

    user = User.query.filter(db.func.lower(User.username) == username.lower()).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid username or password.'}), 401

    session.permanent = True
    session['user_id'] = user.id

    return jsonify({
        'message': 'Logged in successfully.',
        'user': user.to_dict()
    }), 200


@app.route('/api/logout', methods=['POST'])
def logout():
    """Clear session data and log out the user."""
    session.clear()
    return jsonify({'message': 'Logged out successfully.'}), 200


@app.route('/api/me', methods=['GET'])
def get_current_user():
    """Check authentication status and return current user details."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'authenticated': False}), 401

    user = db.session.get(User, user_id)
    if not user:
        session.pop('user_id', None)
        return jsonify({'authenticated': False}), 401

    return jsonify({
        'authenticated': True,
        'user': user.to_dict()
    }), 200


# ---------------------------------------------------------
# Task REST API Endpoints (Guarded & User-Isolated)
# ---------------------------------------------------------
@app.route('/api/tasks', methods=['GET'])
@login_required
def get_tasks(current_user):
    """Retrieve all tasks strictly belonging to the logged-in user."""
    try:
        tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.id.desc()).all()
        return jsonify([task.to_dict() for task in tasks]), 200
    except Exception as e:
        return jsonify({'error': 'Failed to retrieve tasks', 'details': str(e)}), 500


@app.route('/api/tasks', methods=['POST'])
@login_required
def create_task(current_user):
    """Create a new task for the logged-in user."""
    data = request.get_json(silent=True) or {}
    title = str(data.get('title', '')).strip()

    if not title:
        return jsonify({'error': 'Task title is required and cannot be empty.'}), 400

    try:
        new_task = Task(title=title, completed=False, user_id=current_user.id)
        db.session.add(new_task)
        db.session.commit()
        return jsonify(new_task.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create task', 'details': str(e)}), 500


@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
@login_required
def update_task(current_user, task_id):
    """Update task completion status or title for the logged-in user."""
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first()
    if not task:
        return jsonify({'error': f'Task with id {task_id} not found.'}), 404

    data = request.get_json(silent=True) or {}

    if 'completed' in data:
        task.completed = bool(data['completed'])

    if 'title' in data:
        title = str(data['title']).strip()
        if title:
            task.title = title

    try:
        db.session.commit()
        return jsonify(task.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update task', 'details': str(e)}), 500


@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@login_required
def delete_task(current_user, task_id):
    """Delete a task strictly owned by the logged-in user."""
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first()
    if not task:
        return jsonify({'error': f'Task with id {task_id} not found.'}), 404

    try:
        db.session.delete(task)
        db.session.commit()
        return jsonify({'message': 'Task deleted successfully', 'id': task_id}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete task', 'details': str(e)}), 500


# ---------------------------------------------------------
# Expense REST API Endpoints (Guarded & User-Isolated)
# ---------------------------------------------------------
@app.route('/api/expenses', methods=['GET'])
@login_required
def get_expenses(current_user):
    """Retrieve all expenses strictly belonging to the logged-in user."""
    try:
        expenses = Expense.query.filter_by(user_id=current_user.id).order_by(
            Expense.created_at.desc(), Expense.id.desc()
        ).all()
        return jsonify([exp.to_dict() for exp in expenses]), 200
    except Exception as e:
        return jsonify({'error': 'Failed to retrieve expenses', 'details': str(e)}), 500


@app.route('/api/expenses', methods=['POST'])
@login_required
def create_expense(current_user):
    """Log a new expense entry for the logged-in user."""
    data = request.get_json(silent=True) or {}
    description = str(data.get('description', '')).strip()
    amount_raw = data.get('amount')

    if not description:
        return jsonify({'error': 'Expense description is required.'}), 400

    try:
        amount = float(amount_raw)
        if amount <= 0:
            return jsonify({'error': 'Expense amount must be greater than zero.'}), 400
    except (TypeError, ValueError):
        return jsonify({'error': 'Valid numeric amount is required.'}), 400

    try:
        new_expense = Expense(description=description, amount=amount, user_id=current_user.id)
        db.session.add(new_expense)
        db.session.commit()
        return jsonify(new_expense.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create expense', 'details': str(e)}), 500


@app.route('/api/expenses/<int:expense_id>', methods=['DELETE'])
@login_required
def delete_expense(current_user, expense_id):
    """Delete an expense entry strictly owned by the logged-in user."""
    expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first()
    if not expense:
        return jsonify({'error': f'Expense with id {expense_id} not found.'}), 404

    try:
        db.session.delete(expense)
        db.session.commit()
        return jsonify({'message': 'Expense deleted successfully', 'id': expense_id}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete expense', 'details': str(e)}), 500


@app.route('/api/expenses/clear', methods=['DELETE'])
@login_required
def clear_all_expenses(current_user):
    """Delete all logged expense entries for the logged-in user (Reset Data)."""
    try:
        deleted_count = Expense.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        return jsonify({
            'message': 'All expense records cleared successfully.',
            'cleared_count': deleted_count
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to clear expenses', 'details': str(e)}), 500


# ---------------------------------------------------------
# Application Entry Point
# ---------------------------------------------------------
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
