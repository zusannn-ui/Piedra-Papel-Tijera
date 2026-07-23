# Rock, Paper, Scissors vs. Predictive AI (Computer Vision)

A 100% offline, ultra-fast local web application where a player competes against a predictive AI that tries to "read their mind". The system uses **MediaPipe Hands** and **OpenCV** to process the webcam feed in real-time and classify gestures, combined with a **second-order Markov Chain model** to guess and counter the player's next move.

---

## Architecture
```text
stone-paper-scissors-ai/
├── data/
│   └── history.json          # Offline local JSON tracking transition frequencies
├── src/
│   ├── __init__.py
│   ├── backend/
│   │   ├── __init__.py
│   │   ├── camera_manager.py # Threaded webcam capture & gesture processing
│   │   ├── config.py         # App configurations (camera index, resolution, FPS)
│   │   ├── game_logic.py     # Win/loss evaluation matrix
│   │   ├── hand_detector.py  # OpenCV + MediaPipe Hands gesture engine
│   │   └── predictor.py      # Offline Markov Chain frequency predictor
│   └── frontend/
│       ├── static/
│       │   ├── css/
│       │   │   └── styles.css # Clean layout, contrasting dark/pink aesthetic elements
│       │   └── js/
│       │       └── app.js     # WebSocket connection & countdown state machine
│       └── templates/
│           └── index.html     # Main UI rendering webcam feed and scores
├── main.py                   # FastAPI application router & lifespan manager
├── requirements.txt          # Python packages (fastapi, uvicorn, opencv-python, mediapipe, jinja2)
└── README.md
```

---

## Features
1. **Real-time Gesture Recognition**: OpenCV captures frames at 30 FPS, mirrors them for natural interaction, and runs MediaPipe Hands to detect index, middle, ring, and pinky finger open/closed state.
2. **Cheat Prevention**: At countdown tick 0 ("¡Ya!"), the backend locks the AI's predicted countermove *before* reading the user's hand gesture from the webcam.
3. **Mind-Reading Algorithm**: A second-order Markov Chain model tracks transition frequencies: `(last_human_move, last_outcome) -> next_human_move`. Fallbacks include direct transitions `last_human_move -> next_human_move`, global frequencies, and random choice.
4. **Vibrant Cyberpunk UI**: Built with HTML, JS, and CSS, incorporating a hot-pink-on-obsidian aesthetic, neon glows, glassmorphic dashboards, and custom animations.
5. **No Internet Required**: 100% offline. Transition patterns are persisted locally to `data/history.json`.

---

## Setup & Running Instructions

### 1. Prerequisites
Make sure Python 3.9+ is installed.

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Server
Launch the FastAPI uvicorn development server:
```bash
python -m uvicorn main:app --reload
```
Alternatively, just run:
```bash
uvicorn main:app --reload
```

### 4. Play the Game
* Open your browser and navigate to `http://localhost:8000`.
* Position yourself so your hand is visible in the video feed container.
* Click **Iniciar Ronda** or press the **Spacebar** key.
* A 3-second countdown will overlay the stream. Hold your gesture (Piedra, Papel, or Tijera) steady at tick 0 ("¡Ya!").
* The results, scoreboard, and AI mind-reading accuracy will update instantly!
