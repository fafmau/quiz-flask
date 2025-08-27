import tkinter as tk
from tkinter import messagebox
import random
import os

# --- Charger les questions ---
def load_questions(filename):
    questions = []
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(";")
            if len(parts) >= 5:
                question = parts[0]
                answers = parts[1:5]
                correct = answers[0]
                questions.append({
                    "question": question,
                    "answers": answers,
                    "correct": correct
                })
    return questions

# --- Gérer l'historique des scores ---
SCORE_FILE = "scores.txt"

def load_scores():
    if not os.path.exists(SCORE_FILE):
        return {}
    scores = {}
    with open(SCORE_FILE, "r", encoding="utf-8") as f:
        for line in f:
            name, score = line.strip().split(";")
            scores[name] = int(score)
    return scores

def save_score(name, score):
    scores = load_scores()
    if name not in scores or score > scores[name]:
        scores[name] = score
    with open(SCORE_FILE, "w", encoding="utf-8") as f:
        for n, s in scores.items():
            f.write(f"{n};{s}\n")

# --- Jeu ---
class QCMGame:
    def __init__(self, master, questions, player_name, num_questions, return_callback):
        self.master = master
        self.master.configure(bg="#f0f8ff")
        self.questions = random.sample(questions, min(num_questions, len(questions)))
        self.score = 0
        self.index = 0
        self.player_name = player_name
        self.best_score = load_scores().get(player_name, 0)
        self.num_questions = num_questions
        self.return_callback = return_callback

        # Affichage du score
        self.score_label = tk.Label(master, text=f"Score: {self.score}/{self.num_questions} | Meilleur: {self.best_score}",
                                    font=("Helvetica", 14), fg="#16a085", bg="#f0f8ff")
        self.score_label.pack(pady=15)

        # Question
        self.question_label = tk.Label(master, text="", wraplength=450, font=("Helvetica", 16, "bold"),
                                       fg="#2c3e50", bg="#f0f8ff")
        self.question_label.pack(pady=20)

        # Boutons
        self.buttons = []
        for i in range(4):
            btn = tk.Button(master, text="", width=25, font=("Helvetica", 13), bg="#ecf0f1",
                            activebackground="#3498db", relief="ridge", bd=2,
                            command=lambda i=i: self.check_answer(i))
            btn.pack(pady=8, ipadx=5, ipady=5)
            self.buttons.append(btn)

        self.next_question()

    def next_question(self):
        if self.index >= len(self.questions):
            # Enregistrer score
            save_score(self.player_name, self.score)
            # Retour à l'accueil
            self.destroy_game_widgets()
            self.return_callback(self.player_name, self.score)
            return

        self.current_q = self.questions[self.index]
        self.question_label.config(text=self.current_q["question"])

        # Mélanger les réponses
        self.shuffled_answers = self.current_q["answers"][:]
        random.shuffle(self.shuffled_answers)
        for i, ans in enumerate(self.shuffled_answers):
            self.buttons[i].config(text=ans, bg="#ecf0f1", state="normal")

    def check_answer(self, i):
        selected = self.shuffled_answers[i]
        for btn in self.buttons:
            btn.config(state="disabled")

        if selected == self.current_q["correct"]:
            self.animate_button(self.buttons[i], "#2ecc71")
            self.score += 1
            self.master.configure(bg="#d4efdf")  # fond vert léger
        else:
            self.animate_button(self.buttons[i], "#e74c3c")
            # montrer la bonne réponse
            for j, ans in enumerate(self.shuffled_answers):
                if ans == self.current_q["correct"]:
                    self.animate_button(self.buttons[j], "#2ecc71")
                    break
            self.master.configure(bg="#f5b7b1")  # fond rouge léger

        self.score_label.config(text=f"Score: {self.score}/{self.num_questions} | Meilleur: {self.best_score}")
        self.index += 1
        self.master.after(1000, self.reset_background_and_next)

    def reset_background_and_next(self):
        self.master.configure(bg="#f0f8ff")
        self.next_question()

    def animate_button(self, btn, color):
        btn.config(bg=color)

    def destroy_game_widgets(self):
        self.score_label.destroy()
        self.question_label.destroy()
        for btn in self.buttons:
            btn.destroy()

# --- Fenêtre principale avec écran d'accueil et leaderboard ---
class QCMApp:
    def __init__(self, root, questions):
        self.root = root
        self.questions = questions
        self.root.title("🎉 Mini QCM Fun 🎉")
        self.root.geometry("550x600")
        self.root.configure(bg="#f0f8ff")
        self.current_player_score = None

        self.setup_home_screen()

    def setup_home_screen(self):
        # Écran d'accueil
        self.title_label = tk.Label(self.root, text="Bienvenue au QCM Fun !", font=("Helvetica", 18, "bold"), bg="#f0f8ff")
        self.title_label.pack(pady=20)

        self.name_label = tk.Label(self.root, text="Entrez votre nom :", font=("Helvetica", 14), bg="#f0f8ff")
        self.name_label.pack(pady=5)

        self.name_entry = tk.Entry(self.root, font=("Helvetica", 14))
        self.name_entry.pack(pady=5)

        self.start_button = tk.Button(self.root, text="Commencer", font=("Helvetica", 14), bg="#3498db", fg="white",
                                      activebackground="#2980b9", command=self.start_game)
        self.start_button.pack(pady=15)

        # Leaderboard
        self.leader_label = tk.Label(self.root, text="🏅 Meilleurs scores :", font=("Helvetica", 14, "bold"), bg="#f0f8ff")
        self.leader_label.pack(pady=10)

        self.leader_text = tk.Text(self.root, width=35, height=10, font=("Helvetica", 12), bg="#f0f8ff", bd=0)
        self.leader_text.pack()
        self.leader_text.config(state=tk.DISABLED)

        self.update_leaderboard(animated=True)

    def update_leaderboard(self, animated=False):
        scores = load_scores()
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        self.leader_text.config(state=tk.NORMAL)
        self.leader_text.delete(1.0, tk.END)
        for idx, (name, score) in enumerate(sorted_scores[:10], start=1):
            tag_name = None
            display_text = f"{idx}. {name} : {score} "
            if self.current_player_score and name == self.current_player_score[0] and score == self.current_player_score[1]:
                tag_name = "current"
                display_text += "🏅"
            self.leader_text.insert(tk.END, display_text + "\n", tag_name)
        self.leader_text.tag_configure("current", font=("Helvetica", 12, "bold"), foreground="red")
        self.leader_text.config(state=tk.DISABLED)

        if animated and self.current_player_score:
            self.animate_current_score()

    def animate_current_score(self, count=0):
        # Animation clignotante et emoji du score du joueur actuel
        if count >= 6:  # clignote 3 fois
            return
        self.leader_text.config(state=tk.NORMAL)
        color = "red" if count % 2 == 0 else "black"
        self.leader_text.tag_config("current", foreground=color)
        self.leader_text.config(state=tk.DISABLED)
        self.root.after(300, lambda: self.animate_current_score(count+1))

    def start_game(self):
        player_name = self.name_entry.get().strip()
        if not player_name:
            player_name = "Anonyme"

        # Supprimer l'écran d'accueil
        self.title_label.destroy()
        self.name_label.destroy()
        self.name_entry.destroy()
        self.start_button.destroy()
        self.leader_label.destroy()
        self.leader_text.destroy()

        # Lancer le jeu
        QCMGame(self.root, self.questions, player_name, num_questions=20, return_callback=self.return_to_home)

    def return_to_home(self, player_name, score):
        # Mettre à jour le score du joueur actuel pour l'animation
        self.current_player_score = (player_name, score)
        # Recréer l'écran d'accueil
        self.setup_home_screen()

# --- Lancer l'application ---
if __name__ == "__main__":
    questions = load_questions("Questions_QCM.txt")
    root = tk.Tk()
    app = QCMApp(root, questions)
    root.mainloop()
