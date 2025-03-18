from flask_mysqldb import MySQL
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize MySQL
mysql = MySQL()

class User(UserMixin):
    def __init__(self, id, username, email, password_hash, role):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.role = role
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Database Schema Setup
def create_tables():
    cur = mysql.connection.cursor()
    
    # Users Table
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(100) NOT NULL,
        email VARCHAR(100) UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role ENUM('user', 'admin') DEFAULT 'user'
    )''')
    
    # Predictions Table
    cur.execute('''CREATE TABLE IF NOT EXISTS predictions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT,
        guest_id VARCHAR(36),
        audio_file VARCHAR(255) NOT NULL,
        transcribed_text TEXT NOT NULL,
        classification VARCHAR(50) NOT NULL,
        matched_keywords TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    
    mysql.connection.commit()
    cur.close()
