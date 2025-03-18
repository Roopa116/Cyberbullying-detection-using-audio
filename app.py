import os
import uuid
import pandas as pd
import whisper
import librosa
import soundfile as sf
import MySQLdb.cursors  # Ensure this import is present
import mysql.connector 
from pydub import AudioSegment
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask import Flask, render_template, request, redirect, session, url_for
from flask import Flask, render_template

app = Flask(__name__)
app.secret_key = "super_secret_key"

DB_CONFIG = {
    'host': 'localhost',   # Change if your MySQL is on a different server
    'user': 'root',
    'password': 'root',
    'database': 'voiceshield_db'
}

# Admin credentials
ADMIN_EMAIL = "acharoopa01@gmail.com"
ADMIN_PASSWORD = "acha4678"

# Function to fetch user from the database
def fetch_user_from_db(email, password):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cur.fetchone()
    cur.close()

    if user and check_password_hash(user["password_hash"], password):  
        return User(id=user["id"], username=user["username"], email=user["email"], role=user["role"])
    return None

# Function to fetch all predictions for the admin
# Function to fetch all predictions for the admin
def fetch_all_predictions_from_db():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("""
        SELECT id, user_id, guest_id, audio_file, transcribed_text, classification, matched_keywords, timestamp 
        FROM predictions
    """)
    predictions = cur.fetchall()
    cur.close()
    return predictions


# MySQL Config (Update with your MySQL credentials)
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = "root"
app.config["MYSQL_DB"] = "voiceshield_db"
mysql = MySQL(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# User Model
class User(UserMixin):
    def __init__(self, id, username, email, role):
        self.id = id
        self.username = username
        self.email = email
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, username, email, role FROM users WHERE id=%s", (user_id,))
    user = cur.fetchone()
    cur.close()
    if user:
     return User(id=user[0], username=user[1], email=user[2], role=user[3])
    return None


# Load keyword dataset
def load_keyword_dataset():
    dataset_path = "C:/Users/achar/Downloads/cyberbullying_detection sample/cyberbullying_detection-main/dataset.csv"
    if os.path.exists(dataset_path):
        dataset = pd.read_csv(dataset_path)
        return dataset['headline'].dropna().astype(str).tolist()
    return []

keywords = load_keyword_dataset()

# Convert MP3 to WAV
def convert_audio(input_path):
    output_path = input_path.replace(".mp3", ".wav")
    audio = AudioSegment.from_mp3(input_path)
    audio.export(output_path, format="wav")
    return output_path

# Noise Filtering
def noise_filtering(audio_file):
    y, sr = librosa.load(audio_file, sr=None)
    y_filtered = librosa.effects.preemphasis(y)
    sf.write(audio_file, y_filtered, sr)

# Speech-to-Text
def speech_to_text(audio_file):
    model = whisper.load_model("base")
    result = model.transcribe(audio_file)
    return result["text"]

# Classify text
def classify_text(text):
    text_tokens = text.lower().split()
    matched_keywords = [word for word in text_tokens if word in keywords]
    classification = "Bullying" if len(matched_keywords) >= 3 else "Not Bullying"
    return classification, ", ".join(matched_keywords)

@app.route('/')
def index():
    if not session.get("guest_id"):
        session["guest_id"] = str(uuid.uuid4())  # Assign a unique guest ID if it's not already set
    if current_user.is_authenticated:
        logout_user()  # Force logout
        session.clear()
    return render_template('index.html')


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)", (username, email, password))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            user = User(id="admin", username="Admin", email=ADMIN_EMAIL, role="admin")
            login_user(user, remember=True)
            session["role"] = "admin"
            session["username"] = "Admin"  # Store username in session
            return redirect(url_for("admin_dashboard"))

        user = fetch_user_from_db(email, password)
        if user:
            login_user(user, remember=True)
            session["role"] = user.role
            session["username"] = user.username  # Store username in session
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()  # Clears the user session completely
    logout_user()  # Flask-Login logout
    return redirect(url_for('login'))  # Redirects to the login page

@app.route("/dashboard", methods=["GET"])
@login_required
def dashboard():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM predictions WHERE user_id=%s ORDER BY timestamp DESC", (current_user.id,))
    predictions = cur.fetchall()
    cur.close()

    username = session.get("username", "User")  # Retrieve username from session
    return render_template("dashboard.html", predictions=predictions, username=username)

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if session.get("role") == "admin":
        predictions = fetch_all_predictions_from_db()
        if not predictions:
            flash("No predictions found!", "warning")
        return render_template('admin_dashboard.html', predictions=predictions)
    flash("Unauthorized access!", "danger")
    return redirect(url_for('login'))
@app.route("/predict", methods=["POST"])
def predict():
    if "audio" not in request.files:
        flash("No file uploaded!", "danger")
        return redirect(url_for("index"))  # Keep the user on the index page

    file = request.files["audio"]
    filename = f"{uuid.uuid4()}.wav"
    file_path = os.path.join("uploads", filename)
    file.save(file_path)

    # Convert audio if it's MP3
    if file.filename.endswith(".mp3"):
        file_path = convert_audio(file_path)

    # Perform noise filtering and speech-to-text
    noise_filtering(file_path)
    transcribed_text = speech_to_text(file_path)
    classification, matched_keywords = classify_text(transcribed_text)

    # Check if user is logged in and store the prediction accordingly
    if current_user.is_authenticated:
        user_id = current_user.id
    else:
        user_id = None  # Store as guest if not logged in

    # Save the prediction in the database with guest_id if not logged in
    cur = mysql.connection.cursor()
    cur.execute("""INSERT INTO predictions (user_id, guest_id, audio_file, transcribed_text, classification, matched_keywords)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (user_id, str(uuid.uuid4()), filename, transcribed_text, classification, matched_keywords))
    mysql.connection.commit()
    cur.close()

    # Return to the index page with the results
    return render_template('index.html', transcribed_text=transcribed_text, classification=classification, matched_keywords=matched_keywords)

    
@login_manager.user_loader
def load_user(user_id):
    if user_id == "admin":
        return User(id="admin", username="Admin", email=ADMIN_EMAIL, role="admin")

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT id, username, email, role FROM users WHERE id=%s", (user_id,))
    user = cur.fetchone()
    cur.close()
    if user:
        return User(id=user["id"], username=user["username"], email=user["email"], role=user["role"])
    return None
@app.route('/')
def home():
    return "Cyberbullying Detection Running on Replit!"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))  # Render assigns a port dynamically
    app.run(host='0.0.0.0', port=port)
