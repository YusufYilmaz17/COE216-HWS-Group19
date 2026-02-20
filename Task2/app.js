
const keypadEl = document.getElementById('keypad');
let   activeBtn = null; 

Object.keys(DTMF_FREQS).forEach(key => {
  const btn = document.createElement('button');
  btn.className   = 'key';
  btn.textContent = key;
  btn.dataset.key = key;

  btn.addEventListener('click', () => pressKey(key, btn));
  keypadEl.appendChild(btn);
});

const tableBody = document.querySelector('#freq-table tbody');

Object.entries(DTMF_FREQS).forEach(([key, [fL, fH]]) => {
  const row = document.createElement('tr');
  row.innerHTML = `<td>${key}</td><td>${fL}</td><td>${fH}</td>`;
  tableBody.appendChild(row);
});

document.addEventListener('keydown', e => {
  const key = KEYBOARD_MAP[e.key];
  if (!key) return;

  const btn = document.querySelector(`.key[data-key="${key}"]`);
  pressKey(key, btn);
});


function pressKey(key, btn) {
  const [fLow, fHigh] = DTMF_FREQS[key];

  document.getElementById('d-key').textContent   = key;
  document.getElementById('d-flow').textContent  = fLow  + ' Hz';
  document.getElementById('d-fhigh').textContent = fHigh + ' Hz';

  if (activeBtn) activeBtn.classList.remove('key-active');
  if (btn) { btn.classList.add('key-active'); activeBtn = btn; }

  playDTMF(fLow, fHigh);

  const points     = generateSamples(fLow, fHigh);
  const rawSamples = generateRawSamples(fLow, fHigh);

  plotTimeDomain(points, fLow, fHigh);
  plotFFT(rawSamples, fLow, fHigh);

  setTimeout(() => {
    if (btn) btn.classList.remove('key-active');
  }, TONE_DURATION * 1000 + 100);
}