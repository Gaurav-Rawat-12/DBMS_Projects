# 🎫 Complaint Management System (DBMS Project)

A full-stack web application built with **Flask** and **MySQL** to manage and track user complaints efficiently. This project demonstrates core DBMS concepts including relational mapping, foreign key constraints, and CRUD operations.

## 🚀 Features
* **User Authentication:** Secure login/registration for Users and Admins.
* **Ticket Lifecycle:** Create, view, and track the status of tickets (Pending, In Progress, Resolved).
* **Role-Based Access:** Admins can assign tickets and update statuses; Users can only manage their own.
* **Relational Database:** Organized structure with Categories, Users, Admins, and Assignments.

---

## 🛠️ Tech Stack
* **Frontend:** HTML5, CSS3 (Bootstrap)
* **Backend:** Python 3.12, Flask
* **Database:** MySQL / MariaDB (via XAMPP)
* **Environment:** WSL2 (Ubuntu) for Python, Windows for Database

---

## 📋 Prerequisites
* **Python 3.x** installed in WSL.
* **XAMPP** installed on Windows.
* **Virtual Environment** (venv) configured.

---

## 🔧 Installation & Setup

### 1. Database Configuration (XAMPP)
1. Open **XAMPP Control Panel** and start **Apache** and **MySQL**.
2. Open the **XAMPP Shell** and run the following to create the database:
   ```sql
   mysql -u root
   CREATE DATABASE cms_db;
   ```
3. Import the schema to build the tables:
   ```bash
   mysql -u root cms_db < path/to/Schema.sql
   ```

### 2. Backend Setup (WSL)
1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/DBMS_Project.git
   cd DBMS_Project
   ```
2. Activate your virtual environment:
   ```bash
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### 3. Connecting WSL to Windows MySQL
Because Flask is in Linux and MySQL is in Windows, you must update the `host` IP in `app.py`:
1. Find your Windows IP from WSL: `ip route show | grep default`
2. Update the `get_db_connection()` function in `app.py` with that IP.

---

## 🏃 How to Run
```bash
python app.py
```
Visit `http://127.0.0.1:5000` in your browser to access the application.

---

## 📁 Project Structure
```text
DBMS_Project/
├── app.py              # Main Flask application
├── Schema.sql          # Database structure & initial data
├── templates/          # HTML files (Login, Dashboard, etc.)
├── static/             # CSS and Images
├── requirements.txt    # Python dependencies
└── README.md           # Project documentation
```

---

## 🛡️ Database Schema
The system uses 5 primary tables:
* **Users:** Stores customer credentials.
* **Admins:** Stores staff credentials.
* **Categories:** Hardware, Software, Network, etc.
* **Tickets:** The core data (Title, Description, Status, Priority).
* **Ticket_Assignments:** Links specific admins to specific tickets.

