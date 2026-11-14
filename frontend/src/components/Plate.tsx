import type { FrameRecord } from '../api/types';
import { QUALITY_TEXT, detectorLabel, formatDate, formatWavelength, isoDate, qualityStatus, releaseLabel } from '../format';

interface PlateProps {
  letter: string;
  heading: string;
  frame: FrameRecord;
  targetName: string;
  showMarker: boolean;
  showFlags: boolean;
  /** Fixed guide line (percent from top), kept still while frames change. */
  guideY?: number | null;
  hidden?: boolean;
}

export function Plate({ letter, heading, frame: f, targetName, showMarker, showFlags, guideY, hidden }: PlateProps) {
  const date = formatDate(f.observed_at_utc);
  const wave = formatWavelength(f.wavelength_um);
  const q = qualityStatus(f);
  const qt = QUALITY_TEXT[q];
  const w = f.image.width || 256;
  const h = f.image.height || 256;
  const marker = f.marker && f.marker.on_grid !== false ? f.marker : null;
  const fov = f.registration?.fov_arcmin;
  const perFrame = f.display_scale?.mode === 'per_frame';
  const alt = `${targetName} field observed ${date ?? 'on an unstated date'}${wave ? ` at ${wave.replace('µm', 'micrometers')}` : ', wavelength not provided'}. Hatched areas have no usable data: outside the cutout, saturated or non-finite.`;

  return (
    <article className={`plate${hidden ? ' is-hidden' : ''}`} aria-label={`Observation ${letter}`}>
      <div className="plate-heading">
        <div>
          <span className="frame-letter">{letter}</span>
          <h3>{heading}</h3>
        </div>
        <span className={`quality q-${q}`}>
          <span aria-hidden="true">{qt.icon}</span> {qt.label}
        </span>
      </div>
      <p className="frame-meta">
        {date ? <time dateTime={isoDate(f.observed_at_utc)}>{date}</time> : <span className="missing">Date not provided</span>}
        <span className={wave ? 'wave' : 'wave missing'}>
          {wave ?? 'Wavelength not provided'}
        </span>
      </p>
      <div className="sky">
        <img src={f.image.src} alt={alt} width={w} height={h} />
        {showFlags && f.flag_image ? <img className="flags" src={f.flag_image.src} alt="" aria-hidden="true" /> : null}
        {guideY != null ? <span className="guide" style={{ top: `${guideY}%` }} aria-hidden="true" /> : null}
        {showMarker && marker ? (
          <span className="prediction" style={{ left: `${(marker.x / w) * 100}%`, top: `${(marker.y / h) * 100}%` }} aria-hidden="true" />
        ) : null}
        <span className="compass" aria-hidden="true">
          N ↑<br />E ←
        </span>
        {fov ? <span className="sky-scale">{fov} arcmin field</span> : null}
      </div>
      <div className="plate-foot">
        {marker ? (
          <>
            <span className="prediction-key" aria-hidden="true">⊕</span> Catalog prediction
          </>
        ) : (
          <span>No catalog marker</span>
        )}
        <span className="release">
          {releaseLabel(f.collection_id)} · {detectorLabel(f)}
        </span>
      </div>
      {q === 'not_covered' ? (
        <p className="coverage-note">The predicted position is just outside this image, so this frame cannot show the target. That is not evidence that the object is absent.</p>
      ) : null}
      {perFrame ? <p className="scale-note">Brightness scaled for this frame alone · not directly comparable</p> : null}
    </article>
  );
}

export function PlatePlaceholder({ letter, title, message, action }: { letter: string; title: string; message: string; action?: React.ReactNode }) {
  return (
    <article className="plate" aria-label={`Observation ${letter}`}>
      <div className="plate-heading">
        <div>
          <span className="frame-letter">{letter}</span>
          <h3>{title}</h3>
        </div>
      </div>
      <p className="frame-meta">&nbsp;</p>
      <div className="sky sky-empty" role="status">
        <p>{message}</p>
        {action}
      </div>
    </article>
  );
}
