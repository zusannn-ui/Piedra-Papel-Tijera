# Win/loss evaluation logic for Rock-Paper-Scissors vs AI

MOVES = ["PIEDRA", "PAPEL", "TIJERA", "NINGUNO"]

BEATS = {
    "PIEDRA": "TIJERA",
    "PAPEL": "PIEDRA",
    "TIJERA": "PAPEL"
}

MOVE_NAMES_ES = {
    "PIEDRA": "Piedra 🪨",
    "PAPEL": "Papel 📄",
    "TIJERA": "Tijera ✂️",
    "NINGUNO": "Ninguno ❌"
}

def evaluate_round(human_move: str, ai_move: str) -> dict:
    """
    Evaluates a single round of Rock-Paper-Scissors.
    Returns a dictionary with the winner ('human', 'ai', 'tie') and a descriptive message in Spanish.
    """
    human = human_move.upper() if human_move else "NINGUNO"
    ai = ai_move.upper() if ai_move else "NINGUNO"

    if human not in MOVES:
        human = "NINGUNO"
    if ai not in MOVES:
        ai = "NINGUNO"

    human_display = MOVE_NAMES_ES[human]
    ai_display = MOVE_NAMES_ES[ai]

    # Special handling for NINGUNO
    if human == "NINGUNO" and ai == "NINGUNO":
        return {
            "winner": "tie",
            "message": "¡Ninguno mostró una seña! Es un empate de vacíos. 🤖🤷‍♂️"
        }
    elif human == "NINGUNO":
        return {
            "winner": "ai",
            "message": f"¡No mostraste ninguna seña! La IA gana automáticamente con {ai_display}. 🧠💥"
        }
    elif ai == "NINGUNO":
        # AI shouldn't normally play NINGUNO, but handle it
        return {
            "winner": "human",
            "message": f"¡La IA se confundió y no mostró seña! Ganaste automáticamente con {human_display}. 🎉✨"
        }

    # Standard rules
    if human == ai:
        return {
            "winner": "tie",
            "message": f"¡Empate! Ambos eligieron {human_display}. 🤝"
        }
    elif BEATS[human] == ai:
        return {
            "winner": "human",
            "message": f"¡Ganaste! Tu {human_display} vence a {ai_display} de la IA. 🎉🔥"
        }
    else:
        return {
            "winner": "ai",
            "message": f"¡La IA te leyó la mente! Su {ai_display} vence a tu {human_display}. 🧠⚡"
        }
