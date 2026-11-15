import type { ValidQuery } from "./coords";

/** A frame ID alone does not identify a cutout. The signed token also binds its release. */
export function frameCacheKey(mode: string, frameKey: string, token: string, query: ValidQuery): string {
  return JSON.stringify([mode, frameKey, query.ra_deg, query.dec_deg, query.fov_arcmin, token]);
}

export function rememberFrame<T>(cache: Map<string, T>, key: string, frame: T): void {
  cache.delete(key);
  cache.set(key, frame);
  if (cache.size > 128) cache.delete(cache.keys().next().value!);
}
