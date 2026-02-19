import numpy as np
import matplotlib.pyplot as plt

# ---------------------------------------------------------
# 1. Define Signal Parameters
# ---------------------------------------------------------
f0 = 33.0       # Base frequency (Hz)
f1 = 33.0       # Signal 1 frequency (Hz)
f2 = 16.5       # Signal 2 frequency (Hz)
f3 = 330.0      # Signal 3 frequency (Hz)
fs = 3300.0     # Sampling frequency (Hz)

# Calculate periods (T = 1/f)
T1 = 1.0 / f1
T2 = 1.0 / f2
T3 = 1.0 / f3

# ---------------------------------------------------------
# 2. Generate Time Vectors and Signals for Figure 1
#    (3 full periods for each specific signal)
# ---------------------------------------------------------

# Signal 1: 3 periods
t1 = np.arange(0, 3 * T1, 1/fs)
y1 = np.sin(2 * np.pi * f1 * t1)

# Signal 2: 3 periods
t2 = np.arange(0, 3 * T2, 1/fs)
y2 = np.sin(2 * np.pi * f2 * t2)

# Signal 3: 3 periods
t3 = np.arange(0, 3 * T3, 1/fs)
y3 = np.sin(2 * np.pi * f3 * t3)

# ---------------------------------------------------------
# 3. Create First Figure (Subplots)
# ---------------------------------------------------------
fig1, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 12))
fig1.suptitle('Individual Signals (3 Periods Each)', fontsize=16)

# Plot Signal 1
ax1.plot(t1, y1, 'b-', linewidth=2)
ax1.set_title(f'Signal 1 ({f1} Hz)', fontsize=14)
ax1.set_ylabel('Amplitude', fontsize=12)
ax1.set_xlabel('Time (s)', fontsize=12)
ax1.grid(True)

# Plot Signal 2
ax2.plot(t2, y2, 'g-', linewidth=2)
ax2.set_title(f'Signal 2 ({f2} Hz)', fontsize=14)
ax2.set_ylabel('Amplitude', fontsize=12)
ax2.set_xlabel('Time (s)', fontsize=12)
ax2.grid(True)

# Plot Signal 3
ax3.plot(t3, y3, 'r-', linewidth=2)
ax3.set_title(f'Signal 3 ({f3} Hz)', fontsize=14)
ax3.set_ylabel('Amplitude', fontsize=12)
ax3.set_xlabel('Time (s)', fontsize=12)
ax3.grid(True)

plt.tight_layout()

# ---------------------------------------------------------
# 4. Generate Combined Signal for Figure 2
#    (Time duration based on 3 periods of lowest freq f2)
# ---------------------------------------------------------

# Common time vector: 3 periods of f2 (approx 0.1818 seconds)
t_sum = np.arange(0, 3 * T2, 1/fs)

# Generate all three signals on this common time vector
y1_sum = np.sin(2 * np.pi * f1 * t_sum)
y2_sum = np.sin(2 * np.pi * f2 * t_sum)
y3_sum = np.sin(2 * np.pi * f3 * t_sum)

# Sum of signals
y_total = y1_sum + y2_sum + y3_sum

# ---------------------------------------------------------
# 5. Create Second Figure (Sum Signal)
# ---------------------------------------------------------
fig2 = plt.figure(figsize=(10, 6))
plt.plot(t_sum, y_total, 'k-', linewidth=2)
plt.title(f'Sum of All Signals (Duration: 3 periods of {f2} Hz)', fontsize=16)
plt.xlabel('Time (s)', fontsize=14)
plt.ylabel('Amplitude', fontsize=14)
plt.grid(True)
plt.tight_layout()

# Show plots
plt.show()
