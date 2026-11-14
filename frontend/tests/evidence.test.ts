import { describe, expect, it } from 'vitest';
import { buildEvidenceCard, firstMissingNote, serializeCard, type EvidenceContext } from '../src/evidence';
import { classifyPair, formatDate, qualityStatus } from '../src/format';
import { parseCoordinate, sourceFromSearch, sourceToSearch } from '../src/source';
import type { FrameRecord } from '../src/api/types';
import frameExample from '../../backend/tests/api/examples/frame_response.fixture.json';

const base = frameExample.frame as unknown as FrameRecord;
const A: FrameRecord = { ...base, frame_id: 'A1', observed_at_utc: '2026-04-29T12:05:47.874Z', mjd: 61159.504, wavelength_um: 2.3232, bandwidth_um: 0.0577 };
const B: FrameRecord = { ...base, frame_id: 'B1', observed_at_utc: '2026-09-27T07:44:24.312', mjd: 61310.3225, wavelength_um: 2.322, bandwidth_um: 0.0573, collection_id: 'spherex_qr3' };
const C: FrameRecord = { ...A, frame_id: 'C1', wavelength_um: 4.9399, bandwidth_um: 0.0376 };

const ctx = (selected = [{ ref: 'A', frame: A }, { ref: 'B', frame: B }]): EvidenceContext => ({
  investigationKey: 'case:fair_comparison',
  caseId: 'fair_comparison',
  presetId: 'epsilon_indi_b',
  query: null,
  comparison: 'A + B: Different dates, nearly the same wavelength',
  selected,
  sources: [{ label: 'IRSA', url: 'https://irsa.ipac.caltech.edu/Missions/spherex.html' }],
  limitations: ['Marker is a catalog prediction.'],
});

describe('evidence card serialization', () => {
  const notes = { claim: '  A and B are fair.  ', observations: 'Same detector.\nFive months apart.', uncertainty: 'No photometry.' };
  const card = buildEvidenceCard(ctx(), notes, new Date('2026-11-14T18:00:00Z'), 'ev-test');
  const parsed = JSON.parse(serializeCard(card));

  it('carries identity, timestamps, wavelengths, source URLs, release and processing per frame', () => {
    expect(parsed).toMatchObject({ schema_version: 1, id: 'ev-test', case_id: 'fair_comparison', created_at: '2026-11-14T18:00:00.000Z' });
    expect(parsed.selected_frames.map((f: { frame_id: string }) => f.frame_id)).toEqual(['A1', 'B1']);
    const [fa, fb] = parsed.selected_frames;
    expect(fa).toMatchObject({ ref: 'A', observed_at_utc: A.observed_at_utc, wavelength_um: 2.3232, source_url: A.source_url, release: 'DR1' });
    expect(fb.release).toBe('QR3');
    expect(fa.detector).toBe(A.detector);
    expect(fa.processing.registration_method).toBe(A.registration?.method);
    expect(fa.quality.status).toBe(qualityStatus(A));
  });

  it('keeps complete notes, trimmed, including line breaks', () => {
    expect(parsed.notes).toEqual({ claim: 'A and B are fair.', observations: 'Same detector.\nFive months apart.', uncertainty: 'No photometry.' });
  });

  it('records missing quality as unknown, never clear', () => {
    const noQuality = { ...B, quality: null };
    const c = buildEvidenceCard(ctx([{ ref: 'A', frame: A }, { ref: 'B', frame: noQuality }]), notes);
    expect(c.selected_frames[1].quality.status).toBe('unknown');
  });

  it('rejects whitespace-only notes', () => {
    expect(firstMissingNote({ claim: 'x', observations: '   ', uncertainty: 'y' })).toBe('observations');
    expect(firstMissingNote({ claim: 'x', observations: 'y', uncertainty: 'z' })).toBeNull();
  });
});

describe('comparison semantics', () => {
  it('classifies pairs from parsed values, not strings (Z suffix vs none)', () => {
    expect(classifyPair(A, B)).toBe('fair_time');
    expect(classifyPair(A, C)).toBe('same_time');
    expect(classifyPair({ ...B, wavelength_um: 4.0 }, A)).toBe('mixed');
    expect(classifyPair({ ...B, wavelength_um: null }, A)).toBe('unknown');
    expect(formatDate('2026-09-27T07:44:24.312')).toBe('27 Sep 2026');
    expect(formatDate('2026-04-29T12:05:47.874Z')).toBe('29 Apr 2026');
  });
});

describe('coordinate input and shareable URL', () => {
  it('rejects partial numbers, out-of-range values and infinity without clipping', () => {
    expect(parseCoordinate('330.84', 'ra')).toEqual({ ok: true, value: 330.84 });
    expect(parseCoordinate('−56.786', 'dec')).toEqual({ ok: true, value: -56.786 });
    expect(parseCoordinate('12abc', 'ra').ok).toBe(false);
    expect(parseCoordinate('360', 'ra').ok).toBe(false);
    expect(parseCoordinate('-91', 'dec').ok).toBe(false);
    expect(parseCoordinate('Infinity', 'ra').ok).toBe(false);
    expect(parseCoordinate('11', 'fov').ok).toBe(false);
  });

  it('round-trips coordinates and case ids, never notes', () => {
    const s = { kind: 'coords' as const, ra: 330.84, dec: -56.786, fov: 6 };
    expect(sourceFromSearch(sourceToSearch(s))).toEqual(s);
    expect(sourceFromSearch('?case=moving_neighbor')).toEqual({ kind: 'case', caseId: 'moving_neighbor' });
    expect(sourceToSearch(s)).not.toMatch(/claim|note/);
  });
});
