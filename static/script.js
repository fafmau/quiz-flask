<script>
const buttons = document.querySelectorAll(".answer-btn");
const correctAnswer = "{{ correct }}";

buttons.forEach(btn => {
    btn.addEventListener("click", function() {
        const choice = this.dataset.value;

        // Désactiver tous les boutons
        buttons.forEach(b => b.disabled = true);

        // Vérifier la réponse
        if (choice === correctAnswer) {
            this.classList.add("correct");
            this.querySelector("span.icon").innerText = "✔";
        } else {
            this.classList.add("incorrect");
            this.querySelector("span.icon").innerText = "✖";

            // Montrer la bonne réponse
            buttons.forEach(b => {
                if (b.dataset.value === correctAnswer) {
                    b.classList.add("correct");
                    b.querySelector("span.icon").innerText = "✔";
                }
            });
        }

        // Passage à la question suivante après 0.9s
        setTimeout(() => {
            const form = document.createElement("form");
            form.method = "POST";
            form.action = "{{ url_for('answer') }}";

            const inputChoice = document.createElement("input");
            inputChoice.type = "hidden";
            inputChoice.name = "answer";
            inputChoice.value = choice;
            form.appendChild(inputChoice);

            const inputCorrect = document.createElement("input");
            inputCorrect.type = "hidden";
            inputCorrect.name = "correct";
            inputCorrect.value = correctAnswer;
            form.appendChild(inputCorrect);

            document.body.appendChild(form);
            form.submit();
        }, 900);
    });
});

let timeLeft = 12; // secondes
const timerEl = document.getElementById("timer");
const progressEl = document.getElementById("progress-bar");
const totalQuestions = {{ total }};
const currentIndex = {{ index }};

timerEl.innerText = `Temps restant : ${timeLeft} s`;
progressEl.style.width = `${((currentIndex-1)/totalQuestions)*100}%`;

let timerInterval = setInterval(() => {
    timeLeft--;
    timerEl.innerText = `Temps restant : ${timeLeft} s`;
    if(timeLeft <= 0) {
        clearInterval(timerInterval);
        // simuler mauvais choix si le temps est écoulé
        buttons.forEach(b => b.disabled = true);
        buttons.forEach(b => {
            if(b.dataset.value === "{{ correct }}") {
                b.classList.add("correct");
                b.querySelector("span.icon").innerText = "✔";
            }
        });
        setTimeout(() => {
            const form = document.createElement("form");
            form.method = "POST";
            form.action = "{{ url_for('answer') }}";

            const inputChoice = document.createElement("input");
            inputChoice.type = "hidden";
            inputChoice.name = "answer";
            inputChoice.value = ""; // aucun choix
            form.appendChild(inputChoice);

            const inputCorrect = document.createElement("input");
            inputCorrect.type = "hidden";
            inputCorrect.name = "correct";
            inputCorrect.value = "{{ correct }}";
            form.appendChild(inputCorrect);

            document.body.appendChild(form);
            progressEl.style.width = `${(currentIndex/totalQuestions)*100}%`;

            form.submit();
        }, 900);
    }
}, 1000);

</script>
