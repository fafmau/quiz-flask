from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import random
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)
app.secret_key = "ton_secret_key"  # à changer

# ---------------------------
# Connexion à MySQL
# ---------------------------
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="quizuser",
        password="motdepasse",
        database="quiz_flask"
    )


# ---------------------------
# Gestion des utilisateurs
# ---------------------------
def add_user(pseudo, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        password_hash = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (pseudo, password_hash) VALUES (%s, %s)",
            (pseudo, password_hash)
        )
        conn.commit()  # ← obligatoire
    except mysql.connector.Error as e:
        print("Erreur:", e)
        raise e
    finally:
        cursor.close()
        conn.close()


def get_user(pseudo):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE pseudo=%s", (pseudo,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

# ---------------------------
# Gestion du leaderboard
# ---------------------------
def update_leaderboard(user_id, score, total_questions):
    percentage = (score / total_questions * 100) if total_questions > 0 else 0
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO leaderboard (user_id, score, total_questions, percentage)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE score=%s, total_questions=%s, percentage=%s
    """, (user_id, score, total_questions, percentage, score, total_questions, percentage))
    conn.commit()
    cursor.close()
    conn.close()

def get_leaderboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT u.pseudo, l.score, l.total_questions, l.percentage
        FROM leaderboard l
        JOIN users u ON l.user_id = u.id
        ORDER BY l.score DESC
        LIMIT 10
    """)
    leaderboard = cursor.fetchall()
    cursor.close()
    conn.close()
    return leaderboard

# ---------------------------
# Chargement des questions
# ---------------------------
def load_questions():
    questions = []
    with open("Questions_QCM.txt", "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(";")
            if len(parts) >= 5:
                questions.append({
                    "question": parts[0],
                    "answers": parts[1:5],
                    "correct_index": 0  # toujours première réponse correcte
                })
    return questions

# ---------------------------
# Routes
# ---------------------------
@app.route("/")
def home():
    pseudo = session.get("pseudo")
    if not pseudo:
        return redirect(url_for("login"))
    leaderboard = get_leaderboard()
    return render_template("home.html", pseudo=pseudo, leaderboard=leaderboard)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        pseudo = request.form["pseudo"].strip()[:50]  # max 50 caractères
        password = request.form["password"]

        if not pseudo or not password:
            return "Pseudo et mot de passe requis !"

        # Vérifie si le pseudo existe déjà
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
        pseudo = request.form["pseudo"]
        password = request.form["password"]
        user = get_user(pseudo)
        if not user or not check_password_hash(user["password_hash"], password):
            return "Pseudo ou mot de passe incorrect"
        session["pseudo"] = pseudo
        session["user_id"] = user["id"]
        return redirect(url_for("home"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    if "pseudo" not in session:
        return redirect(url_for("login"))

    if "questions" not in session:
        session["questions"] = load_questions()
        random.shuffle(session["questions"])
        session["score"] = 0
        session["q_index"] = 0

    questions = session["questions"]
    q_index = session["q_index"]

    if request.method == "POST":
        answer = int(request.form.get("answer"))
        correct_index = questions[q_index]["correct_index"]
        if answer == correct_index:
            session["score"] += 1
        session["q_index"] += 1
        q_index = session["q_index"]

    if q_index >= len(questions):
        update_leaderboard(session["user_id"], session["score"], len(questions))
        session.pop("questions", None)
        session.pop("q_index", None)
        score = session.pop("score", 0)
        return render_template("quiz_end.html", score=score, leaderboard=get_leaderboard())

    question = questions[q_index]
    return render_template("quiz.html", question=question, q_index=q_index + 1, total=len(questions), score=session.get("score",0))

# ---------------------------
# Lancement de l'application
# ---------------------------
if __name__ == "__main__":
    app.run(debug=True)
