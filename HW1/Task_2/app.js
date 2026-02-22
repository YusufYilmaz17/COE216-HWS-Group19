
const keypadEl = document.getElementById('keypad');
let activeBtn = null;


document.addEventListener('keydown', e => {
  const key = KEYBOARD_MAP[e.key];
  if (!key) return;

  const btn = document.querySelector(`.key[data-key="${key}"]`);
  pressKey(key, btn);
});


function pressKey(key, btn) {
  const [fLow, fHigh] = DTMF_FREQS[key];

  document.getElementById('d-key').textContent = key;
  document.getElementById('d-flow').textContent = fLow + ' Hz';
  document.getElementById('d-fhigh').textContent = fHigh + ' Hz';

  if (activeBtn) activeBtn.classList.remove('key-active');
  if (btn) { btn.classList.add('key-active'); activeBtn = btn; }

  document.querySelectorAll('.chart-container').forEach(el => el.style.display = 'block');

  playDTMF(fLow, fHigh);

  const points = generateSamples(fLow, fHigh);
  const rawSamples = generateRawSamples(fLow, fHigh);

  plotTimeDomain(points, fLow, fHigh);
  plotFFT(rawSamples, fLow, fHigh);

  setTimeout(() => {
    if (btn) btn.classList.remove('key-active');
  }, TONE_DURATION * 1000 + 100);
}