// Browser-side HAR dataset recorder. It reuses the same inference results
// produced by app.js, so training data and live inference share one feature format.
(() => {
  const LABELS = [
    'Pick up container', 'Open container', 'Insert tool',
    'Transfer sample', 'Close container', 'Place container back'
  ];
  let recording = false;
  let frames = [];
  let lastTimestamp = null;

  const el = id => document.getElementById(id);

  function featureVector(r) {
    const hands = r.hands || [];
    const interaction = r.interaction || {};
    const w = Math.max(Number(r.frame_width || 1), 1);
    const h = Math.max(Number(r.frame_height || 1), 1);
    const hx = hands.map(x => Number(x.x || 0));
    const hy = hands.map(x => Number(x.y || 0));
    return [
      Number(r.persons || 0),
      Number(r.objects || 0),
      Number(r.motion || 0) / 100,
      hx.length ? hx[0] / w : 0,
      hy.length ? hy[0] / h : 0,
      hx.length > 1 ? hx[1] / w : 0,
      hy.length > 1 ? hy[1] / h : 0,
      Number(interaction.distance_px || 999) / Math.max(w, h),
      Number(interaction.confidence || 0),
      hands.length
    ];
  }

  async function refreshStats() {
    try {
      const r = await fetch(`${API_BASE}/dataset/stats`);
      const data = await r.json();
      const total = data.total || 0;
      el('datasetStats').textContent = `${total} samples`;
      const selected = el('trainingLabel').value;
      const count = data.actions?.[selected] ?? 0;
      el('trainingStatus').textContent = `${selected}: ${count} saved samples`;
    } catch {
      el('datasetStats').textContent = 'Backend offline';
    }
  }

  function tick() {
    if (!recording || !state.lastResult) return;
    const r = state.lastResult;
    if (r.timestamp === lastTimestamp) return;
    lastTimestamp = r.timestamp;
    frames.push(featureVector(r));
    el('trainingStatus').textContent = `Recording ${el('trainingLabel').value}: ${frames.length} frames`;
  }

  async function stopRecording() {
    recording = false;
    const label = el('trainingLabel').value;
    el('recordTrainingBtn').textContent = '● Start Training Sample';
    if (frames.length < 8) {
      el('trainingStatus').textContent = `Only ${frames.length} frames captured. Record for a little longer.`;
      frames = [];
      return;
    }
    el('trainingStatus').textContent = `Saving ${frames.length} frames...`;
    try {
      const response = await fetch(`${API_BASE}/dataset/sequence`, {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({label, frames})
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Save failed');
      log(`Training sample saved — ${label} (${frames.length} frames)`);
      toast('Training sample saved');
    } catch (err) {
      log(`Training sample save failed — ${err.message}`, 'bad');
      el('trainingStatus').textContent = `Save failed: ${err.message}`;
    } finally {
      frames = [];
      refreshStats();
    }
  }

  function toggleRecording() {
    if (recording) return stopRecording();
    if (!state.ws || state.ws.readyState !== 1) {
      toast('Start the camera or load a video first');
      return;
    }
    recording = true;
    frames = [];
    lastTimestamp = null;
    el('recordTrainingBtn').textContent = '■ Stop & Save Sample';
    el('trainingStatus').textContent = `Recording ${el('trainingLabel').value}... perform the action now.`;
    log(`Training recorder started — ${el('trainingLabel').value}`, 'warn');
  }

  el('recordTrainingBtn').addEventListener('click', toggleRecording);
  el('trainingLabel').addEventListener('change', refreshStats);
  setInterval(tick, 150);
  refreshStats();
})();
