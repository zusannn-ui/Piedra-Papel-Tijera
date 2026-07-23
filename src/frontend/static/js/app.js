'use strict';

// ══════════════════════════════════════════════════════════
// Constants
// ══════════════════════════════════════════════════════════
const MOVE_META = {
    PIEDRA: { faIcon: 'fa-hand-fist',     mvClass: 'mv-piedra', label: 'PIEDRA' },
    PAPEL:  { faIcon: 'fa-hand',          mvClass: 'mv-papel',  label: 'PAPEL'  },
    TIJERA: { faIcon: 'fa-hand-scissors', mvClass: 'mv-tijera', label: 'TIJERA' },
    NINGUNO:{ faIcon: 'fa-ban',           mvClass: '',          label: 'NINGUNO'}
};

const GESTURE_META = {
    PIEDRA:  { faIcon: 'fa-hand-fist',     gClass: 'g-piedra', text: 'Piedra'   },
    PAPEL:   { faIcon: 'fa-hand',          gClass: 'g-papel',  text: 'Papel'    },
    TIJERA:  { faIcon: 'fa-hand-scissors', gClass: 'g-tijera', text: 'Tijera'   },
    NINGUNO: { faIcon: 'fa-hand',          gClass: '',         text: 'Buscando mano...' }
};

// ══════════════════════════════════════════════════════════
// State
// ══════════════════════════════════════════════════════════
let socket          = null;
let isPlaying       = false;
let reconnectTimer  = null;
let resultIdleTimer = null;

// ══════════════════════════════════════════════════════════
// DOM References
// ══════════════════════════════════════════════════════════
const webcamFeed          = document.getElementById('webcam-feed');
const cameraErrorOverlay  = document.getElementById('camera-error-overlay');
const countdownOverlay    = document.getElementById('countdown-overlay');
const countdownText       = document.getElementById('countdown-text');
const gestureBadge        = document.getElementById('gesture-badge');
const gestureIcon         = document.getElementById('gesture-icon');
const gestureText         = document.getElementById('gesture-text');
const btnPlay             = document.getElementById('btn-play');
const btnReset            = document.getElementById('btn-reset');
const playerScore         = document.getElementById('player-score');
const aiScore             = document.getElementById('ai-score');
const playerLastMove      = document.getElementById('player-last-move');
const aiLastMove          = document.getElementById('ai-last-move');
const statRounds          = document.getElementById('stat-rounds');
const statTies            = document.getElementById('stat-ties');
const statWinrate         = document.getElementById('stat-winrate');
const statAccuracy        = document.getElementById('stat-accuracy');
const resultMessageWrap   = document.getElementById('result-message-wrap');
const resultMessageText   = document.getElementById('result-message-text');
const connDot             = document.getElementById('conn-dot');
const connText            = document.getElementById('conn-text');
const humanColumn         = document.getElementById('human-column');
const aiColumn            = document.getElementById('ai-column');

// AI state elements
const aiIdle              = document.getElementById('ai-idle');
const aiThinking          = document.getElementById('ai-thinking');
const aiResult            = document.getElementById('ai-result');
const resultMoveIcon      = document.getElementById('result-move-icon');
const resultRevealWrap    = document.getElementById('result-reveal-wrap');
const resultMoveLabel     = document.getElementById('result-move-label');
const resultAnimationOverlay = document.getElementById('result-animation-overlay');

// ══════════════════════════════════════════════════════════
// AI State Machine
// ══════════════════════════════════════════════════════════
/**
 * Transitions the AI panel between its three visual states:
 *   'idle'     → ready / ambient rings + brain icon
 *   'thinking' → spinning rings + scan line (mind-reading animation)
 *   'result'   → reveals locked move icon with animated pop
 */
function setAIState(state, move = null) {
    // Deactivate all states
    aiIdle.classList.remove('ai-active');
    aiThinking.classList.remove('ai-active');
    aiResult.classList.remove('ai-active');

    if (state === 'idle') {
        aiIdle.classList.add('ai-active');

    } else if (state === 'thinking') {
        aiThinking.classList.add('ai-active');

    } else if (state === 'result' && move) {
        const meta = MOVE_META[move.toUpperCase()] || MOVE_META.NINGUNO;

        // Set the FontAwesome icon class + move colour class
        resultMoveIcon.className = `fa-solid ${meta.faIcon} result-move-icon ${meta.mvClass}`;

        // Label text
        resultMoveLabel.textContent = meta.label;

        // Re-trigger the pop animation on every reveal
        resultMoveIcon.style.animation = 'none';
        resultMoveIcon.offsetHeight;           // force reflow
        resultMoveIcon.style.animation = null;

        aiResult.classList.add('ai-active');
    }
}

// ══════════════════════════════════════════════════════════
// Column Winner / Loser Highlights
// ══════════════════════════════════════════════════════════
const COL_CLASSES = ['col-win', 'col-lose', 'col-tie'];

function applyColumnHighlight(winner) {
    // Strip previous highlight classes
    humanColumn.classList.remove(...COL_CLASSES);
    aiColumn.classList.remove(...COL_CLASSES);

    if (winner === 'human') {
        humanColumn.classList.add('col-win');
        aiColumn.classList.add('col-lose');
    } else if (winner === 'ai') {
        aiColumn.classList.add('col-win');
        humanColumn.classList.add('col-lose');
    } else {
        humanColumn.classList.add('col-tie');
        aiColumn.classList.add('col-tie');
    }

    // Auto-clear after animation finishes (1.3 s)
    setTimeout(() => {
        humanColumn.classList.remove(...COL_CLASSES);
        aiColumn.classList.remove(...COL_CLASSES);
    }, 1400);
}

// ══════════════════════════════════════════════════════════
// Gesture Badge
// ══════════════════════════════════════════════════════════
function updateGestureBadge(gesture) {
    if (isPlaying) return; // freeze during countdown
    const meta = GESTURE_META[gesture] || GESTURE_META.NINGUNO;
    gestureIcon.className = `fa-solid ${meta.faIcon}`;
    gestureText.textContent = meta.text;
    gestureBadge.className = `gesture-badge ${meta.gClass}`;
}

// ══════════════════════════════════════════════════════════
// Countdown Display
// ══════════════════════════════════════════════════════════
function showCountdown(tick) {
    countdownOverlay.classList.remove('hidden');
    countdownText.textContent = tick;
    // Restart CSS animation on every tick
    countdownText.style.animation = 'none';
    countdownText.offsetHeight;
    countdownText.style.animation = null;
}

function hideCountdown() {
    countdownOverlay.classList.add('hidden');
}

// ══════════════════════════════════════════════════════════
// Score Animation
// ══════════════════════════════════════════════════════════
function animateScore(el, newVal) {
    if (parseInt(el.textContent) !== newVal) {
        el.textContent = newVal;
        el.classList.add('pop');
        setTimeout(() => el.classList.remove('pop'), 320);
    }
}

// ══════════════════════════════════════════════════════════
// Connection Status UI
// ══════════════════════════════════════════════════════════
function setConnectionUI(state) {
    if (state === 'connected') {
        connDot.className = 'conn-dot live';
        connText.textContent = 'Conectado';
        enableControls();
    } else {
        connDot.className = 'conn-dot dead';
        connText.textContent = 'Reconectando...';
        disableControls();
    }
}

function disableControls() {
    btnPlay.disabled = true;
    btnPlay.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Conectando...';
}

function enableControls() {
    btnPlay.disabled = false;
    btnPlay.innerHTML = '<i class="fa-solid fa-play"></i> Iniciar Ronda';
}

// ══════════════════════════════════════════════════════════
// Camera Error
// ══════════════════════════════════════════════════════════
function handleCameraError() {
    webcamFeed.classList.add('hidden');
    cameraErrorOverlay.classList.remove('hidden');
}

// ══════════════════════════════════════════════════════════
// Game Actions
// ══════════════════════════════════════════════════════════
function triggerRound() {
    if (isPlaying || !socket || socket.readyState !== WebSocket.OPEN) return;

    isPlaying = true;
    btnPlay.disabled = true;
    btnReset.disabled = true;

    // Cancel any pending return to idle
    if (resultIdleTimer) { clearTimeout(resultIdleTimer); resultIdleTimer = null; }

    // Immediately switch AI to "thinking" state
    setAIState('thinking');

    // Reset result message styling
    resultMessageWrap.className = 'result-message-wrap';
    resultMessageText.textContent = 'Mantén tu mano visible...';

    socket.send(JSON.stringify({ event: 'start_countdown' }));
}

function triggerReset() {
    if (isPlaying || !socket || socket.readyState !== WebSocket.OPEN) return;
    socket.send(JSON.stringify({ event: 'reset_scores' }));
}

// ══════════════════════════════════════════════════════════
// Round Result Rendering
// ══════════════════════════════════════════════════════════
function renderRoundResult(data) {
    const { human_move, ai_move, winner, message, scores } = data;

    isPlaying = false;
    btnPlay.disabled = false;
    btnReset.disabled = false;

    // Reveal AI's locked move
    setAIState('result', ai_move);

    // Border flash on winning/losing column
    applyColumnHighlight(winner);

    // Result message
    const msgClass = winner === 'human' ? 'msg-win' : winner === 'ai' ? 'msg-lose' : 'msg-tie';
    resultMessageWrap.className = `result-message-wrap ${msgClass}`;
    
    let displayMessage = "EMPATE";
    let animClass = "anim-tie";
    if (winner === 'human') {
        displayMessage = "¡GANASTE!";
        animClass = "anim-win";
        AudioFX.win();
    } else if (winner === 'ai') {
        displayMessage = "¡PERDISTE!";
        animClass = "anim-lose";
        AudioFX.lose();
    } else {
        AudioFX.tie();
    }
    resultMessageText.textContent = displayMessage;

    // Trigger full-screen animation overlay
    resultAnimationOverlay.className = `show ${animClass}`;
    setTimeout(() => {
        resultAnimationOverlay.className = '';
    }, 1500);

    // Last moves
    playerLastMove.textContent = MOVE_META[human_move]?.label ?? '—';
    aiLastMove.textContent     = MOVE_META[ai_move]?.label    ?? '—';

    // Scores
    animateScore(playerScore, scores.human);
    animateScore(aiScore, scores.ai);

    // Stats
    const total = scores.human + scores.ai + scores.ties;
    statRounds.textContent   = total;
    statTies.textContent     = scores.ties;
    statWinrate.textContent  = total > 0 ? `${Math.round((scores.human / total) * 100)}%` : '0%';
    statAccuracy.textContent = total > 0 ? `${Math.round((scores.ai    / total) * 100)}%` : '0%';

    // Return to idle after displaying result (5 s)
    resultIdleTimer = setTimeout(() => {
        setAIState('idle');
        resultIdleTimer = null;
    }, 5000);
}

// ══════════════════════════════════════════════════════════
// Reset Rendering
// ══════════════════════════════════════════════════════════
function renderReset(scores) {
    playerScore.textContent = scores.human;
    aiScore.textContent     = scores.ai;
    statRounds.textContent  = '0';
    statTies.textContent    = '0';
    statWinrate.textContent = '0%';
    statAccuracy.textContent= '0%';
    playerLastMove.textContent = '—';
    aiLastMove.textContent     = '—';

    resultMessageWrap.className = 'result-message-wrap';
    resultMessageText.textContent = 'Marcador reiniciado. ¡Comienza de nuevo!';

    setAIState('idle');
}

// ══════════════════════════════════════════════════════════
// WebSocket Event Dispatcher
// ══════════════════════════════════════════════════════════
function handleSocketEvent(payload) {
    switch (payload.event) {
        case 'countdown':
            showCountdown(payload.tick);
            AudioFX.countdown();
            break;

        case 'round_result':
            hideCountdown();
            renderRoundResult(payload);
            break;

        case 'scores_reset':
            renderReset(payload.scores);
            break;
        // Notice: We no longer receive 'gesture_update' from the server, as it's computed locally.
    }
}

// ══════════════════════════════════════════════════════════
// WebSocket Lifecycle
// ══════════════════════════════════════════════════════════
function connectWebSocket() {
    if (socket && (socket.readyState === WebSocket.OPEN ||
                   socket.readyState === WebSocket.CONNECTING)) return;

    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    socket = new WebSocket(`${proto}//${window.location.host}/ws/game`);

    socket.onopen = () => {
        setConnectionUI('connected');
        if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null; }
    };

    socket.onmessage = (evt) => {
        try { handleSocketEvent(JSON.parse(evt.data)); }
        catch (e) { console.warn('Bad WS message', e); }
    };

    socket.onclose = () => {
        setConnectionUI('disconnected');
        reconnectTimer = setTimeout(connectWebSocket, 3000);
    };

    socket.onerror = (err) => console.error('WebSocket error:', err);
}

// ══════════════════════════════════════════════════════════
// Event Listeners
// ══════════════════════════════════════════════════════════
btnPlay.addEventListener('click', triggerRound);
btnReset.addEventListener('click', triggerReset);

// Landing Screen Elements
const landingScreen = document.getElementById('landing-screen');
const btnStartGame = document.getElementById('btn-start-game');
const btnInstructions = document.getElementById('btn-instructions');
const instructionsModal = document.getElementById('instructions-modal');
const btnCloseModal = document.getElementById('btn-close-modal');

// Landing screen logic
btnStartGame.addEventListener('click', () => {
    landingScreen.classList.add('hidden');
});

// ══════════════════════════════════════════════════════════
// Fullscreen Toggle
// ══════════════════════════════════════════════════════════
const btnFullscreen  = document.getElementById('btn-fullscreen');
const fullscreenIcon = document.getElementById('fullscreen-icon');

function updateFullscreenIcon() {
    const isFull = !!document.fullscreenElement;
    fullscreenIcon.className = isFull ? 'fa-solid fa-compress' : 'fa-solid fa-expand';
    btnFullscreen.title = isFull ? 'Salir de pantalla completa' : 'Pantalla completa';
}

function toggleFullscreen() {
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(err => {
            console.warn('No se pudo activar pantalla completa:', err);
        });
    } else {
        document.exitFullscreen();
    }
    initAudio(); // Unlock audio context on user gesture
}

btnFullscreen.addEventListener('click', () => {
    toggleFullscreen();
});

document.addEventListener('fullscreenchange', updateFullscreenIcon);

// Instructions modal logic
btnInstructions.addEventListener('click', () => {
    instructionsModal.classList.remove('hidden');
});

btnCloseModal.addEventListener('click', () => {
    instructionsModal.classList.add('hidden');
});

instructionsModal.addEventListener('click', (e) => {
    if (e.target === instructionsModal) {
        instructionsModal.classList.add('hidden');
    }
});

window.addEventListener('keydown', (e) => {
    if (e.code === 'Space') {
        e.preventDefault();
        
        // If landing screen is active, space hides it
        if (!landingScreen.classList.contains('hidden')) {
            landingScreen.classList.add('hidden');
        } else if (!instructionsModal.classList.contains('hidden')) {
            instructionsModal.classList.add('hidden');
        } else {
            // In-game, space triggers a round
            triggerRound();
        }
    }

    // F key toggles fullscreen
    if (e.code === 'KeyF' && !e.ctrlKey && !e.altKey && !e.metaKey) {
        e.preventDefault();
        toggleFullscreen();
    }
});

// ══════════════════════════════════════════════════════════
// Bootstrap
// ══════════════════════════════════════════════════════════
connectWebSocket();
setAIState('idle'); // start in idle state

// ══════════════════════════════════════════════════════════
// Audio Manager (Web Audio API Synthesizer + Real Samples)
// ══════════════════════════════════════════════════════════
let audioCtx = null;

// Preload the real crowd MP3 files into AudioBuffers
const crowdBuffers = { applause: null, booing: null };

async function loadCrowdSounds() {
    const files = {
        applause: '/static/sounds/applause.mp3',
        booing:   '/static/sounds/booing.mp3',
    };
    for (const [key, url] of Object.entries(files)) {
        try {
            const response = await fetch(url);
            const arrayBuffer = await response.arrayBuffer();
            // Decode once audioCtx is available; defer until first interaction
            crowdBuffers[key] = arrayBuffer; // store raw ArrayBuffer; decode on demand
        } catch (err) {
            console.warn(`Could not preload ${key}:`, err);
        }
    }
}
loadCrowdSounds();

// Play a preloaded crowd sound from its ArrayBuffer
async function playCrowdSound(key, volume = 1.0) {
    if (!audioCtx || !crowdBuffers[key]) return;
    try {
        const audioBuffer = await audioCtx.decodeAudioData(crowdBuffers[key].slice(0));
        const source = audioCtx.createBufferSource();
        source.buffer = audioBuffer;
        const gainNode = audioCtx.createGain();
        gainNode.gain.setValueAtTime(volume, audioCtx.currentTime);
        source.connect(gainNode);
        gainNode.connect(audioCtx.destination);
        source.start();
    } catch (err) {
        console.warn('Error playing crowd sound:', err);
    }
}

function initAudio() {
    if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (audioCtx.state === 'suspended') {
        audioCtx.resume();
    }
}

function playSound(type, freq, duration, vol=0.1, slideFreq=null) {
    if (!audioCtx) return;
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    
    osc.type = type;
    osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
    if (slideFreq) {
        osc.frequency.exponentialRampToValueAtTime(slideFreq, audioCtx.currentTime + duration);
    }
    
    gain.gain.setValueAtTime(vol, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + duration);
    
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    
    osc.start();
    osc.stop(audioCtx.currentTime + duration);
}

const AudioFX = {
    click: () => {
        initAudio();
        playSound('square', 800, 0.1, 0.05, 400); 
    },
    hover: () => {
        initAudio();
        playSound('sine', 1200, 0.05, 0.02);
    },

    // ——— VICTORY: fanfare + real crowd applause ———
    win: () => {
        initAudio();
        // Quick victory fanfare jingle
        playSound('square', 440, 0.15, 0.08); 
        setTimeout(() => playSound('square', 554, 0.15, 0.08), 100); 
        setTimeout(() => playSound('square', 659, 0.3,  0.08), 200); 
        setTimeout(() => playSound('square', 880, 0.4,  0.10), 300);
        // Real crowd applause after fanfare
        setTimeout(() => playCrowdSound('applause', 0.85), 600);
    },

    // ——— DEFEAT: sad jingle + real crowd booing ———
    lose: () => {
        initAudio();
        // Sad jingle
        playSound('sawtooth', 300, 0.3, 0.08, 150);
        setTimeout(() => playSound('sawtooth', 150, 0.4, 0.08, 50), 300);
        // Real crowd booing after jingle
        setTimeout(() => playCrowdSound('booing', 0.80), 600);
    },

    tie: () => {
        initAudio();
        playSound('triangle', 330, 0.2, 0.1);
        setTimeout(() => playSound('triangle', 330, 0.3, 0.1), 250);
    },
    countdown: () => {
        initAudio();
        playSound('sine', 880, 0.1, 0.05); 
    }
};

// Bind audio to all interactive elements
document.querySelectorAll('button, .btn, .brutal-btn').forEach(btn => {
    btn.addEventListener('mouseenter', AudioFX.hover);
    btn.addEventListener('click', AudioFX.click);
});

// ══════════════════════════════════════════════════════════
// Camera & MediaPipe Hands (Client-Side CV)
// ══════════════════════════════════════════════════════════
const canvasElement = document.getElementById('output-canvas');
const canvasCtx = canvasElement.getContext('2d');
let latestLocalGesture = 'NINGUNO';

// Initialize MediaPipe Hands
const hands = new Hands({locateFile: (file) => {
    return `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`;
}});

hands.setOptions({
    maxNumHands: 1,
    modelComplexity: 1,
    minDetectionConfidence: 0.7,
    minTrackingConfidence: 0.5
});

hands.onResults(onResults);

const camera = new Camera(webcamFeed, {
    onFrame: async () => {
        await hands.send({image: webcamFeed});
    },
    width: 640,
    height: 480
});

// Start the camera. If it fails, show error overlay.
camera.start().catch(err => {
    console.error("Camera error:", err);
    handleCameraError();
});

function onResults(results) {
    // Sync canvas size to video size
    if (canvasElement.width !== webcamFeed.videoWidth) {
        canvasElement.width = webcamFeed.videoWidth;
        canvasElement.height = webcamFeed.videoHeight;
    }
    
    canvasCtx.save();
    canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);

    let detectedGesture = 'NINGUNO';

    if (results.multiHandLandmarks && results.multiHandLandmarks.length > 0) {
        const landmarks = results.multiHandLandmarks[0];
        
        // Draw landmarks
        drawConnectors(canvasCtx, landmarks, HAND_CONNECTIONS, {color: '#00FF00', lineWidth: 5});
        drawLandmarks(canvasCtx, landmarks, {color: '#FF0000', lineWidth: 2});

        // Gesture heuristic mapping (translated from Python logic)
        if (landmarks.length >= 21) {
            const indexOpen = landmarks[8].y < landmarks[6].y;
            const middleOpen = landmarks[12].y < landmarks[10].y;
            const ringOpen = landmarks[16].y < landmarks[14].y;
            const pinkyOpen = landmarks[20].y < landmarks[18].y;

            if (indexOpen && middleOpen && ringOpen && pinkyOpen) {
                detectedGesture = 'PAPEL';
            } else if (!indexOpen && !middleOpen && !ringOpen && !pinkyOpen) {
                detectedGesture = 'PIEDRA';
            } else if (indexOpen && middleOpen && !ringOpen && !pinkyOpen) {
                detectedGesture = 'TIJERA';
            }
        }
    }
    
    canvasCtx.restore();

    // Broadcast gesture change locally and to the server
    if (detectedGesture !== latestLocalGesture) {
        latestLocalGesture = detectedGesture;
        updateGestureBadge(detectedGesture);
        
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({
                event: 'gesture_update',
                gesture: detectedGesture
            }));
        }
    }
}
