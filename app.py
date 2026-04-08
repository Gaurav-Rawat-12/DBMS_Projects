import os
import re
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'apple_inspired_secret_key_here')
DATABASE_PATH = os.environ.get('DATABASE_PATH', 'database.db')
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- Database Connection Helper ---
def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    if not os.path.exists(DATABASE_PATH):
        conn = get_db_connection()
        with open('schema.sql', 'r') as f:
            script = f.read()
            conn.executescript(script)
        conn.commit()
        conn.close()

init_db()

# --- Email Validator ---
def is_valid_email(email):
    regex = r'^\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return re.fullmatch(regex, email) is not None

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')

# --- User & Admin Auth ---

@app.route('/login/<role>', methods=['GET', 'POST'])
def login(role):
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM Users WHERE email = ? AND role = ?', (email, role)).fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['loggedin'] = True
            session['role'] = role
            session['email'] = user['email']
            session['name'] = user['name']
            session['user_id'] = user['user_id']
            
            if role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('Incorrect email/password combo!', 'error')
            
    return render_template('login.html', role=role, action='login')

@app.route('/register/<role>', methods=['GET', 'POST'])
def register(role):
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        if not is_valid_email(email):
            flash('Invalid email format.', 'error')
            return redirect(url_for('register', role=role))

        hashed_pw = generate_password_hash(password)
        
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO Users (name, email, password_hash, role) VALUES (?, ?, ?, ?)', (name, email, hashed_pw, role))
            conn.commit()
            flash('Successfully registered! Please log in.', 'success')
            return redirect(url_for('login', role=role))
        except sqlite3.IntegrityError:
            flash('Email already exists.', 'error')
        finally:
            conn.close()

    return render_template('login.html', role=role, action='register')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# --- User Routes ---

@app.route('/dashboard')
def dashboard():
    if not session.get('loggedin') or session.get('role') != 'user':
        return redirect(url_for('login', role='user'))
        
    conn = get_db_connection()
    tickets = conn.execute('''
        SELECT t.*, c.name as category_name 
        FROM Tickets t 
        JOIN Categories c ON t.category_id = c.category_id 
        WHERE t.user_id = ? AND t.is_active = 1
        ORDER BY t.created_at DESC
    ''', (session['user_id'],)).fetchall()
    conn.close()
    
    return render_template('dashboard.html', tickets=tickets)

@app.route('/create_ticket', methods=['GET', 'POST'])
def create_ticket():
    if not session.get('loggedin') or session.get('role') != 'user':
        return redirect(url_for('login', role='user'))
        
    conn = get_db_connection()
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        category_id = request.form['category']
        priority = request.form['priority']
        
        attachment_path = None
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                attachment_path = filename
        
        conn.execute(
            'INSERT INTO Tickets (user_id, category_id, title, description, priority, attachment_path) VALUES (?, ?, ?, ?, ?, ?)',
            (session['user_id'], category_id, title, description, priority, attachment_path)
        )
        conn.commit()
        conn.close()
        flash('Ticket submitted successfully.', 'success')
        return redirect(url_for('dashboard'))
        
    categories = conn.execute('SELECT * FROM Categories').fetchall()
    conn.close()
    
    return render_template('create_ticket.html', categories=categories)

# --- Admin Routes ---

@app.route('/admin')
def admin_dashboard():
    if not session.get('loggedin') or session.get('role') != 'admin':
        return redirect(url_for('login', role='admin'))
        
    conn = get_db_connection()
    
    query = '''
        SELECT t.*, u.name as user_name, c.name as category_name, a.name as assigned_to
        FROM Tickets t
        JOIN Users u ON t.user_id = u.user_id
        JOIN Categories c ON t.category_id = c.category_id
        LEFT JOIN Ticket_Assignments ta ON t.ticket_id = ta.ticket_id
        LEFT JOIN Users a ON ta.user_id = a.user_id
        WHERE t.is_active = 1
        ORDER BY t.created_at DESC
    '''
    tickets = conn.execute(query).fetchall()
    conn.close()
    
    return render_template('admin_dashboard.html', tickets=tickets)

@app.route('/assign/<int:ticket_id>')
def assign_ticket(ticket_id):
    if not session.get('loggedin') or session.get('role') != 'admin':
        return redirect(url_for('login', role='admin'))
        
    conn = get_db_connection()
    
    assignment = conn.execute('SELECT * FROM Ticket_Assignments WHERE ticket_id = ?', (ticket_id,)).fetchone()
    if assignment is None:
        conn.execute(
            'INSERT INTO Ticket_Assignments (ticket_id, user_id) VALUES (?, ?)',
            (ticket_id, session['user_id'])
        )
        conn.execute("UPDATE Tickets SET status='In Progress', updated_at=CURRENT_TIMESTAMP WHERE ticket_id = ? AND status = 'Pending'", (ticket_id,))
        conn.commit()
        flash(f'Ticket #{ticket_id} assigned to you.', 'success')
    else:
        flash('Ticket is already assigned.', 'error')
        
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/update_status/<int:ticket_id>', methods=['POST'])
def update_status(ticket_id):
    if not session.get('loggedin') or session.get('role') != 'admin':
        return redirect(url_for('login', role='admin'))
        
    status = request.form.get('status')
    comment = request.form.get('comment', 'Status updated.')
    
    if status in ['Pending', 'In Progress', 'Resolved']:
        conn = get_db_connection()
        
        update_query = "UPDATE Tickets SET status = ?, updated_at = CURRENT_TIMESTAMP"
        if status == 'Resolved':
            update_query += ", resolved_at = CURRENT_TIMESTAMP"
        update_query += " WHERE ticket_id = ?"
        
        conn.execute(update_query, (status, ticket_id))
        
        # Log the activity
        conn.execute(
            "INSERT INTO Ticket_Logs (ticket_id, user_id, comment) VALUES (?, ?, ?)",
            (ticket_id, session['user_id'], comment)
        )
        
        conn.commit()
        conn.close()
        flash(f'Ticket #{ticket_id} status updated to {status}.', 'success')
        
    return redirect(url_for('admin_dashboard'))

@app.route('/ticket/<int:ticket_id>')
def ticket_detail(ticket_id):
    if not session.get('loggedin'):
        return redirect(url_for('index'))
        
    conn = get_db_connection()
    
    ticket = conn.execute('''
        SELECT t.*, u.name as user_name, c.name as category_name
        FROM Tickets t
        JOIN Users u ON t.user_id = u.user_id
        JOIN Categories c ON t.category_id = c.category_id
        WHERE t.ticket_id = ? AND t.is_active = 1
    ''', (ticket_id,)).fetchone()
    
    if not ticket:
        conn.close()
        flash('Ticket not found.', 'error')
        return redirect(url_for('dashboard') if session.get('role') == 'user' else url_for('admin_dashboard'))
        
    # Check authorization
    if session.get('role') == 'user' and ticket['user_id'] != session['user_id']:
        conn.close()
        flash('Unauthorized access.', 'error')
        return redirect(url_for('dashboard'))
        
    logs = conn.execute('''
        SELECT l.*, u.name as user_name, u.role as user_role
        FROM Ticket_Logs l
        JOIN Users u ON l.user_id = u.user_id
        WHERE l.ticket_id = ?
        ORDER BY l.created_at ASC
    ''', (ticket_id,)).fetchall()
    
    conn.close()
    
    return render_template('ticket_detail.html', ticket=ticket, logs=logs)

@app.route('/add_comment/<int:ticket_id>', methods=['POST'])
def add_comment(ticket_id):
    if not session.get('loggedin'):
        return redirect(url_for('index'))
        
    comment = request.form.get('comment')
    if not comment:
        return redirect(url_for('ticket_detail', ticket_id=ticket_id))
        
    conn = get_db_connection()
    
    # Ensure they have access
    ticket = conn.execute('SELECT * FROM Tickets WHERE ticket_id = ? AND is_active = 1', (ticket_id,)).fetchone()
    if not ticket or (session.get('role') == 'user' and ticket['user_id'] != session['user_id']):
        conn.close()
        return redirect(url_for('dashboard'))
        
    conn.execute(
        "INSERT INTO Ticket_Logs (ticket_id, user_id, comment) VALUES (?, ?, ?)",
        (ticket_id, session['user_id'], comment)
    )
    conn.execute("UPDATE Tickets SET updated_at = CURRENT_TIMESTAMP WHERE ticket_id = ?", (ticket_id,))
    
    conn.commit()
    conn.close()
    
    return redirect(url_for('ticket_detail', ticket_id=ticket_id))

if __name__ == '__main__':
    app.run(debug=True)
