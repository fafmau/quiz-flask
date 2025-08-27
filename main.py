import hashlib
from flask import Flask, render_template, request, redirect, url_for, session
import json, os, random

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "devkey")


USERS_FILE = "users.json"
LEADERBOARD_FILE = "leaderboard.json"
QUESTIONS_FILE = "Questions_QCM.txt"

# ------------------ UTILITAIRES ------------------
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                pass
    return []

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def load_leaderboard():
    if os.path.exists(LEADERBOARD_FILE):
        with open(LEADERBOARD_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                pass
    return []

def save_leaderboard(leaderboard):
    with open(LEADERBOARD_FILE, "w", encoding="utf-8") as f:
        json.dump(leaderboard, f, ensure_ascii=False, indent=2)

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

def get_leaderboard():
    leaderboard = load_leaderboard()
    users = load_users()
    enriched_lb = []
    for entry in leaderboard:
        user = next((u for u in users if u["pseudo"] == entry["name"]), None)
        if user:
            total_questions = len(user.get("asked_questions", []))
            score = user.get("score", 0)
            percentage = int(score / total_questions * 100) if total_questions else 0
            enriched_lb.append({
                "name": user["pseudo"],
                "score": score,
                "total_questions": total_questions,
                "percentage": percentage
            })
    enriched_lb.sort(key=lambda x: x["score"], reverse=True)
    return enriched_lb

# ------------------ ROUTES ------------------
@app.route("/")
def home():
    pseudo = session.get("pseudo")
    current_score = 0
    current_rank = None
    remaining_questions = 0

    leaderboard = get_leaderboard()  # tout le leaderboard enrichi
    users = load_users()  # nécessaire pour calculer remaining_questions

    # Trouver l'utilisateur connecté
    user = None
    if pseudo:
        user = next((u for u in users if u["pseudo"] == pseudo), None)
        if user:
            current_score = user.get("score", 0)
            # Rang
            for idx, entry in enumerate(leaderboard):
                if entry["name"] == pseudo:
                    current_rank = idx + 1
                    break
            # Questions restantes
            total_questions = len(load_questions())
            answered = len(user.get("asked_questions", []))
            remaining_questions = max(0, total_questions - answered)

    return render_template(
        "home.html",
        pseudo=pseudo,
        current_score=current_score,
        current_rank=current_rank,
        leaderboard=leaderboard,  # <-- on passe tout le leaderboard
        remaining_questions=remaining_questions,
        user=user  # <-- on passe l'utilisateur connecté
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        pseudo = request.form["pseudo"].strip()
        password = request.form["password"]
        users = load_users()
        if any(u["pseudo"] == pseudo for u in users):
            return "Pseudo déjà utilisé !"
        users.append({
            "pseudo": pseudo,
            "password": hash_password(password),
            "score": 0,
            "asked_questions": []
        })
        save_users(users)
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        pseudo = request.form["pseudo"]
        password = request.form["password"]
        users = load_users()
        user = next((u for u in users if u["pseudo"] == pseudo), None)
        if user and user["password"] == hash_password(password):
            session["pseudo"] = pseudo
            session["current_score"] = user.get("score", 0)
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
    all_questions = load_questions()
    users = load_users()
    user = next(u for u in users if u["pseudo"] == session["pseudo"])
    asked_ids = user.get("asked_questions", [])
    available = [q for q in all_questions if q["id"] not in asked_ids]
    if not available:
        return render_template("quiz_end.html", leaderboard=get_leaderboard(), message="Vous avez répondu à toutes les questions !", remaining_questions=0)
    block_questions = random.sample(available, min(10, len(available)))
    for q in block_questions:
        answers = q["answers"].copy()
        correct_text = answers[q["correct_index"]]
        random.shuffle(answers)
        q["answers"] = answers
        q["correct_index"] = answers.index(correct_text)
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
    if total == 0:
        return redirect(url_for("home"))
    if q_index >= total:
        return render_template("quiz_end.html", leaderboard=get_leaderboard(), message="Bloc terminé !", remaining_questions=len(load_questions()) - len(next(u for u in load_users() if u["pseudo"] == session["pseudo"])["asked_questions"]))
    question = questions[q_index]
    show_result = session.get("show_result", False)
    last_selected = session.get("last_selected", None)
    users = load_users()
    user = next(u for u in users if u["pseudo"] == session["pseudo"])
    current_score = user.get("score", 0)
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

    # Récupérer les infos de la question précédente
    pending_q = session.pop("pending_question_id", None)
    pending_correct = session.pop("pending_correct", None)
    session.pop("show_result", None)
    session.pop("last_selected", None)

    if pending_q is not None:
        users = load_users()
        user = next(u for u in users if u["pseudo"] == session["pseudo"])

        # Mettre à jour les questions répondues
        if pending_q not in user.get("asked_questions", []):
            user["asked_questions"].append(pending_q)

        # Mettre à jour le score
        if pending_correct:
            user["score"] = user.get("score", 0) + 1

        save_users(users)

        # Mettre à jour le leaderboard
        lb = load_leaderboard()
        lb = [e for e in lb if e["name"] != user["pseudo"]]
        lb.append({"name": user["pseudo"], "score": user["score"]})
        lb.sort(key=lambda x: x["score"], reverse=True)
        save_leaderboard(lb)

    # Passer à la question suivante
    session["q_index"] = session.get("q_index", 0) + 1
    questions = session.get("questions", [])

    # Si bloc terminé
    if session["q_index"] >= len(questions):
        users = load_users()
        user = next(u for u in users if u["pseudo"] == session["pseudo"])
        remaining_questions = len(load_questions()) - len(user.get("asked_questions", []))

        return render_template(
            "quiz_end.html",
            leaderboard=get_leaderboard(),
            message="Bloc terminé !",
            remaining_questions=remaining_questions,
            users=users  # nécessaire pour afficher le joueur hors top 10
        )

    return redirect(url_for("quiz"))


if __name__ == "__main__":
    app.jinja_env.globals.update(enumerate=enumerate)
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
