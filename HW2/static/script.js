// 5x6 Matrix Configuration
const F_LOW = [697, 770, 852, 941, 1045];
const F_HIGH = [1209, 1336, 1477, 1633, 1790, 1968];

const TURKISH_ALPHABET = [
    ['A', 'B', 'C', 'Ç', 'D', 'E'],
    ['F', 'G', 'Ğ', 'H', 'I', 'İ'],
    ['J', 'K', 'L', 'M', 'N', 'O'],
    ['Ö', 'P', 'R', 'S', 'Ş', 'T'],
    ['U', 'Ü', 'V', 'Y', 'Z', ' ']
];

// Web Audio Context setup
let audioCtx;

function initAudio() {
    if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
}

// Variables for recording
let isRecording = false;
let currentSequence = "";
let uploadedFile = null;

// DOM Elements
const dialpadContainer = document.getElementById('dialpad-container');
const btnRecord = document.getElementById('btn-record');
const btnStop = document.getElementById('btn-stop-record');
const sequenceDisplay = document.getElementById('sequence-display');

const fileUpload = document.getElementById('file-upload');
const uploadArea = document.getElementById('upload-area');
const fileNameDisplay = document.getElementById('file-name');
const btnDecode = document.getElementById('btn-decode');
const decodedDisplay = document.getElementById('decoded-display');

// Global map for keyboard integration
window.btnMap = {};

// Build the Dialpad
function buildDialpad() {
    dialpadContainer.innerHTML = '';

    // Top-left empty cell
    const emptyCell = document.createElement('div');
    emptyCell.className = 'freq-header empty';
    dialpadContainer.appendChild(emptyCell);

    // Top row headers (f_high)
    for (let c = 0; c < 6; c++) {
        const header = document.createElement('div');
        header.className = 'freq-header col-header';
        header.innerText = F_HIGH[c] + ' Hz';
        dialpadContainer.appendChild(header);
    }

    for (let r = 0; r < 5; r++) {
        // Left column header (f_low)
        const rowHeader = document.createElement('div');
        rowHeader.className = 'freq-header row-header';
        rowHeader.innerText = F_LOW[r] + ' Hz';
        dialpadContainer.appendChild(rowHeader);

        for (let c = 0; c < 6; c++) {
            const char = TURKISH_ALPHABET[r][c];
            const btn = document.createElement('button');
            btn.className = 'dial-btn';
            if (char === ' ') {
                btn.innerHTML = '&#9251;'; // Space icon
                btn.dataset.key = ' ';
            } else {
                btn.innerText = char;
                btn.dataset.key = char;
            }

            // Interaction handlers
            const playSound = (e) => {
                if (e && e.preventDefault) e.preventDefault();
                if (btn.classList.contains('active')) return; // Prevent re-trigger on hold

                initAudio();
                const oscillators = startTone(F_LOW[r], F_HIGH[c]);
                btn.classList.add('active');
                btn._oscillators = oscillators; // Store for keyup

                // LIVE VISUALIZATION FEEDBACK
                const analysisPanel = document.getElementById('analysis-panel');
                const signalChart = document.getElementById('signal-chart');
                signalChart.src = '/plot/' + encodeURIComponent(char) + '?t=' + new Date().getTime(); // Instant feedback
                analysisPanel.style.display = 'block';

                // Add to sequence if recording
                if (isRecording) {
                    currentSequence += char;
                    sequenceDisplay.innerText = currentSequence.replace(/ /g, '␣');
                }

                const stopSound = () => {
                    if (!btn._oscillators) return;
                    stopTone(btn._oscillators);
                    btn._oscillators = null;
                    btn.classList.remove('active');
                    btn.removeEventListener('mouseup', stopSound);
                    btn.removeEventListener('mouseleave', stopSound);
                    btn.removeEventListener('touchend', stopSound);
                };

                btn.addEventListener('mouseup', stopSound);
                btn.addEventListener('mouseleave', stopSound);
                btn.addEventListener('touchend', stopSound);
            };

            btn.addEventListener('mousedown', playSound);
            btn.addEventListener('touchstart', playSound, { passive: false });

            window.btnMap[char] = { btn, playSound };
            dialpadContainer.appendChild(btn);
        }
    }
}

// Keyboard Event Listeners for Physical Keys
document.addEventListener('keydown', (e) => {
    // Ignore input if user is modifying a field (though none exist except file upload)
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    if (e.repeat) return; // Prevent OS key hold repeat from firing multiple times

    let key = e.key;
    if (e.code === 'Space') {
        key = ' ';
        e.preventDefault(); // Prevent page scroll down
    }

    // Map lowercase tr chars properly
    key = key.toLocaleUpperCase('tr-TR');

    if (window.btnMap && window.btnMap[key]) {
        window.btnMap[key].playSound({ preventDefault: () => { } });
    }
});

document.addEventListener('keyup', (e) => {
    let key = e.key;
    if (e.code === 'Space') key = ' ';
    key = key.toLocaleUpperCase('tr-TR');

    if (window.btnMap && window.btnMap[key]) {
        const item = window.btnMap[key];
        const btn = item.btn;
        if (btn._oscillators) {
            stopTone(btn._oscillators);
            btn._oscillators = null;
            btn.classList.remove('active');
        }
    }
});

// Audio Synthesis for LIVE PLAYBACK only (the true WAV is generated on backend)
function startTone(fLow, fHigh) {
    const osc1 = audioCtx.createOscillator();
    const osc2 = audioCtx.createOscillator();
    const gainNode = audioCtx.createGain();

    osc1.frequency.value = fLow;
    osc2.frequency.value = fHigh;

    // Scale down volume to prevent clipping
    gainNode.gain.value = 0.25;

    osc1.connect(gainNode);
    osc2.connect(gainNode);
    gainNode.connect(audioCtx.destination);

    osc1.start();
    osc2.start();

    return { osc1, osc2, gainNode };
}

function stopTone({ osc1, osc2, gainNode }) {
    // Smooth release
    gainNode.gain.setTargetAtTime(0, audioCtx.currentTime, 0.015);
    setTimeout(() => {
        osc1.stop();
        osc2.stop();
        osc1.disconnect();
        osc2.disconnect();
    }, 50);
}

// Recording Control
btnRecord.addEventListener('click', () => {
    isRecording = true;
    currentSequence = "";
    sequenceDisplay.innerText = "Listening...";
    btnRecord.disabled = true;
    btnStop.disabled = false;
});

btnStop.addEventListener('click', async () => {
    isRecording = false;
    btnRecord.disabled = false;
    btnStop.disabled = true;

    if (currentSequence.length === 0) {
        sequenceDisplay.innerText = "No sequence recorded.";
        return;
    }

    sequenceDisplay.innerText += " (Encoding...)";

    // Send to backend specifically to get the 40ms/char generated 16-bit PCM WAV
    try {
        const formData = new FormData();
        formData.append('text', currentSequence);

        const response = await fetch('/encode', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error("Server error");

        const blob = await response.blob();

        // Trigger download
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `dtmf_${currentSequence.slice(0, 10).replace(/ /g, '_')}.wav`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        sequenceDisplay.innerText = "Current Sequence: " + currentSequence.replace(/ /g, '␣') + " ✔️ Downloaded";
    } catch (err) {
        console.error(err);
        sequenceDisplay.innerText = "Error during encoding.";
    }
});

// File Upload Drag & Drop
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
});
uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('dragover');
});
uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        handleFileSelection(e.dataTransfer.files[0]);
    }
});

fileUpload.addEventListener('change', (e) => {
    if (e.target.files && e.target.files[0]) {
        handleFileSelection(e.target.files[0]);
    }
});

function handleFileSelection(file) {
    if (!file.name.endsWith('.wav')) {
        fileNameDisplay.innerText = "Invalid file type. Please select a .wav file.";
        fileNameDisplay.style.color = 'var(--danger)';
        uploadedFile = null;
        btnDecode.disabled = true;
        return;
    }

    uploadedFile = file;
    fileNameDisplay.innerText = `Selected: ${file.name}`;
    fileNameDisplay.style.color = 'var(--text-muted)';
    btnDecode.disabled = false;
}

// Decode logic
btnDecode.addEventListener('click', async () => {
    if (!uploadedFile) return;

    decodedDisplay.innerText = "Analyzing audio... ⚡";
    btnDecode.disabled = true;

    try {
        const formData = new FormData();
        formData.append('file', uploadedFile);

        const response = await fetch('/decode', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error("Server decoding error");
        const json = await response.json();

        // Render
        const text = json.decoded_text;
        decodedDisplay.innerText = text ? text : "[No recognizable sequence found]";

    } catch (err) {
        console.error(err);
        decodedDisplay.innerText = "Failed to decode the file.";
    } finally {
        btnDecode.disabled = false; // re-enable
    }
});

// Init
buildDialpad();
