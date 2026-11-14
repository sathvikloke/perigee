import { useEffect, useRef, useState, type FormEvent } from 'react';
import {
  EMPTY_NOTES,
  NOTE_FIELDS,
  buildEvidenceCard,
  downloadCard,
  firstMissingNote,
  loadNotes,
  saveNotes,
  savedCards,
  storeCard,
  type EvidenceCard,
  type EvidenceContext,
  type NoteField,
  type Notes,
} from '../evidence';

const FIELD_TEXT: Record<NoteField, { label: string; hint: string; placeholder: string; max: number }> = {
  claim: { label: 'What’s your claim?', hint: 'Which pair is a fair test of change over time?', placeholder: 'I think these observations…', max: 1200 },
  observations: { label: 'What did you notice?', hint: 'Point to dates, wavelengths or visible details.', placeholder: 'The evidence that supports this is…', max: 2000 },
  uncertainty: { label: 'What remains uncertain?', hint: 'What would you need before saying more?', placeholder: 'I can’t conclude… because…', max: 2000 },
};

interface NotebookProps {
  context: EvidenceContext | null;
  claimHint?: string;
  attached: string;
}

export function Notebook({ context, claimHint, attached }: NotebookProps) {
  const key = context?.investigationKey ?? 'none';
  const [notes, setNotes] = useState<Notes>(EMPTY_NOTES);
  const [status, setStatus] = useState('Notes stay on this device');
  const [lastCard, setLastCard] = useState<EvidenceCard | null>(null);
  const [cardCount, setCardCount] = useState(() => savedCards().length);
  const refs = useRef<Partial<Record<NoteField, HTMLTextAreaElement | null>>>({});

  // Each investigation keeps its own notebook; switching pairs or blinking never touches it.
  useEffect(() => {
    const restored = loadNotes(key);
    setNotes(restored ?? EMPTY_NOTES);
    setLastCard(null);
    setStatus(restored && NOTE_FIELDS.some((f) => restored[f]) ? 'Restored from this device' : 'Notes stay on this device');
  }, [key]);

  const edit = (field: NoteField, value: string) => {
    refs.current[field]?.setCustomValidity('');
    const next = { ...notes, [field]: value };
    setNotes(next);
    setStatus(saveNotes(key, next) ? 'Saved on this device' : 'Storage unavailable · download to keep notes');
  };

  const save = (e: FormEvent) => {
    e.preventDefault();
    const missing = firstMissingNote(notes);
    if (missing) {
      const el = refs.current[missing];
      el?.setCustomValidity('Add a note before saving your evidence card.');
      el?.reportValidity();
      return;
    }
    if (!context || context.selected.length < 2) {
      setStatus('Select two loaded observations before saving');
      return;
    }
    const card = buildEvidenceCard(context, notes);
    const count = storeCard(card);
    setLastCard(card);
    if (count == null) {
      setStatus('Storage unavailable · download the card to keep it');
    } else {
      setCardCount(count);
      setStatus(`Evidence card saved on this device (${count} saved)`);
    }
  };

  const download = () => {
    const missing = firstMissingNote(notes);
    if (missing || !context || context.selected.length < 2) {
      setStatus('Save a complete evidence card first');
      return;
    }
    const card = lastCard ?? buildEvidenceCard(context, notes);
    downloadCard(card);
    setStatus('Evidence file downloaded');
  };

  return (
    <aside className="notebook" id="notebook" aria-labelledby="notebook-title">
      <div className="notebook-heading">
        <span className="notebook-icon" aria-hidden="true">▤</span>
        <div>
          <p className="eyebrow">Make your reasoning visible</p>
          <h2 id="notebook-title">Evidence notebook</h2>
        </div>
      </div>
      <div className="notebook-body">
        <p className="notebook-intro">
          A useful answer includes what you saw <em>and</em> what you still can’t tell.
        </p>
        <div className="attached">
          <span>Attached observations</span>
          <strong>{attached}</strong>
        </div>
        <form onSubmit={save} noValidate>
          {NOTE_FIELDS.map((field) => {
            const t = FIELD_TEXT[field];
            const hint = field === 'claim' && claimHint ? claimHint : t.hint;
            return (
              <div className="field" key={field}>
                <label htmlFor={`note-${field}`}>{t.label}</label>
                <span className="field-hint" id={`note-${field}-hint`}>
                  {hint}
                </span>
                <textarea
                  id={`note-${field}`}
                  ref={(el) => {
                    refs.current[field] = el;
                  }}
                  rows={3}
                  maxLength={t.max}
                  required
                  aria-describedby={`note-${field}-hint`}
                  placeholder={t.placeholder}
                  value={notes[field]}
                  onChange={(e) => edit(field, e.target.value)}
                />
                <p className="print-note">{notes[field] || '—'}</p>
              </div>
            );
          })}
          <div className="notebook-tip">
            <span aria-hidden="true">✧</span>
            <p>A different-looking image is a question to investigate, not yet a discovery.</p>
          </div>
          <button className="primary" type="submit">
            <span aria-hidden="true">✓</span> Save evidence card
          </button>
          <div className="notebook-actions">
            <button type="button" onClick={download}>
              Download JSON
            </button>
            <button type="button" onClick={() => window.print()}>
              Print / save PDF
            </button>
            <span role="status" className="save-status">
              {status}
            </span>
          </div>
          {cardCount > 0 ? <p className="card-count">{cardCount} evidence card{cardCount === 1 ? '' : 's'} saved in this browser</p> : null}
        </form>
      </div>
    </aside>
  );
}
