import os
import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager

from src.backend.config import HISTORY_FILE
from src.backend.predictor import MarkovPredictor
from src.backend.game_logic import evaluate_round

# Create shared instances
predictor = MarkovPredictor(HISTORY_FILE)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic (if any)
    yield
    # Shutdown logic (if any)

app = FastAPI(
    title="Rock, Paper, Scissors AI Game",
    lifespan=lifespan
)

# Resolve paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(BASE_DIR, "src", "frontend", "static")
templates_dir = os.path.join(BASE_DIR, "src", "frontend", "templates")

# Mount static files
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Templates
templates = Jinja2Templates(directory=templates_dir)

@app.get("/")
async def get_index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.websocket("/ws/game")
async def websocket_game(websocket: WebSocket):
    """
    Manages the game state machine over WebSocket.
    """
    await websocket.accept()
    print("WebSocket connection established.")

    # Connection-scoped session statistics and state
    session_scores = {"human": 0, "ai": 0, "ties": 0}
    last_human_move = None
    last_outcome = None
    
    # Track the latest gesture sent by the client
    latest_client_gesture = "NINGUNO"

    try:
        while True:
            # Read messages from the user
            data = await websocket.receive_text()
            payload = json.loads(data)
            event = payload.get("event")

            if event == "gesture_update":
                # The client continuously sends what it sees
                latest_client_gesture = payload.get("gesture", "NINGUNO")

            elif event == "start_countdown":
                # Step 1: Countdown broadcasting (3 -> 2 -> 1)
                for tick in [3, 2, 1]:
                    await websocket.send_json({
                        "event": "countdown",
                        "tick": tick
                    })
                    await asyncio.sleep(1)

                # Step 2: Instant locking of AI Move (at tick 0, BEFORE reading human hand)
                ai_move = predictor.get_ai_countermove(last_human_move, last_outcome)

                # Step 3: Capture immediate human hand gesture at tick 0 (from the latest client update)
                human_move = latest_client_gesture

                # Step 4: Evaluate winner and details
                result = evaluate_round(human_move, ai_move)
                winner = result["winner"]

                # Step 5: Asynchronously push state to Markov predictor
                if human_move in ["PIEDRA", "PAPEL", "TIJERA"]:
                    predictor.update(last_human_move, last_outcome, human_move)
                    
                    # Advance session memory
                    last_human_move = human_move
                    last_outcome = winner

                # Update session score
                if winner == "human":
                    session_scores["human"] += 1
                elif winner == "ai":
                    session_scores["ai"] += 1
                else:
                    session_scores["ties"] += 1

                # Send comprehensive round results to client
                await websocket.send_json({
                    "event": "round_result",
                    "tick": 0,
                    "human_move": human_move,
                    "ai_move": ai_move,
                    "winner": winner,
                    "message": result["message"],
                    "scores": session_scores
                })

            elif event == "reset_scores":
                session_scores = {"human": 0, "ai": 0, "ties": 0}
                last_human_move = None
                last_outcome = None
                await websocket.send_json({
                    "event": "scores_reset",
                    "scores": session_scores
                })
    except WebSocketDisconnect:
        print("WebSocket disconnected.")
    except Exception as e:
        print(f"Error in websocket loop: {e}")
    finally:
        print("WebSocket connection closed.")

