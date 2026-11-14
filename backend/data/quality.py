"""Coverage and flag screen around one sky position.

This is a narrow screen, not a detection test and not photometry. It answers:
"Is this position on the image, and are the pixels right around it free of the flags that
make a pixel unreliable?"

Aperture: pixels whose centers lie within APERTURE_RADIUS_PX native SPHEREx pixels
(6.15 arcsec each) of the position, about 19-21 pixels. Same size as the original audit,
so the new results can be compared with it.

Flag classes (bit names are read from each file's FLAGS header, not hard-coded):
  informational: SOURCE (pixel lies on a catalogued source) and FULLSAMPLE (extra readout
                 history exists). These describe the pixel, they do not mark it bad.
  adverse:       every other named flag (TRANSIENT, OVERFLOW, SUR_ERROR, NONFUNC, DICHROIC,
                 MISSING_DATA, HOT, COLD, PHANMISS, NONLINEAR, PERSIST, OUTLIER, CROSSTALK,
                 GHOST*, STREAK, BLOOM, SNOWBALL, HALO ...), plus any set bit the header does
                 not name. This matches the original audit's "conservative screen".

Status rules (contract `quality.status`), applied in this order:
  not_covered  the position itself is off the cutout (geometric only, board decision 3)
  flagged      at least one pixel in the aperture has an adverse flag, a non-finite value, or a
               non-finite / non-positive variance. A saturated star core is often NaN *and*
               flagged OVERFLOW: that is "flagged", never "not covered".
  unknown      flag mask or variance missing, or fewer than MIN_VALID_PIXELS usable pixels
               with no adverse flag (too little to say "clear")
  clear        none of the above
"Usable" = finite value, no adverse flag, positive finite variance.
Stricter than the board on purpose: a missing VARIANCE extension gives "unknown", not
"clear" (contract scenario 15), and so does a clipped edge aperture with < 10 usable pixels.
`None` counts mean "not measured". A zero is only reported when pixels were really counted.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field

import numpy as np

from .fits_io import SpherexCutout

APERTURE_RADIUS_PX = 2.5
MIN_VALID_PIXELS = 10
INFORMATIONAL_FLAGS = frozenset({"SOURCE", "FULLSAMPLE"})

FLAG_EXPLANATIONS = {
    "TRANSIENT": "a cosmic-ray-like jump during the exposure",
    "OVERFLOW": "the pixel neared saturation",
    "SUR_ERROR": "onboard slope fit had an error",
    "NONFUNC": "permanently unusable pixel",
    "DICHROIC": "low efficiency from the dichroic",
    "MISSING_DATA": "data lost onboard",
    "HOT": "hot pixel",
    "COLD": "anomalously low signal",
    "PHANMISS": "phantom correction not applied",
    "NONLINEAR": "nonlinearity correction unreliable",
    "PERSIST": "charge left over from an earlier bright exposure",
    "OUTLIER": "statistical outlier",
    "CROSSTALK": "electronic crosstalk",
    "GHOST": "optical ghost from a bright source in the exposure",
    "GHOST_FPA": "optical ghost from a source on another detector",
    "GHOST_EXT": "optical ghost from a source outside the field",
    "STREAK": "satellite or other streak",
    "BLOOM": "bloom from a saturated bright source",
    "SNOWBALL": "snowball artifact",
    "HALO": "halo around a transient",
}


@dataclass
class QualityScreen:
    status: str
    covered: bool
    valid_aperture_pixels: int | None
    adverse_aperture_pixels: int | None
    flag_names: list[str]
    notes: list[str]
    aperture_pixels: int | None = None
    flag_counts: dict[str, int] = field(default_factory=dict)  # includes informational ones
    pixel_x: float | None = None
    pixel_y: float | None = None

    def contract_dict(self) -> dict:
        return {
            "status": self.status,
            "covered": self.covered,
            "valid_aperture_pixels": self.valid_aperture_pixels,
            "adverse_aperture_pixels": self.adverse_aperture_pixels,
            "flag_names": list(self.flag_names),
            "notes": list(self.notes),
        }


def adverse_bit_mask(flag_bits: dict[str, int]) -> int:
    """All bits except the informational ones. Unnamed bits count as adverse."""
    informational = 0
    for name, bit in flag_bits.items():
        if name in INFORMATIONAL_FLAGS:
            informational |= bit
    return ~informational & 0x7FFFFFFF


def screen_position(cut: SpherexCutout, ra_deg: float, dec_deg: float, *, what: str = "position") -> QualityScreen:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        x, y = cut.wcs.world_to_pixel_values(ra_deg, dec_deg)
    x, y = float(x), float(y)
    ny, nx = cut.shape
    if not (np.isfinite(x) and np.isfinite(y)):
        return QualityScreen("not_covered", False, None, None, [], [f"The {what} could not be placed on this image."])

    # Coverage first: the position itself must be on the image.
    if not (-0.5 <= x <= nx - 0.5 and -0.5 <= y <= ny - 0.5):
        return QualityScreen(
            "not_covered", False, None, None, [],
            [f"The {what} is outside the area this image covers."],
            pixel_x=x, pixel_y=y,
        )
    yy, xx = np.mgrid[0:ny, 0:nx]
    in_ap = (xx - x) ** 2 + (yy - y) ** 2 <= APERTURE_RADIUS_PX**2
    n_ap = int(in_ap.sum())

    notes: list[str] = []
    partial_edge = n_ap < int(np.pi * APERTURE_RADIUS_PX**2 * 0.9)
    if partial_edge:
        notes.append(f"The {what} is near the image edge; only part of the check area is on the image.")

    nonfinite = in_ap & ~np.isfinite(cut.image)
    if cut.variance is not None:
        with np.errstate(invalid="ignore"):
            nonfinite |= in_ap & ~(np.isfinite(cut.variance) & (cut.variance > 0))
    n_nonfinite = int(nonfinite.sum())
    if n_nonfinite:
        notes.append(
            f"{n_nonfinite} of the {n_ap} pixels have no usable value (typical of a saturated bright source). "
            "The position is covered, so this is a quality problem, not missing coverage."
        )

    if cut.flags is None:
        notes.append("This file has no readable flag mask, so the SPHEREx pixel flags could not be checked.")
        status = "flagged" if n_nonfinite else "unknown"
        return QualityScreen(status, True, None, n_nonfinite if n_nonfinite else None, [], notes,
                             aperture_pixels=n_ap, pixel_x=x, pixel_y=y)

    flags = cut.flags
    adverse = adverse_bit_mask(cut.flag_bits)
    ap_flags = flags[in_ap]
    counts: dict[str, int] = {}
    named_bits = 0
    for name, bit in cut.flag_bits.items():
        named_bits |= bit
        c = int(((ap_flags & bit) != 0).sum())
        if c:
            counts[name] = c
    unnamed = ap_flags & ~named_bits & 0x7FFFFFFF
    for b in range(31):
        c = int(((unnamed >> b) & 1).sum())
        if c:
            counts[f"UNDOCUMENTED_BIT_{b}"] = c

    adverse_px = (in_ap & ((flags & adverse) != 0)) | nonfinite
    usable = in_ap & ~adverse_px
    n_adverse = int(adverse_px.sum())
    n_valid = int(usable.sum())
    adverse_names = sorted(k for k in counts if k not in INFORMATIONAL_FLAGS)
    info_names = sorted(k for k in counts if k in INFORMATIONAL_FLAGS)

    if n_adverse > 0:
        status = "flagged"
        if adverse_names:
            expl = "; ".join(f"{n} ({FLAG_EXPLANATIONS.get(n, 'see SPHEREx flag documentation')})" for n in adverse_names)
            notes.insert(0, f"{n_adverse} of {n_ap} pixels at the {what} are flagged or have no usable value. Flags: {expl}.")
    elif cut.variance is None:
        status = "unknown"
        notes.append("This file has no variance map, so the pixels could not be fully checked.")
    elif n_valid < MIN_VALID_PIXELS:
        status = "unknown"
        notes.append(f"Only {n_valid} usable pixels at the {what}; at least {MIN_VALID_PIXELS} are needed for a clear screen.")
    else:
        status = "clear"
        notes.append(
            f"{n_valid} pixels at the {what} have no adverse flags. This is a pixel-quality screen only: "
            "it does not show that a source was detected or that its brightness was measured."
        )
    if info_names:
        notes.append(
            "Informational flags present: "
            + ", ".join(info_names)
            + (" (SOURCE means the pixel lies on a catalogued source; it is not a defect)." if "SOURCE" in info_names else ".")
        )
    return QualityScreen(
        status, True, n_valid, n_adverse, adverse_names, notes,
        aperture_pixels=n_ap, flag_counts=counts, pixel_x=x, pixel_y=y,
    )
