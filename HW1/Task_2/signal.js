
const FS = 44100;

function generateSamples(fLow, fHigh, duration = 0.3) {
  const N = Math.round(FS * duration);
  const points = [];

  for (let i = 0; i < N; i++) {
    const t = i / FS;

    const y = 0.5 * (Math.sin(2 * Math.PI * fLow * t)
      + Math.sin(2 * Math.PI * fHigh * t));

    points.push({ x: t, y: y });
  }

  return points;
}

function generateRawSamples(fLow, fHigh, duration = 0.3) {
  const N = Math.round(FS * duration);
  const samples = new Float64Array(N);

  for (let i = 0; i < N; i++) {
    const t = i / FS;
    samples[i] = 0.5 * (Math.sin(2 * Math.PI * fLow * t)
      + Math.sin(2 * Math.PI * fHigh * t));
  }

  return samples;
}