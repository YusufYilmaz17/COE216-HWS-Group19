let timeChart = null;
let fftChart  = null;

function plotTimeDomain(points, fLow, fHigh) {
  const periods  = 3;
  const showSecs = periods / fLow;
  const showN    = Math.round(FS * showSecs);
  const visible  = points.slice(0, showN);

  const ctx = document.getElementById('time-chart').getContext('2d');

  if (timeChart) timeChart.destroy(); 

  timeChart = new Chart(ctx, {
    type: 'line',
    data: {
      datasets: [{
        label: `Time Domain — ${fLow} Hz + ${fHigh} Hz`,
        data: visible,
        borderColor: '#00ff88',
        borderWidth: 1.5,
        pointRadius: 0, 
        tension: 0,
      }]
    },
    options: {
      parsing: false,  
      animation: false,
      scales: {
        x: {
          type: 'linear',
          title: { display: true, text: 'Time (s)', color: '#aaa' },
          ticks: { color: '#aaa', maxTicksLimit: 8 },
          grid:  { color: '#2a2a2a' }
        },
        y: {
          min: -2.5, max: 2.5,  
          title: { display: true, text: 'Amplitude', color: '#aaa' },
          ticks: { color: '#aaa' },
          grid:  { color: '#2a2a2a' }
        }
      },
      plugins: { legend: { labels: { color: '#aaa', font: { family: 'monospace' } } } }
    }
  });
}

function computeFFT(re, im) {
  const N = re.length;
  if (N <= 1) return;

  const rEven = new Float64Array(N/2), iEven = new Float64Array(N/2);
  const rOdd  = new Float64Array(N/2), iOdd  = new Float64Array(N/2);

  for (let i = 0; i < N/2; i++) {
    rEven[i] = re[2*i];   iEven[i] = im[2*i];
    rOdd[i]  = re[2*i+1]; iOdd[i]  = im[2*i+1];
  }

  computeFFT(rEven, iEven);
  computeFFT(rOdd,  iOdd);

  for (let k = 0; k < N/2; k++) {
    const angle = -2 * Math.PI * k / N;
    const wr = Math.cos(angle), wi = Math.sin(angle);
    const tr = wr * rOdd[k] - wi * iOdd[k];
    const ti = wr * iOdd[k] + wi * rOdd[k];
    re[k]       = rEven[k] + tr;  im[k]       = iEven[k] + ti;
    re[k + N/2] = rEven[k] - tr;  im[k + N/2] = iEven[k] - ti;
  }
}

function plotFFT(rawSamples, fLow, fHigh) {
  const FFT_SIZE = 4096;
  const re = new Float64Array(FFT_SIZE);
  const im = new Float64Array(FFT_SIZE);

  for (let i = 0; i < FFT_SIZE && i < rawSamples.length; i++) {
    re[i] = rawSamples[i];
  }

  computeFFT(re, im);

  const MAX_FREQ = 2000;
  const binHz    = FS / FFT_SIZE;           
  const maxBin   = Math.floor(MAX_FREQ / binHz);

  const freqLabels = [];
  const magnitudes = [];
  let maxMag = 0;

  for (let i = 0; i < maxBin; i++) {
    const mag = Math.sqrt(re[i] * re[i] + im[i] * im[i]);
    freqLabels.push(Math.round(i * binHz));
    magnitudes.push(mag);
    if (mag > maxMag) maxMag = mag;
  }

  const normalized = magnitudes.map(m => m / maxMag);

  const ctx = document.getElementById('fft-chart').getContext('2d');
  if (fftChart) fftChart.destroy();

  fftChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: freqLabels,
      datasets: [{
        label: `FFT Spectrum — peaks at ${fLow} Hz & ${fHigh} Hz`,
        data: normalized,
        backgroundColor: '#00ccff55',
        borderColor: '#00ccff',
        borderWidth: 1,
        barPercentage: 1.0,
        categoryPercentage: 1.0,
      }]
    },
    options: {
      animation: false,
      scales: {
        x: {
          title: { display: true, text: 'Frequency (Hz)', color: '#aaa' },
          ticks: {
            color: '#aaa',
            maxTicksLimit: 10,
            callback: val => freqLabels[val] + ' Hz'
          },
          grid: { color: '#2a2a2a' }
        },
        y: {
          min: 0, max: 1,
          title: { display: true, text: 'Magnitude (normalized)', color: '#aaa' },
          ticks: { color: '#aaa' },
          grid: { color: '#2a2a2a' }
        }
      },
      plugins: { legend: { labels: { color: '#aaa', font: { family: 'monospace' } } } }
    }
  });

}
