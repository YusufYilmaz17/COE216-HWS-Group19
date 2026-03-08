import numpy as np
import scipy.io.wavfile as wav
from scipy.signal import get_window, medfilt
import os

def analyze_speech(input_file_path, output_file_path):
    # 1. Load a WAV file and normalize it to [-1, 1].
    try:
        fs, signal = wav.read(input_file_path)
    except Exception as e:
        raise Exception(f"Error reading WAV file: {e}")

    # If stereo, convert to mono
    if len(signal.shape) > 1:
        signal = signal.mean(axis=1)
        
    # Normalize signal to [-1, 1]
    max_val = np.max(np.abs(signal))
    if max_val > 0:
        signal = signal / max_val
    
    # 2. Segment the signal into 20ms windows with 50% overlap using a Hamming window.
    frame_length_ms = 20
    overlap_percent = 50
    frame_length = int(fs * frame_length_ms / 1000)
    frame_step = int(frame_length * (1 - overlap_percent / 100))
    
    num_frames = int(np.ceil((len(signal) - frame_length) / frame_step)) + 1
    pad_signal_length = (num_frames - 1) * frame_step + frame_length
    
    padded_signal = np.pad(signal, (0, pad_signal_length - len(signal)), 'constant')
    
    # Compute Hamming window
    window = get_window('hamming', frame_length)
    
    # Arrays to hold properties
    energies = np.zeros(num_frames)
    zcrs = np.zeros(num_frames)
    
    # 3. Implement VAD: Calculate energy for each frame, determine a dynamic noise threshold from the first 200ms
    for i in range(num_frames):
        start = i * frame_step
        end = start + frame_length
        frame = padded_signal[start:end] * window
        
        # Calculate Energy
        energy = np.sum(frame ** 2)
        energies[i] = energy
        
        # Calculate Zero Crossing Rate (ZCR)
        # Add epsilon to prevent issues with flat line exactly zero
        zcr = np.sum(np.abs(np.diff(np.sign(frame + 1e-8)))) / (2 * frame_length)
        zcrs[i] = zcr
        
    # Dynamic noise threshold from the first 200ms
    frames_in_200ms = int(0.2 * fs / frame_step)
    if frames_in_200ms <= 0:
        frames_in_200ms = 1
    
    noise_energy_mean = np.mean(energies[:frames_in_200ms])
    noise_energy_std = np.std(energies[:frames_in_200ms])
    
    # Dynamic threshold: Mean + standard deviations for stability
    noise_threshold = noise_energy_mean + 3 * noise_energy_std
    if noise_threshold == 0:
        noise_threshold = 1e-5 # Fallback threshold if pure silence
    
    # Initial VAD decision
    vad = np.zeros(num_frames)
    vad[energies > noise_threshold] = 1
    
    # Implement 4-frame hangover
    hangover_frames = 4
    hangover_count = 0
    for i in range(num_frames):
        if vad[i] == 1:
            hangover_count = hangover_frames
        elif hangover_count > 0:
            vad[i] = 1
            hangover_count -= 1
            
    # Median filtering for stability
    vad = medfilt(vad, 5) 
    
    # 4. Classify speech into Voiced (High Energy/Low ZCR) and Unvoiced (Low Energy/High ZCR).
    # Calculate threshold for ZCR based on active speech segments
    active_zcrs = zcrs[vad == 1]
    if len(active_zcrs) > 0:
        zcr_threshold = np.mean(active_zcrs)
    else:
        zcr_threshold = np.mean(zcrs)
    
    voiced = np.zeros(num_frames)
    unvoiced = np.zeros(num_frames)
    
    for i in range(num_frames):
        if vad[i] == 1:
            if zcrs[i] < zcr_threshold:
                voiced[i] = 1  # High Energy, Low ZCR (relatively)
            else:
                unvoiced[i] = 1 # Low/Medium Energy, High ZCR

    # Save output WAV file
    active_indices = np.zeros(len(signal), dtype=bool)
    for i in range(num_frames):
        if vad[i] == 1:
            start = i * frame_step
            end = min(start + frame_length, len(signal)) 
            active_indices[start:end] = True
            
    if np.any(active_indices):
        speech_signal = signal[active_indices]
    else:
        speech_signal = np.array([])
        
    original_length = len(signal)
    compressed_length = len(speech_signal)

    if len(speech_signal) > 0:
        speech_signal_pcm = np.int16(speech_signal * 32767)
        wav.write(output_file_path, fs, speech_signal_pcm)
    else:
        # Save empty wav file to avoid error
        wav.write(output_file_path, fs, np.array([], dtype=np.int16))
        
    # Downsample signal for UI rendering to prevent browser crash
    max_ui_points = 5000
    downsample_factor = max(1, len(signal) // max_ui_points)
    signal_ds = signal[::downsample_factor]
    
    time_signal_ds = (np.arange(len(signal_ds)) * downsample_factor) / fs
    time_frames = np.arange(num_frames) * frame_step / fs + (frame_length_ms / 1000) / 2
    
    # Prepare JSON response data
    # Convert numpy arrays to lists
    result = {
        "time_signal": time_signal_ds.tolist(),
        "signal": signal_ds.tolist(),
        "time_frames": time_frames.tolist(),
        "energies": energies.tolist(),
        "zcrs": zcrs.tolist(),
        "voiced": voiced.tolist(),
        "unvoiced": unvoiced.tolist(),
        "noise_threshold": float(noise_threshold),
        "zcr_threshold": float(zcr_threshold),
        "fs": fs,
        "frame_step": float(frame_step),
        "frame_length": float(frame_length),
        "original_duration": original_length / fs,
        "compressed_duration": compressed_length / fs,
        "compression_ratio": compressed_length / original_length if original_length > 0 else 0
    }
    
    return result
