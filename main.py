import hashlib
import random
from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

import os

# ------------------ CHARGEMENT VARIABLES D'ENV ------------------
load_dotenv()
SECRET_KEY = os.environ.get("SECRET_KEY", "devkey")
MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
MYSQL_DB = os.environ.get("MYSQL_DB", "quiz_db")

# ------------------ INITIALISATION FLASK ------------------
app = Flask(__name__)
app.secret_key = SECRET_KEY

app.config['MYSQL_HOST'] = os.getenv("MYSQL_HOST", "localhost")
app.config['MYSQL_USER'] = os.getenv("MYSQL_USER", "root")
app.config['MYSQL_PASSWORD'] = os.getenv("MYSQL_PASSWORD", "")
app.config['MYSQL_DB'] = os.getenv("MYSQL_DB", "quiz_db")
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'  # pratique pour fetchall() en dict

mysql = MySQL(app)

# ------------------ UTILITAIRES ------------------
QUESTIONS_FILE = "Questions_QCM.txt"

def hash_password(pwd):
    return generate_password_hash(pwd, method='pbkdf2:sha256', salt_length=8)

def verify_password(pwd, hash):
    return check_password_hash(hash, pwd)

def get_user_by_pseudo(pseudo):
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, pseudo, password, score FROM users WHERE pseudo=%s", (pseudo,))
    return cur.fetchone()  # retourne tuple (id, pseudo, password, score) ou None


def add_user(pseudo, password_hashed):
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO users (pseudo, password) VALUES (%s, %s)", (pseudo, password_hashed))
    mysql.connection.commit()
    cur.close()


def load_questions():
    questions = []
    if not os.path.exists(QUESTIONS_FILE):
        return questions
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            parts = [p.strip() for p in line.strip().split(";")]
            if len(parts) == 5:
                question_text = parts[0]
                answers = parts[1:]
                correct_text = answers[0]
                random.shuffle(answers)
                correct_index = answers.index(correct_text)
                questions.append({
                    "id": idx,
                    "question": question_text,
                    "answers": answers,
                    "correct_index": correct_index
                })
    return questions

def get_user_answered_questions(user_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT question_id FROM user_questions WHERE user_id=%s", (user_id,))
    answered = [row['question_id'] for row in cur.fetchall()]
    cur.close()
    return answered

def record_answer(user_id, question_id, correct):
    cur = mysql.connection.cursor()
    cur.execute(
        "INSERT INTO user_questions (user_id, question_id, answered_correct) VALUES (%s,%s,%s)",
        (user_id, question_id, int(correct))
    )
    if correct:
        cur.execute("UPDATE users SET score = score + 1 WHERE id=%s", (user_id,))
    mysql.connection.commit()
    cur.close()

def get_leaderboard(limit=100):
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, pseudo, score FROM users ORDER BY score DESC LIMIT %s", (limit,))
    users = cur.fetchall()

    leaderboard = []
    for user in users:
        # Nombre total de questions répondues
        cur.execute("SELECT COUNT(*) AS total FROM user_questions WHERE user_id=%s", (user['id'],))
        row = cur.fetchone()
        total_questions = row['total'] if row else 0

        # Pourcentage de bonnes réponses
        percentage = int(user['score'] / total_questions * 100) if total_questions else 0

        leaderboard.append({
            "name": user['pseudo'],
            "score": user['score'],
            "total_questions": total_questions,
            "percentage": percentage
        })

    return leaderboard



# ------------------ ROUTES ------------------
@app.route("/")
def home():
    pseudo = session.get("pseudo")
    current_score = 0
    current_rank = None
    remaining_questions = 0

    leaderboard = get_leaderboard(100)

    if pseudo:
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, score FROM users WHERE pseudo=%s", (pseudo,))
        user = cur.fetchone()
        if user:
            current_score = user['score']

            # Calcul du rang
            for idx, entry in enumerate(leaderboard):
                if entry['name'] == pseudo:
                    current_rank = idx + 1
                    break

            # Questions restantes
            cur.execute("SELECT COUNT(*) AS total_questions FROM user_questions WHERE user_id=%s", (user['id'],))
            row = cur.fetchone()
            answered_questions = row['total_questions'] if row else 0
            total_available_questions = len(load_questions())  # à partir du .txt
            remaining_questions = max(0, total_available_questions - answered_questions)

    return render_template(
        "home.html",
        pseudo=pseudo,
        current_score=current_score,
        current_rank=current_rank,
        leaderboard=leaderboard,
        remaining_questions=remaining_questions,
        user={"pseudo": pseudo, "score": current_score, "answered_questions": remaining_questions}
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        pseudo = request.form["pseudo"].strip()
        password = request.form["password"]
        if get_user_by_pseudo(pseudo):
            return "Pseudo déjà utilisé !"
        add_user(pseudo, hash_password(password))
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        pseudo = request.form["pseudo"]
        password = request.form["password"]
        user = get_user_by_pseudo(pseudo)
        if user and user['password'] == hash_password(password):
            session["pseudo"] = pseudo
            session["user_id"] = user['id']
            return redirect(url_for("home"))
        return "Pseudo ou mot de passe incorrect !"
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/start_quiz")
def start_quiz():
    if "pseudo" not in session:
        return redirect(url_for("login"))

    user_id = session['user_id']
    all_questions = load_questions()
    asked_ids = get_user_answered_questions(user_id)
    available = [q for q in all_questions if q['id'] not in asked_ids]
    if not available:
        return render_template("quiz_end.html", leaderboard=get_leaderboard(), message="Vous avez répondu à toutes les questions !", remaining_questions=0)

    block_questions = random.sample(available, min(10, len(available)))
    session["questions"] = block_questions
    session["q_index"] = 0
    session["session_score"] = 0
    return redirect(url_for("quiz"))

@app.route("/quiz")
def quiz():
    if "pseudo" not in session:
        return redirect(url_for("login"))

    questions = session.get("questions", [])
    q_index = session.get("q_index", 0)
    total = len(questions)
    if total == 0 or q_index >= total:
        return redirect(url_for("home"))

    question = questions[q_index]
    show_result = session.get("show_result", False)
    last_selected = session.get("last_selected", None)

    cur_user = get_user_by_pseudo(session['pseudo'])
    current_score = cur_user['score'] if cur_user else 0

    return render_template(
        "quiz.html",
        question=question,
        q_index=q_index + 1,
        total=total,
        score=current_score,
        show_result=show_result,
        last_selected=last_selected
    )

@app.route("/answer", methods=["POST"])
def answer():
    if "pseudo" not in session:
        return redirect(url_for("login"))

    question_id = int(request.form["question_id"])
    selected_index = int(request.form["answer_index"])
    correct_index = int(request.form["correct_index"])

    session["last_selected"] = selected_index
    session["show_result"] = True
    session["pending_question_id"] = question_id
    session["pending_correct"] = int(selected_index == correct_index)
    return redirect(url_for("quiz"))

@app.route("/next_question")
def next_question():
    if "pseudo" not in session:
        return redirect(url_for("login"))

    pending_q = session.pop("pending_question_id", None)
    pending_correct = session.pop("pending_correct", None)
    session.pop("show_result", None)
    session.pop("last_selected", None)

    user_id = session['user_id']
    if pending_q is not None:
        record_answer(user_id, pending_q, pending_correct)

    session["q_index"] = session.get("q_index", 0) + 1
    questions = session.get("questions", [])

    if session["q_index"] >= len(questions):
        remaining_questions = len(load_questions()) - len(get_user_answered_questions(user_id))
        return render_template(
            "quiz_end.html",
            leaderboard=get_leaderboard(),
            message="Bloc terminé !",
            remaining_questions=remaining_questions
        )

    return redirect(url_for("quiz"))

# ------------------ LANCEMENT ------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
