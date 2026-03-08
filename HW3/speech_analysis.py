import numpy as np
import scipy.io.wavfile as wav
from scipy.signal import get_window, medfilt
import matplotlib.pyplot as plt
import argparse
import os

def process_speech(input_file, output_file):
    # 1. Load a WAV file and normalize it to [-1, 1].
    try:
        fs, signal = wav.read(input_file)
    except Exception as e:
        print(f"Error reading {input_file}: {e}")
        return

    # If stereo, convert to mono
    if len(signal.shape) > 1:
        signal = signal.mean(axis=1)
        
    # Normalize signal to [-1, 1]
    max_val = np.max(np.abs(signal))
    if max_val > 0:
        signal = signal / max_val
    else:
        print("Warning: Blank audio signal.")
    
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
    
    # 3. Implement VAD: Calculate energy for each frame, determine a dynamic noise threshold from the first 200ms, 
    # and use a 4-frame 'hangover' and median filtering for stability.
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
    # Using a median filter size of 5 frames
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

    # 5. Visualization: Create subplots showing the raw signal, energy/ZCR curves, and color-coded masks 
    # (Green for Voiced, Yellow for Unvoiced).
    time_signal = np.arange(len(signal)) / fs
    time_frames = np.arange(num_frames) * frame_step / fs + (frame_length_ms / 1000) / 2
    
    fig, axs = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
    
    # Subplot 1: Raw signal with Green/Yellow masks
    axs[0].plot(time_signal, signal, label='Raw Signal', color='blue', alpha=0.6)
    axs[0].set_title('Raw Signal with Voiced (Green) / Unvoiced (Yellow) Masks')
    axs[0].set_ylabel('Amplitude')
    
    # Enhance visualization using filled areas for the masks
    for i in range(num_frames):
        start_time = i * frame_step / fs
        end_time = (i * frame_step + frame_length) / fs
        
        # Limit end_time to match time_signal range visually
        end_time = min(end_time, time_signal[-1])
        
        if voiced[i] == 1:
            axs[0].axvspan(start_time, end_time, color='green', alpha=0.3, lw=0)
        elif unvoiced[i] == 1:
            axs[0].axvspan(start_time, end_time, color='yellow', alpha=0.3, lw=0)
            
    # Subplot 2: Energy Curve
    axs[1].plot(time_frames, energies, label='Short-Time Energy', color='red')
    axs[1].axhline(noise_threshold, color='black', linestyle='--', label='Noise Threshold')
    axs[1].set_title('Short-Time Energy (Log Scale)')
    axs[1].set_ylabel('Energy')
    axs[1].set_yscale('log') # Better viewing dynamic range of energy
    axs[1].legend()

    # Subplot 3: ZCR Curve
    axs[2].plot(time_frames, zcrs, label='Zero-Crossing Rate (ZCR)', color='purple')
    axs[2].axhline(zcr_threshold, color='black', linestyle='--', label='ZCR Threshold')
    axs[2].set_title('Zero-Crossing Rate')
    axs[2].set_xlabel('Time (s)')
    axs[2].set_ylabel('ZCR')
    axs[2].legend()

    plt.tight_layout()
    plot_path = output_file.replace('.wav', '_plot.png')
    plt.savefig(plot_path)
    print(f"Saved analysis plot to {plot_path}")
    plt.show()

    # 6. Export: Save only the speech segments as a new WAV file and print the compression ratio.
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
        print("Warning: No speech detected in the audio.")

    if len(speech_signal) > 0:
        # Convert back to 16-bit PCM format
        speech_signal_pcm = np.int16(speech_signal * 32767)
        wav.write(output_file, fs, speech_signal_pcm)
        
        original_length = len(signal)
        compressed_length = len(speech_signal)
        compression_ratio = compressed_length / original_length
        print(f"Original Signal: {original_length} samples ({original_length/fs:.2f} s)")
        print(f"Speech Signal:   {compressed_length} samples ({compressed_length/fs:.2f} s)")
        print(f"Retained Ratio:  {compression_ratio:.2%}")
        print(f"Compression (Data Reduced): {(1 - compression_ratio):.2%}")
        print(f"Saved speech segments to {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Speech Analysis Tool: VAD and Voiced/Unvoiced Classification")
    parser.add_argument("input", help="Path to input WAV file")
    parser.add_argument("-o", "--output", default="output_speech.wav", help="Path to save output output WAV file")
    
    args = parser.parse_args()
    
    if os.path.exists(args.input):
        process_speech(args.input, args.output)
    else:
        print(f"Error: Could not find input file '{args.input}'.")
        print("Please provide a valid WAV file to process.")
