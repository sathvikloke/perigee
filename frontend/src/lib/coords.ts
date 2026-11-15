// Coordinate query validation matching docs/INTEGRATION_CONTRACT.md "Query request":
// finite RA in [0,360), Dec in [-90,90], FOV 2–10 arcmin (default 6), limit
// 1–48 (frontend default 12). Reject NaN, infinity and partly parsed strings; never
// clip silently. Exactly 360 is normalized to 0 with a visible notice.

export const FOV_MIN = 2;
export const FOV_MAX = 10;
export const FOV_DEFAULT = 6;
export const LIMIT_MIN = 1;
export const LIMIT_MAX = 48;
export const LIMIT_DEFAULT = 12;

const DECIMAL = /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/;

/** Parses a whole string as a finite decimal number, or returns null. */
export function parseStrictNumber(input: string): number | null {
  const s = input.trim();
  if (!DECIMAL.test(s)) return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

/** A colon-separated RA is hours; a decimal RA is always degrees. */
export function parseCoordinate(input: string, axis: "ra" | "dec"): number | null {
  const text = input.trim();
  if (!text.includes(":")) return parseStrictNumber(text);
  const match = /^([+-]?)(\d{1,2}):(\d{2}):(\d{2}(?:\.\d+)?)$/.exec(text);
  if (!match) return null;
  const [, sign, wholeText, minutesText, secondsText] = match;
  const whole = Number(wholeText), minutes = Number(minutesText), seconds = Number(secondsText);
  if (minutes >= 60 || seconds >= 60) return null;
  if (axis === "ra" && (sign === "-" || whole >= 24)) return null;
  if (axis === "dec" && (whole > 90 || (whole === 90 && (minutes !== 0 || seconds !== 0)))) return null;
  const value = whole + minutes / 60 + seconds / 3600;
  return (sign === "-" ? -1 : 1) * value * (axis === "ra" ? 15 : 1);
}

export interface QueryInput {
  ra: string;
  dec: string;
  fov: string;
  limit: string;
}

export interface ValidQuery {
  ra_deg: number;
  dec_deg: number;
  fov_arcmin: number;
  limit: number;
}

export type QueryErrors = Partial<Record<keyof QueryInput, string>>;

export function validateQuery(
  input: QueryInput,
): { ok: true; value: ValidQuery; notices: string[] } | { ok: false; errors: QueryErrors } {
  const errors: QueryErrors = {};
  const notices: string[] = [];

  let ra = parseCoordinate(input.ra, "ra");
  if (ra === null) errors.ra = "Enter degrees (269.4463) or hours:minutes:seconds (17:57:47.1).";
  else if (ra === 360) {
    ra = 0;
    notices.push("Right ascension 360° is the same direction as 0°; sending 0.");
  } else if (ra < 0 || ra >= 360) errors.ra = "Right ascension must be at least 0 and less than 360 degrees.";

  const dec = parseCoordinate(input.dec, "dec");
  if (dec === null) errors.dec = "Enter degrees (+4.7683) or degrees:minutes:seconds (+04:46:06).";
  else if (dec < -90 || dec > 90) errors.dec = "Declination must be between -90 and 90 degrees.";

  const fovText = input.fov.trim() === "" ? String(FOV_DEFAULT) : input.fov;
  const fov = parseStrictNumber(fovText);
  if (fov === null || fov < FOV_MIN || fov > FOV_MAX) {
    errors.fov = `Field of view must be a number from ${FOV_MIN} to ${FOV_MAX} arcminutes.`;
  }

  const limitText = input.limit.trim() === "" ? String(LIMIT_DEFAULT) : input.limit;
  const limit = parseStrictNumber(limitText);
  if (limit === null || !Number.isInteger(limit) || limit < LIMIT_MIN || limit > LIMIT_MAX) {
    errors.limit = `Result limit must be a whole number from ${LIMIT_MIN} to ${LIMIT_MAX}.`;
  }

  if (Object.keys(errors).length) return { ok: false, errors };
  return {
    ok: true,
    value: { ra_deg: ra as number, dec_deg: dec as number, fov_arcmin: fov as number, limit: limit as number },
    notices,
  };
}
