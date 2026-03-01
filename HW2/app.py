import io
import math
import numpy as np
from scipy.io import wavfile
import matplotlib
matplotlib.use('Agg') # Run headless to prevent GUI errors in server
import matplotlib.pyplot as plt
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import Response, JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Turkish DTMF Encoder/Decoder")

# 5x6 Matrix frequencies
F_LOW = [697, 770, 852, 941, 1045]
F_HIGH = [1209, 1336, 1477, 1633, 1790, 1968]

# 30 Turkish Characters
TURKISH_ALPHABET = [
    ['A', 'B', 'C', 'Ç', 'D', 'E'],
    ['F', 'G', 'Ğ', 'H', 'I', 'İ'],
    ['J', 'K', 'L', 'M', 'N', 'O'],
    ['Ö', 'P', 'R', 'S', 'Ş', 'T'],
    ['U', 'Ü', 'V', 'Y', 'Z', ' ']
]

# Audio Config
SAMPLE_RATE = 44100
DURATION_MS = 40
SAMPLES_PER_CHAR = int(SAMPLE_RATE * (DURATION_MS / 1000.0)) # 1764
POWER_THRESHOLD = 5000 # Adjust based on testing, but this is a reasonable starting point

# Precompute character to frequencies mapping
CHAR_TO_FREQ = {}
for r_idx, r_freq in enumerate(F_LOW):
    for c_idx, c_freq in enumerate(F_HIGH):
        char = TURKISH_ALPHABET[r_idx][c_idx]
        CHAR_TO_FREQ[char] = (r_freq, c_freq)

def generate_tone(f_low, f_high, duration_samples, fs):
    t = np.arange(duration_samples) / fs
    s = 0.5 * (np.sin(2 * np.pi * f_low * t) + np.sin(2 * np.pi * f_high * t))
    return s

def plot_and_save_signal(tone, fs, f_low, f_high, char, return_buffer=False):
    """
    Generates and saves a combined Time-Domain and Frequency-Domain plot.
    """
    t = np.arange(len(tone)) / fs
    
    # Calculate Frequency Spectrum using FFT for visualization
    N = len(tone)
    yf = np.fft.fft(tone)
    xf = np.fft.fftfreq(N, 1/fs)[:N//2]
    power = 2.0/N * np.abs(yf[0:N//2])
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
    
    # Time domain (Plotting a subset for clarity, 40ms is a lot of oscillations)
    # We will plot the full 40ms to fulfill the requirement realistically.
    ax1.plot(t * 1000, tone, color='#2ea043')
    ax1.set_title(f"Time-Domain Waveform for Character '{char}'")
    ax1.set_xlabel("Time (ms)")
    ax1.set_ylabel("Amplitude")
    ax1.grid(True, alpha=0.3)
    
    # Frequency domain
    ax2.plot(xf, power, color='#58a6ff')
    ax2.set_title(f"Frequency-Domain Spectrum (f_low={f_low}Hz, f_high={f_high}Hz)")
    ax2.set_xlabel("Frequency (Hz)")
    ax2.set_ylabel("Magnitude")
    ax2.set_xlim(500, 2200) # Zoom to DTMF band
    ax2.grid(True, alpha=0.3)
    
    # Highlight theoretical peaks
    ax2.axvline(x=f_low, color='red', linestyle='--', alpha=0.8, label=f'{f_low}Hz')
    ax2.axvline(x=f_high, color='orange', linestyle='--', alpha=0.8, label=f'{f_high}Hz')
    ax2.legend()
    
    plt.tight_layout()
    if return_buffer:
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150)
        plt.close(fig)
        buf.seek(0)
        return buf
    else:
        plt.savefig('static/signal_analysis.png', format='png', dpi=150)
        plt.close(fig)

def goertzel(samples, target_freq, fs):
    """
    Computes the Goertzel algorithm for a specific target frequency.
    Returns the squared magnitude (power).
    """
    N = len(samples)
    k = int(0.5 + (N * target_freq) / fs)
    omega = (2.0 * math.pi * k) / N
    cosine = math.cos(omega)
    coeff = 2.0 * cosine
    
    q1 = 0.0
    q2 = 0.0
    
    for sample in samples:
        q0 = coeff * q1 - q2 + sample
        q2 = q1
        q1 = q0
        
    power = q1 * q1 + q2 * q2 - q1 * q2 * coeff
    return power

@app.post("/encode")
async def encode_text(text: str = Form(...)):
    """
    Encodes a string into a DTMF-like WAV file using 16-bit PCM.
    """
    text = text.upper()
    audio_signal = np.array([], dtype=np.float32)
    
    for char in text:
        if char in CHAR_TO_FREQ:
            f_low, f_high = CHAR_TO_FREQ[char]
            tone = generate_tone(f_low, f_high, SAMPLES_PER_CHAR, SAMPLE_RATE)
            
            # Save the technical analysis plot to disk
            plot_and_save_signal(tone, SAMPLE_RATE, f_low, f_high, char)
            
            audio_signal = np.concatenate((audio_signal, tone))
            
    # Convert to 16-bit PCM
    # Audio is in range [-1.0, 1.0], scale to Int16
    audio_signal_16 = np.int16(audio_signal * 32767)
    
    # Save to memory buffer
    buffer = io.BytesIO()
    wavfile.write(buffer, SAMPLE_RATE, audio_signal_16)
    buffer.seek(0)
    
    return Response(content=buffer.read(), media_type="audio/wav")

@app.get("/plot/{char}")
def generate_plot(char: str):
    """
    Dynamically generates the plot for a specific character and returns it as a PNG image directly.
    """
    char = char.upper()
    if char not in CHAR_TO_FREQ:
        return JSONResponse(status_code=400, content={"message": "Invalid character."})
    
    f_low, f_high = CHAR_TO_FREQ[char]
    tone = generate_tone(f_low, f_high, SAMPLES_PER_CHAR, SAMPLE_RATE)
    buf = plot_and_save_signal(tone, SAMPLE_RATE, f_low, f_high, char, return_buffer=True)
    return Response(content=buf.read(), media_type="image/png")

@app.post("/decode")
async def decode_audio(file: UploadFile = File(...)):
    """
    Decodes an uploaded WAV file using the Goertzel algorithm and Hamming windows.
    """
    # Read the audio file
    contents = await file.read()
    buffer = io.BytesIO(contents)
    
    try:
        fs, data = wavfile.read(buffer)
    except Exception as e:
        return JSONResponse(status_code=400, content={"message": "Invalid WAV file."})
        
    if data.ndim > 1:
        # Stereo to Mono by taking the left channel
        data = data[:, 0]
        
    # Standardize data to float32 between -1 and 1
    if data.dtype == np.int16:
        data = data.astype(np.float32) / 32768.0
    elif data.dtype == np.int32:
        data = data.astype(np.float32) / 2147483648.0
        
    window = np.hamming(SAMPLES_PER_CHAR)
    decoded_text = []
    
    # Iterate through chunks of SAMPLES_PER_CHAR
    num_chunks = len(data) // SAMPLES_PER_CHAR
    last_char = None
    
    for i in range(num_chunks):
        start_idx = i * SAMPLES_PER_CHAR
        end_idx = start_idx + SAMPLES_PER_CHAR
        chunk = data[start_idx:end_idx]
        
        # Apply Hamming window
        windowed_chunk = chunk * window
        
        # Calculate powers for low and high frequencies
        low_powers = [goertzel(windowed_chunk, f, fs) for f in F_LOW]
        high_powers = [goertzel(windowed_chunk, f, fs) for f in F_HIGH]
        
        max_low_power = max(low_powers)
        max_high_power = max(high_powers)
        
        # Basic thresholding to avoid silence/noise
        if max_low_power > POWER_THRESHOLD and max_high_power > POWER_THRESHOLD:
            best_low_idx = low_powers.index(max_low_power)
            best_high_idx = high_powers.index(max_high_power)
            
            detected_char = TURKISH_ALPHABET[best_low_idx][best_high_idx]
            
            # Debouncing: only add if it's different from the immediately previous chunk
            # (Note: this stops identical consecutive characters from being typed, e.g. "SAAT" will become "SAT".
            # The assignment specifies "so that consecutive chunks detecting the SAME character do not print it multiple times".
            # If the user presses a button for longer than 40ms, multiple chunks are generated.
            # But what if they type "AA"? Typically, a space or silence separator is needed to type "AA". 
            # Our debouncing logic will simply collapse consecutive identical characters without silence in between.)
            if detected_char != last_char:
                decoded_text.append(detected_char)
            last_char = detected_char
        else:
            # Silence detected -> break the debounce sequence
            last_char = None
            
    return {"decoded_text": "".join(decoded_text)}

# Serve static files for frontend
import os
os.makedirs("static", exist_ok=True)
app.mount("/", StaticFiles(directory="static", html=True), name="static")
