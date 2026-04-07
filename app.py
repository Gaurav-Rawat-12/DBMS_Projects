import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql.cursors

app = Flask(__name__)
app.secret_key = 'apple_inspired_secret_key_here'

# --- Database Connection Helper ---
def get_db_connection():
    # Update these credentials as necessary for your local MySQL server.
    return pymysql.connect(
        host='172.29.112.1',
        user='root',
        password='', 
        database='cms_db',
        cursorclass=pymysql.cursors.DictCursor
    )

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
        cursor = conn.cursor()
        
        if role == 'admin':
            cursor.execute('SELECT * FROM Admins WHERE email = %s', (email,))
            user = cursor.fetchone()
        else:
            cursor.execute('SELECT * FROM Users WHERE email = %s', (email,))
            user = cursor.fetchone()
            
        cursor.close()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['loggedin'] = True
            session['role'] = role
            session['email'] = user['email']
            session['name'] = user['name']
            
            if role == 'admin':
                session['user_id'] = user['admin_id']
                return redirect(url_for('admin_dashboard'))
            else:
                session['user_id'] = user['user_id']
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
        hashed_pw = generate_password_hash(password)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            if role == 'admin':
                cursor.execute('INSERT INTO Admins (name, email, password_hash) VALUES (%s, %s, %s)', (name, email, hashed_pw))
            else:
                cursor.execute('INSERT INTO Users (name, email, password_hash) VALUES (%s, %s, %s)', (name, email, hashed_pw))
            conn.commit()
            flash('Successfully registered! Please log in.', 'success')
            return redirect(url_for('login', role=role))
        except pymysql.err.IntegrityError:
            flash('Email already exists.', 'error')
        finally:
            cursor.close()
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
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.*, c.name as category_name 
        FROM Tickets t 
        JOIN Categories c ON t.category_id = c.category_id 
        WHERE t.user_id = %s 
        ORDER BY t.created_at DESC
    ''', (session['user_id'],))
    tickets = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('dashboard.html', tickets=tickets)

@app.route('/create_ticket', methods=['GET', 'POST'])
def create_ticket():
    if not session.get('loggedin') or session.get('role') != 'user':
        return redirect(url_for('login', role='user'))
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        category_id = request.form['category']
        priority = request.form['priority']
        
        cursor.execute(
            'INSERT INTO Tickets (user_id, category_id, title, description, priority) VALUES (%s, %s, %s, %s, %s)',
            (session['user_id'], category_id, title, description, priority)
        )
        conn.commit()
        cursor.close()
        conn.close()
        flash('Ticket submitted successfully.', 'success')
        return redirect(url_for('dashboard'))
        
    cursor.execute('SELECT * FROM Categories')
    categories = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('create_ticket.html', categories=categories)

# --- Admin Routes ---

@app.route('/admin')
def admin_dashboard():
    if not session.get('loggedin') or session.get('role') != 'admin':
        return redirect(url_for('login', role='admin'))
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all tickets with user names, categories, and assignments
    query = '''
        SELECT t.*, u.name as user_name, c.name as category_name, a.name as assigned_to
        FROM Tickets t
        JOIN Users u ON t.user_id = u.user_id
        JOIN Categories c ON t.category_id = c.category_id
        LEFT JOIN Ticket_Assignments ta ON t.ticket_id = ta.ticket_id
        LEFT JOIN Admins a ON ta.admin_id = a.admin_id
        ORDER BY t.created_at DESC
    '''
    cursor.execute(query)
    tickets = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('admin_dashboard.html', tickets=tickets)

@app.route('/assign/<int:ticket_id>')
def assign_ticket(ticket_id):
    if not session.get('loggedin') or session.get('role') != 'admin':
        return redirect(url_for('login', role='admin'))
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if already assigned
    cursor.execute('SELECT * FROM Ticket_Assignments WHERE ticket_id = %s', (ticket_id,))
    if cursor.fetchone() is None:
        cursor.execute(
            'INSERT INTO Ticket_Assignments (ticket_id, admin_id) VALUES (%s, %s)',
            (ticket_id, session['user_id'])
        )
        cursor.execute("UPDATE Tickets SET status='In Progress' WHERE ticket_id = %s AND status = 'Pending'", (ticket_id,))
        conn.commit()
        flash(f'Ticket #{ticket_id} assigned to you.', 'success')
    else:
        flash('Ticket is already assigned.', 'error')
        
    cursor.close()
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/update_status/<int:ticket_id>', methods=['POST'])
def update_status(ticket_id):
    if not session.get('loggedin') or session.get('role') != 'admin':
        return redirect(url_for('login', role='admin'))
        
    status = request.form.get('status')
    if status in ['Pending', 'In Progress', 'Resolved']:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE Tickets SET status = %s WHERE ticket_id = %s', (status, ticket_id))
        conn.commit()
        cursor.close()
        conn.close()
        flash(f'Ticket #{ticket_id} status updated to {status}.', 'success')
        
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
