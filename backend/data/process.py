"""Pure frame processing: FITS bytes + metadata in, FrameRecord + PNGs out.

No network, no filesystem paths, no web-app imports, no global state. The same function
builds live frames (API) and curated preset assets (tools/ingest/build_presets.py).
"""
from __future__ import annotations

import hashlib
import warnings

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord

from . import display
from .errors import DataError, ProcessingFailed, UnsupportedData
from .fits_io import open_cutout
from .grid import GridSpec, resample_bilinear, resample_nearest, source_pixel_coords
from .quality import adverse_bit_mask, screen_position
from .records import CatalogTarget, FrameContext, FrameProduct, frame_key
from .timeutil import mjd_to_iso, mjd_to_jyear
from .wavelength import wavelength_at

PROCESSING_VERSION = "perigee-data 0.1.0"

ACKNOWLEDGMENTS = [
    "SPHEREx data from the NASA/IPAC Infrared Science Archive (IRSA). SPHEREx is a NASA mission "
    "led by Caltech/JPL; IRSA is operated by Caltech/IPAC for NASA.",
]

STANDARD_LIMITATIONS = [
    "Display image only: resampled and contrast-stretched for viewing, not for measuring brightness.",
    "Resampling to the display grid does not add telescope resolution (SPHEREx pixels are 6.15 arcsec).",
    "The wavelength applies at the stated position only; SPHEREx wavelength changes across each image.",
]


def predicted_position(target: CatalogTarget, mjd: float) -> tuple[float, float, float]:
    """Propagate a catalog position to the observation epoch (finder marker only).

    Uses astropy's space-motion propagation with proper motion and, when the catalog has
    them, parallax distance and radial velocity (perspective acceleration matters for
    Barnard's Star: ~0.4" over 26 years). Annual parallax and binary orbits are not modeled.
    Times are built directly in TDB from Julian years, so no leap-second table is needed.
    Returns (ra_deg, dec_deg, epoch_jyear). Not an astrometric measurement.
    """
    from astropy.coordinates import Distance
    from astropy.time import Time

    epoch = mjd_to_jyear(mjd)
    if target.pm_ra_cosdec_masyr is None or target.pm_dec_masyr is None:
        return target.ra_deg, target.dec_deg, epoch
    kw = {}
    if target.parallax_mas and target.parallax_mas > 0:
        kw["distance"] = Distance(parallax=target.parallax_mas * u.mas)
        if target.radial_velocity_kms is not None:
            kw["radial_velocity"] = target.radial_velocity_kms * u.km / u.s
    c = SkyCoord(
        ra=target.ra_deg * u.deg,
        dec=target.dec_deg * u.deg,
        pm_ra_cosdec=target.pm_ra_cosdec_masyr * u.mas / u.yr,
        pm_dec=target.pm_dec_masyr * u.mas / u.yr,
        obstime=Time(target.epoch_jyear, format="jyear", scale="tdb"),
        frame="icrs",
        **kw,
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # astropy warns when no distance is given; that case is fine for a finder
        moved = c.apply_space_motion(new_obstime=Time(epoch, format="jyear", scale="tdb"))
    return float(moved.ra.deg), float(moved.dec.deg), epoch


def frame_id(key_: str, grid: GridSpec) -> str:
    key = f"{key_}|{grid.center_ra_deg:.7f}|{grid.center_dec_deg:.7f}|{grid.fov_arcmin:g}|{grid.size}|{PROCESSING_VERSION}"
    return "frm_" + hashlib.sha256(key.encode()).hexdigest()[:16]


def process_frame(fits_bytes: bytes, ctx: FrameContext) -> FrameProduct:
    try:
        return _process(fits_bytes, ctx)
    except DataError:
        raise
    except Exception as exc:  # never leak a stack trace or path to the user
        raise ProcessingFailed("frame processing failed") from exc


def _process(fits_bytes: bytes, ctx: FrameContext) -> FrameProduct:
    obs = ctx.observation
    cut = open_cutout(fits_bytes)

    # 1. The bytes must be the observation we were asked for.
    file_obs = (cut.meta.get("observation_id") or "").strip() or None
    file_det = cut.meta.get("detector")
    if (file_obs and file_obs != obs.observation_id) or (
        file_det is not None and obs.detector is not None and file_det != obs.detector
    ):
        raise UnsupportedData(
            "downloaded file does not match the requested observation",
            details={"expected": obs.frame_key, "file": frame_key(file_obs or "?", file_det)},
        )
    detector = file_det if file_det is not None else obs.detector

    # Time: mid-exposure from the header (board decision 2); fall back to start, then archive.
    limitations = list(STANDARD_LIMITATIONS)
    if cut.meta.get("mjd_avg") is not None:
        mjd, time_basis, time_note = cut.meta["mjd_avg"], "header_mjd_avg", "Mid-exposure time (DATE-AVG / MJD-AVG) from the file header."
        date_str = cut.meta.get("date_avg")
    elif cut.meta.get("mjd_obs") is not None:
        mjd, time_basis, time_note = cut.meta["mjd_obs"], "header_mjd_obs", "Exposure start (DATE-OBS / MJD-OBS); the file has no mid-exposure time."
        date_str = cut.meta.get("date_obs")
    elif obs.mjd is not None:
        mjd, time_basis, time_note, date_str = obs.mjd, "archive_t_min", "Exposure start from the archive record; the file header has no time.", None
    else:
        raise UnsupportedData("observation time is missing from the file and the archive record")
    observed_at = (str(date_str).strip() + "Z") if date_str else mjd_to_iso(mjd)
    if obs.mjd is not None and abs(obs.mjd - mjd) > 0.01:
        limitations.append("The archive record and the file header disagree on the observation time; the header time is shown.")

    grid = GridSpec(ctx.center_ra_deg, ctx.center_dec_deg, ctx.fov_arcmin, ctx.grid_size)

    # 2. Where to evaluate wavelength and quality: predicted target position, else field center.
    marker = None
    if ctx.target is not None:
        pra, pdec, epoch = predicted_position(ctx.target, mjd)
        where = "predicted target position"
        dx, dy = grid.to_display_xy(pra, pdec)
        if 0 <= dx <= grid.size and 0 <= dy <= grid.size:
            marker = {
                "x": round(dx, 2),
                "y": round(dy, 2),
                "ra_deg": pra,
                "dec_deg": pdec,
                "kind": "catalog_prediction",
                "label": "Catalog prediction (not a detection)",
                "epoch_mjd": mjd,
                "epoch_utc": mjd_to_iso(mjd),
                "epoch_jyear": round(epoch, 4),
                "source": (
                    f"{ctx.target.name}: catalog position (epoch J{ctx.target.epoch_jyear:g}) propagated with catalog proper motion"
                    + (", parallax distance and radial velocity" if ctx.target.radial_velocity_kms is not None else "")
                    + f" to this frame's time. Not a measured position. Catalog: {ctx.target.source}"
                ),
            }
        else:
            limitations.append("The catalog-predicted target position falls outside the displayed field.")
    else:
        pra, pdec = ctx.center_ra_deg, ctx.center_dec_deg
        where = "query position"

    # 3. Wavelength at that position.
    wl = wavelength_at(cut, pra, pdec)
    if wl.wavelength_um is None:
        limitations.append(f"Wavelength unknown: {wl.note}.")
        wl_location = f"Not available at the {where}: {wl.note}."
    else:
        wl_location = f"Evaluated at the {where} (RA {pra:.5f}, Dec {pdec:.5f}) from the file's spectral lookup table."

    # 4. Coverage and flags at that position.
    q = screen_position(cut, pra, pdec, what=where)
    if q.status == "flagged":
        limitations.append("Pixels at the checked position are flagged; do not use this frame for brightness or position measurements there.")
    elif q.status == "not_covered":
        limitations.append(f"This image does not cover the {where}.")

    # 5. Resample onto the fixed grid.
    sx, sy = source_pixel_coords(grid, cut.wcs)
    img = resample_bilinear(cut.image, sx, sy)
    valid_frac = float(np.isfinite(img).mean())
    if valid_frac == 0.0:
        raise UnsupportedData("cutout does not overlap the display field")
    if valid_frac < 0.98:
        limitations.append(f"The image covers {valid_frac:.0%} of the displayed field; the rest is shown as empty (transparent).")

    flag_png = None
    flag_image = None
    if cut.flags is not None:
        fl, inside = resample_nearest(cut.flags, sx, sy, fill=0)
        adverse = (fl & adverse_bit_mask(cut.flag_bits)) != 0
        flag_png = display.flag_overlay_png(adverse, inside & np.isfinite(img))
        flag_image = {
            "src": None,
            "width": grid.size,
            "height": grid.size,
            "media_type": "image/png",
            "meaning": "Hatched pixels carry at least one adverse SPHEREx flag (informational SOURCE/FULLSAMPLE flags are not drawn).",
        }

    # 6. Display stretch.
    offset = display.background_offset(img)
    shown = img - (offset or 0.0)
    auto = display.per_frame_limits(shown)
    if auto is None:
        raise UnsupportedData("too few valid pixels to display this frame")
    if ctx.shared_scale is not None:
        mode, scale = "shared", ctx.shared_scale
    else:
        mode, scale = "per_frame", auto
        limitations.append("Contrast is set per frame, so brightness differences between frames are not meaningful.")
    image_png = display.intensity_png(shown, scale)

    record = {
        "frame_id": frame_id(frame_key(obs.observation_id, detector), grid),
        "frame_key": frame_key(obs.observation_id, detector),
        "observation_id": obs.observation_id,
        "collection_id": obs.collection_id,
        "observed_at_utc": observed_at,
        "mjd": mjd,
        "time_basis": time_basis,
        "detector": detector,
        "source_url": obs.source_url,
        "wavelength_um": wl.wavelength_um,
        "bandwidth_um": wl.bandwidth_um,
        "wavelength_location": wl_location,
        "image": {"src": None, "width": grid.size, "height": grid.size, "media_type": "image/png"},
        "flag_image": flag_image,
        "registration": grid.registration(),
        "quality": q.contract_dict(),
        "display_scale": display.scale_record(mode, scale, offset),
        "marker": marker,
        "provenance": {
            "data_origin": "nasa_archive",
            "retrieved_at": ctx.retrieved_at_utc,
            "retrieved_at_basis": ctx.retrieved_at_basis,
            "original_url": obs.source_url,
            "cutout_url": ctx.cutout_url,
            "sha256": hashlib.sha256(fits_bytes).hexdigest(),
            "processing_version": PROCESSING_VERSION,
            "pipeline_version": cut.meta.get("pipeline_version"),
            "time_note": time_note,
            "acknowledgments": list(ACKNOWLEDGMENTS),
        },
        "limitations": limitations,
    }
    stats = {
        "background_offset": offset,
        "display_values_finite": int(np.isfinite(shown).sum()),
        "auto_scale": {"low": auto.low, "high": auto.high, "asinh_softening": auto.asinh_softening},
        "quality_flag_counts": q.flag_counts,
        "quality_pixel_xy": (q.pixel_x, q.pixel_y),
        "wavelength_pixel_xy": (wl.pixel_x, wl.pixel_y),
        "valid_fraction": valid_frac,
    }
    cut.hdul.close()
    return FrameProduct(record=record, image_png=image_png, flag_png=flag_png, stats=stats)
