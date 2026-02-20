const audioCtx = new (window.AudioContext || window.webkitAudioContext)();

const TONE_DURATION = 0.3; 

function playDTMF(fLow, fHigh) {
  if (audioCtx.state === 'suspended') audioCtx.resume();

  [fLow, fHigh].forEach(freq => {
    const osc  = audioCtx.createOscillator();
    const gain = audioCtx.createGain();

    osc.type = 'sine';
    osc.frequency.setValueAtTime(freq, audioCtx.currentTime);

    gain.gain.setValueAtTime(0.4, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + TONE_DURATION);

    osc.connect(gain);
    gain.connect(audioCtx.destination); // destination = your speakers

    osc.start(audioCtx.currentTime);
    osc.stop(audioCtx.currentTime + TONE_DURATION);
  });
}