import os
import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager

from src.backend.config import HISTORY_FILE
from src.backend.camera_manager import CameraManager
from src.backend.predictor import MarkovPredictor
from src.backend.game_logic import evaluate_round

# Create shared instances
camera_manager = CameraManager()
predictor = MarkovPredictor(HISTORY_FILE)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start camera background thread
    print("Starting camera manager...")
    camera_manager.start()
    yield
    # Shutdown: Stop camera thread
    print("Stopping camera manager...")
    camera_manager.stop()

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
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/video_feed")
async def video_feed():
    """Streams the real-time camera feed to the browser."""
    async def frame_generator():
        while True:
            jpeg = camera_manager.get_latest_jpeg()
            if jpeg:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg + b'\r\n')
            await asyncio.sleep(0.04)  # ~25 FPS to save bandwidth and keep CPU happy

    return StreamingResponse(
        frame_generator(), 
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

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
    
    # State tracker to pause gesture updates during active countdown
    is_counting_down = False

    async def gesture_sender():
        nonlocal is_counting_down
        last_g = None
        try:
            while True:
                if not is_counting_down:
                    g = camera_manager.get_latest_gesture()
                    if g != last_g:
                        await websocket.send_json({
                            "event": "gesture_update",
                            "gesture": g
                        })
                        last_g = g
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Error in gesture_sender: {e}")

    async def message_receiver():
        nonlocal session_scores, last_human_move, last_outcome, is_counting_down
        try:
            while True:
                # Read messages from the user
                data = await websocket.receive_text()
                payload = json.loads(data)
                event = payload.get("event")

                if event == "start_countdown":
                    is_counting_down = True
                    # Step 1: Countdown broadcasting (3 -> 2 -> 1)
                    for tick in [3, 2, 1]:
                        await websocket.send_json({
                            "event": "countdown",
                            "tick": tick
                        })
                        await asyncio.sleep(1)

                    # Step 2: Instant locking of AI Move (at tick 0, BEFORE reading human hand)
                    ai_move = predictor.get_ai_countermove(last_human_move, last_outcome)

                    # Step 3: Capture immediate human hand gesture at tick 0
                    human_move = camera_manager.get_latest_gesture()

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
                    is_counting_down = False

                elif event == "reset_scores":
                    session_scores = {"human": 0, "ai": 0, "ties": 0}
                    last_human_move = None
                    last_outcome = None
                    await websocket.send_json({
                        "event": "scores_reset",
                        "scores": session_scores
                    })
        except WebSocketDisconnect:
            pass
        except Exception as e:
            print(f"Error in message_receiver: {e}")

    # Spawn tasks
    sender_task = asyncio.create_task(gesture_sender())
    receiver_task = asyncio.create_task(message_receiver())

    try:
        # Run until client disconnects or connection is lost
        await asyncio.gather(sender_task, receiver_task)
    except Exception as e:
        pass
    finally:
        sender_task.cancel()
        receiver_task.cancel()
        print("WebSocket tasks cleaned up and connection closed.")

