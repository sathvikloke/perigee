import { afterEach, describe, expect, it } from 'vitest';
import { ApiError, api, createLatest, loadFrames, setFetch } from '../src/api/client';
import type { ObservationDescriptor } from '../src/api/types';
import frameExample from '../../backend/tests/api/examples/frame_response.fixture.json';
import expiredExample from '../../backend/tests/api/examples/error.token_expired.json';

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });

const descriptor = (token: string): ObservationDescriptor => ({
  observation_id: token,
  collection_id: 'spherex_dr1',
  observed_at_utc: null,
  mjd: null,
  source_url: 'https://irsa.ipac.caltech.edu/x.fits',
  frame_token: token,
});

afterEach(() => setFetch((...a) => fetch(...a)));

describe('createLatest stale guard', () => {
  it('only the newest ticket is current and older signals abort', () => {
    const latest = createLatest();
    const first = latest.next();
    const second = latest.next();
    expect(first.isCurrent()).toBe(false);
    expect(first.signal.aborted).toBe(true);
    expect(second.isCurrent()).toBe(true);
    latest.cancel();
    expect(second.isCurrent()).toBe(false);
  });

  it('drops frame results from an older query even if they resolve late', async () => {
    const pending: Record<string, (r: Response) => void> = {};
    setFetch(((_url: string, init?: RequestInit) => {
      const token = JSON.parse(String(init?.body)).frame_token as string;
      return new Promise<Response>((resolve) => (pending[token] = resolve));
    }) as typeof fetch);

    const latest = createLatest();
    const seen: string[] = [];
    const old = latest.next();
    // the old query never aborts its fetch in this fake, so only the ticket check protects us
    const oldRun = loadFrames([descriptor('old-1')], (o) => o.ok && seen.push(`old:${o.frame.frame_id}`), {
      isCurrent: old.isCurrent,
    });
    const now = latest.next();
    const newRun = loadFrames([descriptor('new-1')], (o) => o.ok && seen.push(`new:${o.frame.frame_id}`), {
      isCurrent: now.isCurrent,
    });

    await Promise.resolve();
    pending['new-1'](json({ request_id: 'n', frame: { ...frameExample.frame, frame_id: 'NEW' } }));
    pending['old-1'](json({ request_id: 'o', frame: { ...frameExample.frame, frame_id: 'OLD' } }));
    await Promise.all([oldRun, newRun]);
    expect(seen).toEqual(['new:NEW']);
  });
});

describe('loadFrames', () => {
  it('limits concurrency to two and reports failures by index without reordering', async () => {
    let inFlight = 0;
    let peak = 0;
    setFetch((async (_url: string, init?: RequestInit) => {
      const token = JSON.parse(String(init?.body)).frame_token as string;
      inFlight++;
      peak = Math.max(peak, inFlight);
      await new Promise((r) => setTimeout(r, 5));
      inFlight--;
      if (token === 't2') return json(expiredExample, 401);
      return json({ request_id: token, frame: { ...frameExample.frame, frame_id: token } });
    }) as typeof fetch);

    const results: string[] = [];
    await loadFrames(['t0', 't1', 't2', 't3', 't4'].map(descriptor), (o) =>
      results[o.index] = o.ok ? o.frame.frame_id : `error:${o.error.code}`,
    );
    expect(peak).toBe(2);
    expect(results).toEqual(['t0', 't1', 'error:TOKEN_EXPIRED', 't3', 't4']);
  });
});

describe('request errors', () => {
  it('maps the error envelope to ApiError', async () => {
    setFetch((async () => json(expiredExample, 401)) as typeof fetch);
    await expect(api.frame('x')).rejects.toMatchObject({ code: 'TOKEN_EXPIRED', retryable: false, status: 401 });
  });

  it('never treats an HTML fallback page as success', async () => {
    setFetch((async () => new Response('<!doctype html>', { status: 200, headers: { 'content-type': 'text/html' } })) as typeof fetch);
    const err = await api.presets().catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.code).toBe('BAD_RESPONSE');
  });

  it('reports a network failure as retryable, not as an empty result', async () => {
    setFetch((async () => {
      throw new TypeError('Failed to fetch');
    }) as typeof fetch);
    await expect(api.search({ ra_deg: 1, dec_deg: 2, fov_arcmin: 6, limit: 12 })).rejects.toMatchObject({ code: 'NETWORK', retryable: true });
  });
});
