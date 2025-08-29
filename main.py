from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector

app = Flask(__name__)
app.secret_key = "ton_secret_key"  # Change pour un vrai secret en prod

# ------------------------------
# Connexion MySQL
# ------------------------------
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",      # IP ou hostname de ton serveur MySQL
        user="quizuser",
        password="motdepasse",
        database="quiz_flask"
    )

# ------------------------------
# Utilisateurs
# ------------------------------
def add_user(pseudo, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        password_hash = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (pseudo, password_hash) VALUES (%s, %s)",
            (pseudo, password_hash)
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def get_user(pseudo):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE pseudo = %s", (pseudo,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

# ------------------------------
# Leaderboard
# ------------------------------
def add_score(pseudo, score):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO leaderboard (pseudo, score) VALUES (%s, %s)",
        (pseudo, score)
    )
    conn.commit()
    cursor.close()
    conn.close()

def get_leaderboard(limit=10):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT pseudo, score, date FROM leaderboard ORDER BY score DESC LIMIT %s",
        (limit,)
    )
    scores = cursor.fetchall()
    cursor.close()
    conn.close()
    return scores

# ------------------------------
# Routes
# ------------------------------
@app.route("/")
def home():
    if "pseudo" in session:
        return redirect(url_for("quiz"))
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        pseudo = request.form["pseudo"].strip()[:50]
        password = request.form["password"]

        if not pseudo or not password:
            return "Pseudo et mot de passe requis !"

        if get_user(pseudo):
            return "Pseudo déjà utilisé !"

        try:
            add_user(pseudo, password)
        except mysql.connector.Error as e:
            if e.errno == 1406:  # Data too long
                return "Pseudo trop long ! Limite 50 caractères."
            else:
                return f"Erreur base de données : {e}"

        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        pseudo = request.form["pseudo"].strip()
        password = request.form["password"]

        user = get_user(pseudo)
        if user and check_password_hash(user["password_hash"], password):
            session["pseudo"] = pseudo
            return redirect(url_for("quiz"))
        else:
            return "Pseudo ou mot de passe incorrect !"

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("pseudo", None)
    return redirect(url_for("login"))

@app.route("/quiz")
def quiz():
    if "pseudo" not in session:
        return redirect(url_for("login"))
    # Ici tu peux charger les questions depuis ton fichier Questions_QCM.txt
    with open("Questions_QCM.txt", "r", encoding="utf-8") as f:
        questions = [line.strip() for line in f if line.strip()]
    return render_template("quiz.html", questions=questions)

@app.route("/quiz_end", methods=["POST"])
def quiz_end():
    if "pseudo" not in session:
        return redirect(url_for("login"))
    pseudo = session["pseudo"]
    score = int(request.form.get("score", 0))
    add_score(pseudo, score)
    return render_template("quiz_end.html", score=score)

@app.route("/leaderboard")
def leaderboard():
    scores = get_leaderboard()
    return render_template("leaderboard.html", leaderboard=scores)

@app.route("/finish")
def finish():
    return render_template("finish.html")

# ------------------------------
# Lancer l'application
# ------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
