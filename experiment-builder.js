/**
 * Space Experiment AI - Experiment Builder
 * Standalone and Edge-Integrated Experiment Protocol Generator
 */
(() => {
  const isHttp = location.protocol.startsWith('http');
  const isLocal = isHttp && (location.hostname === 'localhost' || location.hostname === '127.0.0.1');
  const API = window.SPACE_AI_API || (isLocal ? location.origin : 'http://localhost:8000');

  const steps = [];
  const $ = id => document.getElementById(id);
  const esc = val => String(val ?? '').replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  function status(text, isGood = false) {
    const el = $('builderStatus');
    if (!el) return;
    el.textContent = text;
    el.style.color = isGood ? '#35d59d' : '';
  }

  // Domain-specific AI Knowledge Base for Space Experiment Steps
  const AI_STEP_TEMPLATES = [
    {
      keys: ['pipette', 'liquid', 'micropipette', 'reagent', 'solution', 'titration', 'buffer', 'assay'],
      steps: [
        { name: 'Pick up micropipette', objects: ['person', 'pipette'], interaction: 'Hand → Pipette' },
        { name: 'Attach sterile pipette tip', objects: ['pipette', 'tip'], interaction: 'Hand → Tip' },
        { name: 'Aspirate reagent sample', objects: ['pipette', 'sample'], interaction: 'Pipette → Liquid' },
        { name: 'Dispense into test microwell', objects: ['pipette', 'well'], interaction: 'Pipette → Well' },
        { name: 'Eject tip into waste receptacle', objects: ['pipette', 'waste'], interaction: 'Pipette → Waste' },
        { name: 'Return pipette to stand', objects: ['pipette'], interaction: 'Hand → Stand' }
      ]
    },
    {
      keys: ['sample', 'transfer', 'tube', 'vial', 'specimen', 'container', 'extract'],
      steps: [
        { name: 'Pick up sample container', objects: ['person', 'container'], interaction: 'Hand → Container' },
        { name: 'Open sample container lid', objects: ['container'], interaction: 'Hand → Lid' },
        { name: 'Pick up transfer tool', objects: ['person', 'tool'], interaction: 'Hand → Tool' },
        { name: 'Transfer sample to target vessel', objects: ['sample', 'tool'], interaction: 'Tool → Sample' },
        { name: 'Close sample container', objects: ['container'], interaction: 'Hand → Container' },
        { name: 'Place container back in storage rack', objects: ['container', 'rack'], interaction: 'Hand → Rack' }
      ]
    },
    {
      keys: ['weigh', 'weight', 'balance', 'scale', 'mass', 'gravimetric'],
      steps: [
        { name: 'Calibrate precision microbalance', objects: ['balance'], interaction: 'Hand → Balance' },
        { name: 'Place tare container on pan', objects: ['container', 'balance'], interaction: 'Hand → Balance' },
        { name: 'Zero balance display', objects: ['balance'], interaction: 'Hand → Tare' },
        { name: 'Add specimen to target mass', objects: ['specimen', 'tool'], interaction: 'Tool → Pan' },
        { name: 'Record stable mass readout', objects: ['balance'], interaction: 'Observation' },
        { name: 'Remove weighed sample and secure', objects: ['container'], interaction: 'Hand → Container' }
      ]
    },
    {
      keys: ['inspect', 'inspection', 'microscope', 'visual', 'optical', 'magnif', 'lens', 'slide'],
      steps: [
        { name: 'Pick up specimen slide mount', objects: ['person', 'slide'], interaction: 'Hand → Slide' },
        { name: 'Secure slide onto microscope stage', objects: ['slide', 'stage'], interaction: 'Hand → Stage' },
        { name: 'Adjust optical focus & illumination', objects: ['microscope'], interaction: 'Hand → Dial' },
        { name: 'Examine field and capture high-res frame', objects: ['microscope', 'camera'], interaction: 'Observation' },
        { name: 'Log visual inspection findings', objects: ['console'], interaction: 'Data Entry' },
        { name: 'Remove slide and store in tray', objects: ['slide'], interaction: 'Hand → Tray' }
      ]
    },
    {
      keys: ['plant', 'seed', 'leaf', 'botany', 'crop', 'germination', 'foliage', 'vegetation', 'soil'],
      steps: [
        { name: 'Open plant growth chamber', objects: ['chamber'], interaction: 'Hand → Door' },
        { name: 'Inspect leaf foliage & stems', objects: ['plant'], interaction: 'Observation' },
        { name: 'Measure canopy height & root moisture', objects: ['sensor', 'plant'], interaction: 'Probe → Soil' },
        { name: 'Administer nutrient hydration dose', objects: ['dispenser', 'plant'], interaction: 'Hand → Dispenser' },
        { name: 'Capture multispectral growth scan', objects: ['camera', 'plant'], interaction: 'Observation' },
        { name: 'Seal growth chamber enclosure', objects: ['chamber'], interaction: 'Hand → Door' }
      ]
    },
    {
      keys: ['centrifuge', 'spin', 'separation', 'pellet', 'serum', 'rpm'],
      steps: [
        { name: 'Prepare balanced centrifuge tube pairs', objects: ['tubes', 'balance'], interaction: 'Hand → Tubes' },
        { name: 'Load tubes into rotor symmetrically', objects: ['tubes', 'centrifuge'], interaction: 'Hand → Rotor' },
        { name: 'Latch and lock safety lid', objects: ['centrifuge'], interaction: 'Hand → Latch' },
        { name: 'Execute timed separation cycle', objects: ['centrifuge'], interaction: 'Console → Start' },
        { name: 'Wait for rotor to come to complete stop', objects: ['centrifuge'], interaction: 'Observation' },
        { name: 'Carefully extract supernatant fraction', objects: ['tubes', 'tool'], interaction: 'Hand → Tubes' }
      ]
    },
    {
      keys: ['crystal', 'crystallization', 'macromolecule', 'protein crystal', 'vapor', 'diffusion'],
      steps: [
        { name: 'Verify crystallization cell seals', objects: ['cell'], interaction: 'Observation' },
        { name: 'Inject precipitant solution into well', objects: ['syringe', 'cell'], interaction: 'Hand → Cell' },
        { name: 'Seal vapor diffusion chamber', objects: ['cell', 'seal'], interaction: 'Hand → Seal' },
        { name: 'Mount cassette in microgravity locker', objects: ['cell', 'locker'], interaction: 'Hand → Locker' },
        { name: 'Acquire initial polarization baseline', objects: ['camera', 'cell'], interaction: 'Observation' },
        { name: 'Engage continuous optical logging', objects: ['console'], interaction: 'System Start' }
      ]
    },
    {
      keys: ['fluid', 'droplet', 'capillary', 'surface tension', 'physics', 'liquid bridge', 'dispersion'],
      steps: [
        { name: 'Purge fluid test loop channel', objects: ['cassette'], interaction: 'Hand → Valve' },
        { name: 'Inject calibrated micro-droplet', objects: ['dispenser', 'substrate'], interaction: 'Hand → Droplet' },
        { name: 'Trigger high-speed imaging capture', objects: ['camera'], interaction: 'System Trigger' },
        { name: 'Observe wetting & capillary spreading', objects: ['camera', 'fluid'], interaction: 'Observation' },
        { name: 'Record contact angle telemetry', objects: ['console'], interaction: 'Data Entry' },
        { name: 'Absorb fluid and sanitize test plate', objects: ['wipe', 'substrate'], interaction: 'Hand → Wipe' }
      ]
    },
    {
      keys: ['sensor', 'telemetry', 'wire', 'cable', 'probe', 'voltage', 'circuit', 'signal', 'hardware', 'electronics'],
      steps: [
        { name: 'Position payload module in test bay', objects: ['module'], interaction: 'Hand → Module' },
        { name: 'Attach multichannel sensor leads', objects: ['probe', 'module'], interaction: 'Hand → Leads' },
        { name: 'Power on instrumentation bus', objects: ['switch'], interaction: 'Hand → Switch' },
        { name: 'Run automated diagnostic sweep', objects: ['console'], interaction: 'System Test' },
        { name: 'Verify telemetry data stream', objects: ['display'], interaction: 'Observation' },
        { name: 'Power down and decouple sensor harness', objects: ['probe', 'module'], interaction: 'Hand → Leads' }
      ]
    },
    {
      keys: ['heat', 'incubator', 'thermal', 'temperature', 'warm', 'cool', 'cryo', 'freeze'],
      steps: [
        { name: 'Verify thermal chamber setpoint reading', objects: ['incubator'], interaction: 'Observation' },
        { name: 'Don protective thermal safety gear', objects: ['person', 'glove'], interaction: 'Hand → Glove' },
        { name: 'Load specimen tray into thermal zone', objects: ['sample', 'incubator'], interaction: 'Hand → Chamber' },
        { name: 'Engage thermal soaking profile', objects: ['console'], interaction: 'System Trigger' },
        { name: 'Extract treated sample upon completion', objects: ['sample', 'incubator'], interaction: 'Hand → Sample' },
        { name: 'Transfer sample to stabilization rack', objects: ['sample', 'rack'], interaction: 'Hand → Rack' }
      ]
    }
  ];

  function generateFallbackSteps(name) {
    const cleanName = (name || 'Experiment').replace(/[^a-zA-Z0-9\s-]/g, '').trim() || 'Demo';
    return [
      { name: `Prepare ${cleanName} equipment`, objects: ['person', 'equipment'], interaction: 'Hand → Equipment' },
      { name: 'Inspect specimen and apparatus', objects: ['person', 'specimen'], interaction: 'Observation' },
      { name: `Execute primary ${cleanName} step`, objects: ['specimen', 'tool'], interaction: 'Hand → Specimen' },
      { name: 'Monitor real-time sensor telemetry', objects: ['console', 'sensor'], interaction: 'Observation' },
      { name: 'Record observations and results', objects: ['console'], interaction: 'Data Entry' },
      { name: 'Secure test items and clean workstation', objects: ['equipment'], interaction: 'Hand → Storage' }
    ];
  }

  function render() {
    const container = $('builderSteps');
    if (!container) return;

    if (!steps.length) {
      container.innerHTML = '<div class="builder-empty">No steps yet. Click <b>✨ AI Suggest Steps</b> or <b>+ Add Step</b> below.</div>';
      return;
    }

    container.innerHTML = `
      <div class="builder-steps-container">
        ${steps.map((s, i) => `
          <div class="builder-step" data-index="${i}">
            <span class="builder-num">${i + 1}</span>
            <input data-i="${i}" class="step-name" value="${esc(s.name)}" placeholder="Step ${i + 1} description..." />
            <div class="step-actions">
              <button type="button" class="step-btn" data-move-up="${i}" title="Move up" ${i === 0 ? 'disabled style="opacity:0.3;cursor:default"' : ''}>▲</button>
              <button type="button" class="step-btn" data-move-down="${i}" title="Move down" ${i === steps.length - 1 ? 'disabled style="opacity:0.3;cursor:default"' : ''}>▼</button>
              <button type="button" class="step-btn danger" data-remove="${i}" title="Remove step">✕</button>
            </div>
          </div>
        `).join('')}
      </div>
    `;

    // Real-time input binding
    container.querySelectorAll('.step-name').forEach(input => {
      input.addEventListener('input', e => {
        const idx = Number(e.target.dataset.i);
        if (steps[idx]) {
          steps[idx].name = e.target.value;
        }
      });
      input.addEventListener('change', () => {
        status('Step modified — remember to save experiment.');
      });
    });

    // Remove buttons
    container.querySelectorAll('[data-remove]').forEach(btn => {
      btn.addEventListener('click', () => {
        const idx = Number(btn.dataset.remove);
        const removed = steps.splice(idx, 1)[0];
        render();
        status(`Removed step: "${removed?.name || idx + 1}".`);
      });
    });

    // Move up
    container.querySelectorAll('[data-move-up]').forEach(btn => {
      btn.addEventListener('click', () => {
        const idx = Number(btn.dataset.moveUp);
        if (idx > 0) {
          const item = steps.splice(idx, 1)[0];
          steps.splice(idx - 1, 0, item);
          render();
        }
      });
    });

    // Move down
    container.querySelectorAll('[data-move-down]').forEach(btn => {
      btn.addEventListener('click', () => {
        const idx = Number(btn.dataset.moveDown);
        if (idx < steps.length - 1) {
          const item = steps.splice(idx, 1)[0];
          steps.splice(idx + 1, 0, item);
          render();
        }
      });
    });
  }

  function add(step = {}) {
    steps.push({
      id: step.id || `step-${steps.length + 1}`,
      name: step.name || `Step ${steps.length + 1}`,
      description: step.description || '',
      objects: Array.isArray(step.objects) ? step.objects : ['object'],
      interaction: step.interaction || 'Hand → Object',
      required: step.required !== false
    });
    render();
    status('New step added — edit its name and review sequence.');
  }

  async function suggest() {
    const nameInput = $('experimentName');
    const descInput = $('experimentDescription');
    const btn = $('suggestStepsBtn');
    const name = nameInput ? nameInput.value.trim() : '';
    const desc = descInput ? descInput.value.trim() : '';

    if (!name) {
      status('Please enter an experiment name first.', false);
      if (nameInput) {
        nameInput.focus();
        nameInput.style.borderColor = '#ff6478';
        setTimeout(() => { nameInput.style.borderColor = ''; }, 1800);
      }
      return;
    }

    const originalText = btn ? btn.innerHTML : '✨ AI Suggest Steps';
    if (btn) {
      btn.innerHTML = '✨ Generating Steps…';
      btn.classList.add('loading');
    }
    status('AI Assistant is formulating the optimal step sequence…');

    let generatedSteps = null;
    let sourceLabel = 'Built-in Space AI Engine';

    // Attempt edge backend call if HTTP/HTTPS is available
    if (isHttp && API) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 1500);
        const res = await fetch(`${API}/experiments/suggest`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, description: desc }),
          signal: controller.signal
        });
        clearTimeout(timeoutId);
        if (res.ok) {
          const data = await res.json();
          if (data && data.suggestion && Array.isArray(data.suggestion.steps) && data.suggestion.steps.length) {
            generatedSteps = data.suggestion.steps;
            sourceLabel = 'Edge AI Model';
          }
        }
      } catch {
        // Silently fall back to built-in AI engine
      }
    }

    // Client-side AI Domain Synthesis (Offline, GitHub Pages, or fallback)
    if (!generatedSteps) {
      const text = `${name} ${desc}`.toLowerCase();
      const matched = AI_STEP_TEMPLATES.find(t => t.keys.some(k => text.includes(k)));
      if (matched) {
        generatedSteps = matched.steps;
        sourceLabel = 'Domain Template AI';
      } else {
        generatedSteps = generateFallbackSteps(name);
        sourceLabel = 'Sequence Synthesizer';
      }
    }

    // Populate steps safely
    steps.splice(0, steps.length, ...generatedSteps.map((s, idx) => ({
      id: s.id || `step-${idx + 1}`,
      name: s.name || `Step ${idx + 1}`,
      description: s.description || '',
      objects: Array.isArray(s.objects) ? s.objects : ['object'],
      interaction: s.interaction || 'Hand → Object',
      required: s.required !== false
    })));

    render();

    if (btn) {
      btn.innerHTML = originalText;
      btn.classList.remove('loading');
    }

    status(`✨ AI draft ready — ${steps.length} steps generated for "${name}" (${sourceLabel}). Review, edit, or save below.`, true);
    const toastEl = $('toast');
    if (toastEl) {
      toastEl.textContent = `✨ AI suggested ${steps.length} steps for "${name}"`;
      toastEl.classList.add('show');
      setTimeout(() => toastEl.classList.remove('show'), 2400);
    }
  }

  async function save() {
    const nameInput = $('experimentName');
    const descInput = $('experimentDescription');
    const name = nameInput ? nameInput.value.trim() : '';
    const description = descInput ? descInput.value.trim() : '';

    if (!name || !steps.length) {
      status('Enter an experiment name and at least one step before saving.', false);
      const toastEl = $('toast');
      if (toastEl) {
        toastEl.textContent = 'Please enter a name and at least one step';
        toastEl.classList.add('show');
        setTimeout(() => toastEl.classList.remove('show'), 2000);
      }
      return;
    }

    status('Saving experiment…');

    const experimentData = {
      name,
      description,
      steps: steps.map((s, idx) => ({
        id: s.id || `step-${idx + 1}`,
        name: s.name.trim(),
        description: s.description || '',
        objects: s.objects || ['object'],
        interaction: s.interaction || 'Hand → Object',
        required: s.required !== false
      })),
      verification: 'human-verified',
      source: 'user-reviewed',
      savedAt: new Date().toISOString()
    };

    // 1. Always persist to localStorage for full static & GitHub Pages deployment support
    try {
      const savedList = JSON.parse(localStorage.getItem('SPACE_AI_EXPERIMENTS') || '[]');
      const existingIdx = savedList.findIndex(e => (e.name || '').toLowerCase() === name.toLowerCase());
      if (existingIdx >= 0) {
        savedList[existingIdx] = experimentData;
      } else {
        savedList.push(experimentData);
      }
      localStorage.setItem('SPACE_AI_EXPERIMENTS', JSON.stringify(savedList));
      localStorage.setItem('SPACE_AI_ACTIVE_EXPERIMENT', JSON.stringify(experimentData));
    } catch (err) {
      console.warn('localStorage save warning:', err);
    }

    // 2. Persist to Edge backend if reachable
    let backendSaved = false;
    if (isHttp && API) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 2000);
        const res = await fetch(`${API}/experiments`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(experimentData),
          signal: controller.signal
        });
        clearTimeout(timeoutId);
        if (res.ok) backendSaved = true;
      } catch {
        // Backend offline is normal in static deployment
      }
    }

    // 3. Synchronize with Live Experiment Monitor and Training Recorder
    window.dispatchEvent(new CustomEvent('spaceai:experiment-loaded', { detail: experimentData }));

    const saveMessage = backendSaved
      ? `✓ Saved to Edge AI & active in monitor: ${name} (${steps.length} steps)`
      : `✓ Saved locally & active in monitor: ${name} (${steps.length} steps)`;
    status(saveMessage, true);

    const toastEl = $('toast');
    if (toastEl) {
      toastEl.textContent = `✓ Experiment "${name}" is now active in monitor`;
      toastEl.classList.add('show');
      setTimeout(() => toastEl.classList.remove('show'), 2400);
    }
  }

  // Bind main buttons
  const addBtn = $('addStepBtn');
  if (addBtn) addBtn.onclick = () => add();

  const suggestBtn = $('suggestStepsBtn');
  if (suggestBtn) suggestBtn.onclick = suggest;

  const saveBtn = $('saveExperimentBtn');
  if (saveBtn) saveBtn.onclick = save;

  // Initialize: load saved active experiment if present, otherwise default demo steps
  try {
    const active = localStorage.getItem('SPACE_AI_ACTIVE_EXPERIMENT');
    if (active) {
      const parsed = JSON.parse(active);
      if (parsed && Array.isArray(parsed.steps) && parsed.steps.length) {
        if ($('experimentName')) $('experimentName').value = parsed.name || 'BAS Demo Experiment';
        if ($('experimentDescription')) $('experimentDescription').value = parsed.description || '';
        steps.splice(0, steps.length, ...parsed.steps);
        render();
        status(`Loaded active experiment: "${parsed.name}" (${steps.length} steps).`, true);
        return;
      }
    }
  } catch (e) {
    console.warn('Could not load cached experiment:', e);
  }

  // Default demo protocol steps
  add({ name: 'Pick up container', objects: ['person', 'container'], interaction: 'Hand → Container' });
  add({ name: 'Open container', objects: ['container'], interaction: 'Hand → Container' });
  add({ name: 'Insert tool', objects: ['person', 'tool'], interaction: 'Hand → Tool' });
  add({ name: 'Transfer sample', objects: ['sample', 'tool'], interaction: 'Hand → Sample' });
  add({ name: 'Close container', objects: ['container'], interaction: 'Hand → Container' });
  add({ name: 'Place container back', objects: ['container'], interaction: 'Hand → Rack' });
})();
