import { useState, type FormEvent } from 'react';
import type { PresetDescriptor } from '../api/types';
import { CASE_IDS, FOV_MAX, FOV_MIN, parseCoordinate, type Source } from '../source';

const CASE_TITLES: Record<string, string> = {
  fair_comparison: 'Is this a fair comparison?',
  moving_neighbor: 'Follow a nearby moving star',
};

interface PickerProps {
  source: Source;
  presets: PresetDescriptor[];
  presetsError: string | null;
  busy: boolean;
  onPick: (s: Source) => void;
}

/** Choose a case, a named target or public coordinates. Native disclosure keeps the sky in the first viewport. */
export function Picker({ source, presets, presetsError, busy, onPick }: PickerProps) {
  const [ra, setRa] = useState(source.kind === 'coords' ? String(source.ra) : '330.84');
  const [dec, setDec] = useState(source.kind === 'coords' ? String(source.dec) : '-56.786');
  const [fov, setFov] = useState(source.kind === 'coords' ? String(source.fov) : '6');
  const [errors, setErrors] = useState<Partial<Record<'ra' | 'dec' | 'fov', string>>>({});
  const [open, setOpen] = useState(false);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const r = parseCoordinate(ra, 'ra');
    const d = parseCoordinate(dec, 'dec');
    const f = parseCoordinate(fov, 'fov');
    const next = { ra: r.ok ? undefined : r.message, dec: d.ok ? undefined : d.message, fov: f.ok ? undefined : f.message };
    setErrors(next);
    if (r.ok && d.ok && f.ok) onPick({ kind: 'coords', ra: r.value, dec: d.value, fov: f.value });
  };

  const pick = (s: Source) => {
    onPick(s);
    setOpen(false);
  };

  const active = (s: Source) =>
    (s.kind === 'case' && source.kind === 'case' && s.caseId === source.caseId) ||
    (s.kind === 'preset' && source.kind === 'preset' && s.presetId === source.presetId);

  return (
    <details className="picker" open={open} onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)}>
      <summary>
        <span>
          <span className="section-icon" aria-hidden="true">⌖</span> Change investigation, target or coordinates
        </span>
        <span className="expand" aria-hidden="true">+</span>
      </summary>
      <div className="picker-body">
        <fieldset>
          <legend>Guided investigations</legend>
          <div className="chip-row">
            {CASE_IDS.map((id, i) => {
              const s: Source = { kind: 'case', caseId: id };
              return (
                <button key={id} type="button" className="chip" aria-pressed={active(s)} onClick={() => pick(s)}>
                  <span className="chip-num">0{i + 1}</span> {CASE_TITLES[id]}
                </button>
              );
            })}
          </div>
        </fieldset>
        <fieldset>
          <legend>Named targets · every retained frame</legend>
          {presetsError ? <p className="inline-error">{presetsError}</p> : null}
          <div className="chip-row">
            {presets.map((p) => {
              const s: Source = { kind: 'preset', presetId: p.id };
              return (
                <button key={p.id} type="button" className="chip" aria-pressed={active(s)} onClick={() => pick(s)}>
                  {p.display_name}
                  {p.frame_count != null ? <span className="chip-count">{p.frame_count} frames</span> : null}
                </button>
              );
            })}
          </div>
        </fieldset>
        <form className="coord-form" onSubmit={submit} noValidate>
          <fieldset>
            <legend>Any sky position · live NASA/IPAC archive search</legend>
            <div className="coord-fields">
              <CoordField id="ra" label="Right ascension" unit="°" value={ra} onChange={setRa} error={errors.ra} hint="0 to < 360" />
              <CoordField id="dec" label="Declination" unit="°" value={dec} onChange={setDec} error={errors.dec} hint="−90 to 90" />
              <CoordField id="fov" label="Field size" unit="′" value={fov} onChange={setFov} error={errors.fov} hint={`${FOV_MIN}–${FOV_MAX} arcmin`} />
              <button type="submit" className="search-btn" disabled={busy}>
                {busy ? 'Searching…' : 'Search archive'}
              </button>
            </div>
            {ra.trim() === '330.84' && dec.trim() === '-56.786' ? (
              <p className="prefill-note">Pre-filled example: Epsilon Indi A, J2000 catalog position. Epsilon Indi B lies about 2′ away in 2026.</p>
            ) : null}
            <p className="field-hint">Decimal degrees (ICRS). Searches SPHEREx DR1 and QR3 only; an empty result says nothing about other missions.</p>
          </fieldset>
        </form>
      </div>
    </details>
  );
}

function CoordField(props: { id: string; label: string; unit: string; value: string; hint: string; error?: string; onChange: (v: string) => void }) {
  const { id, label, unit, value, hint, error, onChange } = props;
  return (
    <div className="coord-field">
      <label htmlFor={`coord-${id}`}>{label}</label>
      <div className="coord-input">
        <input
          id={`coord-${id}`}
          inputMode="decimal"
          autoComplete="off"
          spellCheck={false}
          value={value}
          aria-invalid={error ? true : undefined}
          aria-describedby={`coord-${id}-hint`}
          onChange={(e) => onChange(e.target.value)}
        />
        <span aria-hidden="true">{unit}</span>
      </div>
      <span className={error ? 'coord-hint inline-error' : 'coord-hint'} id={`coord-${id}-hint`}>
        {error ?? hint}
      </span>
    </div>
  );
}
