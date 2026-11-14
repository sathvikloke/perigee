(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const key = 'perigee.ui-reference.evidence.v1';
  const fields = ['claim', 'observations', 'uncertainty'];
  let data = null, pair = 'B', visible = 'A', timer = null;
  const small = window.matchMedia('(max-width: 560px)');
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  function save() {
    fields.forEach(id => { document.getElementById(`${id}-print`).textContent = $(id).value; });
    try {
      localStorage.setItem(key, JSON.stringify({ pair, notes: Object.fromEntries(fields.map(id => [id, $(id).value])) }));
      $('save-status').textContent = 'Saved on this device';
    } catch { $('save-status').textContent = 'Storage unavailable · export to keep notes'; }
  }
  function show(ref) {
    visible = ref;
    $('plate-a').classList.toggle('mobile-hidden', ref !== 'A');
    $('plate-other').classList.toggle('mobile-hidden', ref === 'A');
    $('plate-a').classList.toggle('is-hidden', ref !== 'A');
    $('plate-other').classList.toggle('is-hidden', ref === 'A');
    document.querySelectorAll('[data-frame]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.frame === (ref === 'A' ? 'A' : 'other'))));
  }
  function stopBlink() {
    if (timer) clearInterval(timer);
    timer = null;
    $('blink').textContent = '▷ Blink pair';
    $('blink').setAttribute('aria-pressed', 'false');
    $('plates').classList.remove('blinking');
  }
  function renderSources() {
    if (!data) return;
    $('source-rows').replaceChildren(...data.frames.filter(f => f.ref === 'A' || f.ref === pair).map(f => {
      const tr = document.createElement('tr');
      [f.ref, f.observed_at_utc.slice(0, 10), `${f.wavelength_um.toFixed(4)} µm`].forEach(value => { const td = document.createElement('td'); td.textContent = value; tr.append(td); });
      const td = document.createElement('td'), a = document.createElement('a');
      a.href = f.source_url; a.target = '_blank'; a.rel = 'noopener'; a.textContent = `${f.collection_id === 'spherex_dr1' ? 'DR1' : 'QR3'} / D${f.detector} FITS ↗`;
      td.append(a); tr.append(td); return tr;
    }));
    const frames = [data.frames.find(f => f.ref === 'A'), data.frames.find(f => f.ref === pair)];
    const heading = document.createElement('h2'); heading.textContent = 'Selected observation provenance';
    $('print-provenance').replaceChildren(heading);
    frames.forEach(f => {
      const block = document.createElement('div'), title = document.createElement('h3');
      title.textContent = `Observation ${f.ref} · ${f.frame_key}`; block.append(title);
      const lines = [
        `Observation ID: ${f.observation_id} | Detector: ${f.detector} | Collection: ${f.collection_id}`,
        `UTC: ${f.observed_at_utc} | Wavelength: ${f.wavelength_um} µm | Flag screen: ${f.expected_quality_status}`,
        `Source: ${f.source_url}`,
        `Retained FITS SHA-256: ${f.retained_file_sha256}`
      ];
      lines.forEach(text => { const p = document.createElement('p'); p.textContent = text; block.append(p); });
      $('print-provenance').append(block);
    });
    const processing = document.createElement('p'); processing.textContent = `${data.processing.method}. ${data.processing.orientation}; ${data.processing.grid_px} pixels at ${data.processing.scale_arcsec_per_pixel} arcsec/pixel. ${data.processing.stretch}. ${data.processing.marker}. Outside retained cutout coverage is not zero signal. This is a local UI reference, not a live archive search.`;
    $('print-provenance').append(processing);
    document.querySelectorAll('.prediction').forEach((el, i) => {
      el.style.left = `${frames[i].marker_percent[0]}%`; el.style.top = `${frames[i].marker_percent[1]}%`;
    });
  }
  function setPair(ref, persist = true) {
    stopBlink(); pair = ref === 'C' ? 'C' : 'B'; show('A');
    const isC = pair === 'C';
    $('pair-ab').setAttribute('aria-pressed', String(!isC));
    $('pair-ac').setAttribute('aria-pressed', String(isC));
    $('other-letter').textContent = pair;
    $('a-heading').textContent = isC ? 'Shorter wavelength' : 'Earlier observation';
    $('other-frame-button').textContent = `Observation ${pair}`;
    $('other-heading').textContent = isC ? 'Another infrared color' : 'Later observation';
    $('other-date').textContent = isC ? '29 Apr 2026' : '27 Sep 2026';
    $('other-date').dateTime = isC ? '2026-04-29' : '2026-09-27';
    $('other-wave').textContent = isC ? '4.9399 µm' : '2.3220 µm';
    $('other-image').src = `assets/frame-${pair.toLowerCase()}.png`;
    $('other-image').alt = `Epsilon Indi B field observed on ${isC ? 'April 29, 2026 at 4.9399' : 'September 27, 2026 at 2.3220'} micrometers. Hatched corners are outside the retained cutout.`;
    $('other-release').textContent = isC ? 'DR1 · Detector 6' : 'QR3 · Detector 3';
    $('attached-frames').textContent = `A + ${pair}`;
    $('comparison-insight').classList.toggle('different', isC);
    $('insight-title').textContent = isC ? 'Same moment, a different infrared color' : 'Different dates, nearly the same wavelength';
    $('insight-body').textContent = isC ? 'A and C were taken at the same time. This pair compares wavelengths, not change over time. A different appearance is not evidence that time changed the object.' : 'Five months apart. Both record almost the same infrared color, so A + B passes the first check for a fair comparison.';
    renderSources(); if (persist) save();
  }
  fields.forEach(id => {
    const printable = document.createElement('p'); printable.id = `${id}-print`; printable.className = 'print-note';
    $(id).after(printable);
    $(id).addEventListener('input', () => $(id).setCustomValidity(''));
  });
  try {
    const saved = JSON.parse(localStorage.getItem(key) || 'null');
    if (saved && saved.notes) fields.forEach(id => { if (typeof saved.notes[id] === 'string') $(id).value = saved.notes[id].slice(0, $(id).maxLength); });
    if (saved) { pair = saved.pair === 'C' ? 'C' : 'B'; $('save-status').textContent = 'Restored from this device'; }
  } catch { $('save-status').textContent = 'Storage unavailable · export to keep notes'; }
  fields.forEach(id => { document.getElementById(`${id}-print`).textContent = $(id).value; });
  setPair(pair, false);
  fields.forEach(id => $(id).addEventListener('input', save));
  $('pair-ab').addEventListener('click', () => setPair('B'));
  $('pair-ac').addEventListener('click', () => setPair('C'));
  document.querySelectorAll('[data-frame]').forEach(b => b.addEventListener('click', () => { stopBlink(); show(b.dataset.frame === 'A' ? 'A' : pair); }));
  $('show-marker').addEventListener('change', e => $('plates').classList.toggle('markers-hidden', !e.target.checked));
  $('blink').setAttribute('aria-pressed', 'false');
  $('blink').addEventListener('click', () => {
    if (timer) { stopBlink(); return; }
    $('plates').classList.add('blinking');
    show('A');
    $('blink').textContent = 'Ⅱ Pause blink';
    $('blink').setAttribute('aria-pressed', 'true');
    timer = setInterval(() => show(visible === 'A' ? pair : 'A'), reduced.matches ? 1500 : 1000);
  });
  document.addEventListener('visibilitychange', () => { if (document.hidden) stopBlink(); });
  small.addEventListener('change', () => { stopBlink(); show('A'); });
  $('print').addEventListener('click', () => { stopBlink(); window.print(); });
  $('evidence-form').addEventListener('submit', e => {
    e.preventDefault();
    const empty = fields.find(id => !$(id).value.trim());
    if (empty) { $(empty).setCustomValidity('Add a note before exporting your evidence.'); $(empty).reportValidity(); return; }
    if (!data) { $('save-status').textContent = 'Provenance has not loaded · reload to export'; return; }
    save();
    const card = { schema_version: 1, kind: 'perigee-ui-reference-evidence', case_id: data.case_id, created_at: new Date().toISOString(), notes: Object.fromEntries(fields.map(id => [id, $(id).value.trim()])), selected_frames: data.frames.filter(f => f.ref === 'A' || f.ref === pair), processing: data.processing, limitations: ['UI reference using local samples; not a live archive search.', 'Flag screening is not a detection or calibrated brightness measurement.', 'Markers are catalog predictions. A/B span different data releases.'] };
    const url = URL.createObjectURL(new Blob([JSON.stringify(card, null, 2)], { type: 'application/json' }));
    const a = document.createElement('a'); a.href = url; a.download = 'perigee-evidence.json'; document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 1500);
    $('save-status').textContent = 'Evidence file downloaded';
  });
  fetch('assets/provenance.json').then(r => { if (!r.ok) throw new Error('Missing provenance'); return r.json(); }).then(record => { data = record; renderSources(); }).catch(() => { $('load-error').hidden = false; });
  document.querySelectorAll('.sky img').forEach(img => img.addEventListener('error', () => { $('load-error').hidden = false; }));
})();
