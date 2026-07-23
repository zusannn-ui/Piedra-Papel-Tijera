import os
import json
import random
from typing import Optional, Dict

class MarkovPredictor:
    def __init__(self, history_filepath: str):
        self.history_filepath = history_filepath
        self.data = {
            "state_transitions": {},  # "MOVE_outcome": {"PIEDRA": c, "PAPEL": c, "TIJERA": c}
            "move_transitions": {},   # "MOVE": {"PIEDRA": c, "PAPEL": c, "TIJERA": c}
            "global_counts": {        # {"PIEDRA": c, "PAPEL": c, "TIJERA": c}
                "PIEDRA": 0,
                "PAPEL": 0,
                "TIJERA": 0
            }
        }
        self.load_history()

    def load_history(self) -> None:
        """Loads transition history from the local JSON file."""
        if os.path.exists(self.history_filepath):
            try:
                with open(self.history_filepath, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    # Verify basic structure
                    if isinstance(loaded_data, dict):
                        for key in ["state_transitions", "move_transitions", "global_counts"]:
                            if key in loaded_data:
                                self.data[key] = loaded_data[key]
            except Exception as e:
                print(f"Error loading history file (re-initializing): {e}")
                # Keep default empty structure

    def save_history(self) -> None:
        """Saves current transition history to the local JSON file."""
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(self.history_filepath), exist_ok=True)
            with open(self.history_filepath, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving history file: {e}")

    def predict_next_human_move(self, last_human_move: Optional[str], last_outcome: Optional[str]) -> str:
        """
        Predicts the next move of the human based on transition frequencies.
        Fallback order:
        1. Second-order State Markov: (last_human_move + last_outcome) -> next_move
        2. First-order Move Markov: last_human_move -> next_move
        3. Global frequency: what move the user plays most overall
        4. Random choice (baseline bias towards Piedra/Papel/Tijera)
        """
        valid_moves = ["PIEDRA", "PAPEL", "TIJERA"]

        # 1. State transition check (e.g. "PIEDRA_lose" -> next_move)
        if last_human_move and last_outcome:
            state_key = f"{last_human_move.upper()}_{last_outcome.lower()}"
            transitions = self.data["state_transitions"].get(state_key, {})
            # Ensure there is enough sample size
            if transitions and sum(transitions.values()) >= 2:
                best_move = max(transitions, key=transitions.get)
                if transitions[best_move] > 0:
                    return best_move

        # 2. Direct move transition check (e.g. "PIEDRA" -> next_move)
        if last_human_move:
            move_key = last_human_move.upper()
            transitions = self.data["move_transitions"].get(move_key, {})
            if transitions and sum(transitions.values()) >= 2:
                best_move = max(transitions, key=transitions.get)
                if transitions[best_move] > 0:
                    return best_move

        # 3. Global frequency check
        global_cnt = self.data["global_counts"]
        if sum(global_cnt.values()) >= 3:
            best_move = max(global_cnt, key=global_cnt.get)
            if global_cnt[best_move] > 0:
                return best_move

        # 4. Default to random valid move (equal weight)
        return random.choice(valid_moves)

    def get_ai_countermove(self, last_human_move: Optional[str], last_outcome: Optional[str]) -> str:
        """
        Predicts human move and returns the winning countermove:
        - Human Rock (PIEDRA) -> AI Paper (PAPEL)
        - Human Paper (PAPEL) -> AI Scissors (TIJERA)
        - Human Scissors (TIJERA) -> AI Rock (PIEDRA)
        """
        predicted_move = self.predict_next_human_move(last_human_move, last_outcome)
        
        countermoves = {
            "PIEDRA": "PAPEL",
            "PAPEL": "TIJERA",
            "TIJERA": "PIEDRA"
        }
        return countermoves.get(predicted_move, random.choice(["PIEDRA", "PAPEL", "TIJERA"]))

    def update(self, last_human_move: Optional[str], last_outcome: Optional[str], current_human_move: str) -> None:
        """
        Updates transition counts with the user's latest move.
        Skips updating transition maps if either the current or previous moves are "NINGUNO".
        """
        current = current_human_move.upper() if current_human_move else "NINGUNO"
        if current not in ["PIEDRA", "PAPEL", "TIJERA"]:
            # Do not train on "NINGUNO" (no gesture shown)
            return

        # 1. Update global counts
        self.data["global_counts"][current] = self.data["global_counts"].get(current, 0) + 1

        # 2. Update direct move-to-move transitions
        if last_human_move and last_human_move.upper() in ["PIEDRA", "PAPEL", "TIJERA"]:
            prev_move = last_human_move.upper()
            if prev_move not in self.data["move_transitions"]:
                self.data["move_transitions"][prev_move] = {"PIEDRA": 0, "PAPEL": 0, "TIJERA": 0}
            self.data["move_transitions"][prev_move][current] = self.data["move_transitions"][prev_move].get(current, 0) + 1

            # 3. Update state-to-move transitions (incorporates outcome)
            if last_outcome:
                state_key = f"{prev_move}_{last_outcome.lower()}"
                if state_key not in self.data["state_transitions"]:
                    self.data["state_transitions"][state_key] = {"PIEDRA": 0, "PAPEL": 0, "TIJERA": 0}
                self.data["state_transitions"][state_key][current] = self.data["state_transitions"][state_key].get(current, 0) + 1

        # Save to disk
        self.save_history()
