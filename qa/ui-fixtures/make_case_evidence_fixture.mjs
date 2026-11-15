// N4: evidence-record fixture and reproducibility check for the staged third
// investigation (science/staging/wise_0855_quality_trap).
//
// Records are normalized by the shipped API client (frontend/src/api/client.ts
// normalizePresetFrames) and cards are built with the shipped evidence code
// (frontend/src/evidence/card.ts: createEvidenceCard, toggleEvidenceFrame,
// updateEvidenceText, validateEvidenceCard, serializeEvidenceCard), imported
// read-only. Node must strip TypeScript types (Node >= 22.18 or 23.6).
//
//   node qa/ui-fixtures/make_case_evidence_fixture.mjs [--data-root <build_data>]
//
// Writes qa/ui-fixtures/evidence_card.wise_0855_quality_trap.illustrative.json
// and qa/ui-fixtures/case_evidence_check.json. Exits 1 if any check fails.
//
// The learner text in the cards is ILLUSTRATIVE, written by the coordinator to
// show the shape of an initial and a revised claim. It is not from any real
// participant.
import { createHash } from "node:crypto";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { register } from "node:module";

// frontend/src uses extensionless relative imports (Vite resolves them); map them to .ts.
register(
  "data:text/javascript,export async function resolve(s,c,n){try{return await n(s,c)}catch(e){if(s.startsWith('.')&&!/\\.[a-z]+$/.test(s))return n(s+'.ts',c);throw e}}",
);
const { createEvidenceCard, serializeEvidenceCard, toggleEvidenceFrame, updateEvidenceText, validateEvidenceCard, CLAIM_MAX } =
  await import("../../frontend/src/evidence/card.ts");
// Records reach the card code through the shipped API client normalizer (it maps
// the processor's provenance.sha256 to file_sha256), exactly as in the app.
const { normalizePresetFrames } = await import("../../frontend/src/api/client.ts");

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, "..", "..");
const STAGE = path.join(REPO, "science", "staging", "wise_0855_quality_trap");
const PRODUCTS = path.join(STAGE, "presets", "wise_0855", "case-wise_0855_quality_trap");
const argv = process.argv.slice(2);
const dataRoot = argv.includes("--data-root") ? argv[argv.indexOf("--data-root") + 1] : null;

const sha256 = (buf) => createHash("sha256").update(buf).digest("hex");
const readJson = (p) => JSON.parse(readFileSync(p, "utf8"));
const rel = (p) => path.relative(REPO, p);

const caseDoc = readJson(path.join(STAGE, "case.json"));
const framesDoc = readJson(path.join(PRODUCTS, "frames.json"));
const answerEvidence = readJson(path.join(REPO, "science/reviews/transfer-exercise/answer_evidence.json"));
const byRef = Object.fromEntries(framesDoc.frames.map((f) => [f.case_ref, f]));
const normalized = normalizePresetFrames(framesDoc);
const normFrames = normalized.frames ?? normalized;
const normByKey = Object.fromEntries(normFrames.map((f) => [f.frame_key, f]));

// ---------------------------------------------------------------------------
// 1. Reproducibility check: case.json frame references vs the referenced records
const checks = [];
const check = (name, ok, detail) => checks.push({ name, ok: Boolean(ok), detail });

for (const cf of caseDoc.frames) {
  const rec = byRef[cf.ref];
  const tag = `frame ${cf.ref} (${cf.frame_key})`;
  check(`${tag}: record exists`, rec && rec.frame_key === cf.frame_key, rec ? rec.frame_key : "missing");
  if (!rec) continue;
  for (const k of ["observation_id", "detector", "collection_id", "source_url", "mjd", "time_basis"]) {
    check(`${tag}: ${k}`, rec[k] === cf[k], { case: cf[k], record: rec[k] });
  }
  // case.json writes UTC without the trailing Z; the record carries it.
  check(`${tag}: observed_at_utc`, rec.observed_at_utc === `${cf.observed_at_utc}Z`, { case: cf.observed_at_utc, record: rec.observed_at_utc });
  check(`${tag}: wavelength_um (case rounds to 4 dp)`, Math.abs(rec.wavelength_um - cf.wavelength_um) <= 0.00005, { case: cf.wavelength_um, record: rec.wavelength_um });
  check(`${tag}: bandwidth_um (case rounds to 4 dp)`, Math.abs(rec.bandwidth_um - cf.bandwidth_um) <= 0.00005, { case: cf.bandwidth_um, record: rec.bandwidth_um });
  check(`${tag}: quality status`, rec.quality.status === cf.expected_quality_status, { case: cf.expected_quality_status, record: rec.quality.status, flags: rec.quality.flag_names });
  check(`${tag}: cutout sha256 = record provenance.sha256`, rec.provenance.sha256 === cf.sha256_of_retained_cutout, rec.provenance.sha256);
  check(`${tag}: display_scale unit`, rec.display_scale.unit === "MJy / sr", rec.display_scale.unit);
  check(`${tag}: grid shared with case grid_id`, rec.registration.grid_id === framesDoc.grid_id, rec.registration.grid_id);
  check(`${tag}: marker is a catalog prediction`, rec.marker.kind === "catalog_prediction", rec.marker.kind);
  check(`${tag}: processing_version`, rec.provenance.processing_version === framesDoc.processing_version, rec.provenance.processing_version);
  for (const [field, img] of [["image", rec.image], ["flag_image", rec.flag_image]]) {
    const id = img.src.split("/").pop();
    const p = path.join(STAGE, "presets", framesDoc.assets[id] || "__missing__");
    check(`${tag}: ${field} asset present`, existsSync(p), rel(p));
    if (existsSync(p)) checks[checks.length - 1].detail = { path: rel(p), sha256: sha256(readFileSync(p)) };
  }
}
// Display-scale descriptions: A and B share one stretch, C has its own.
const [A, B, C] = ["A", "B", "C"].map((r) => byRef[r]);
check("A/B share one stretch (mode shared, identical low/high)", A.display_scale.mode === "shared" && B.display_scale.mode === "shared" && A.display_scale.low === B.display_scale.low && A.display_scale.high === B.display_scale.high, { low: A.display_scale.low, high: A.display_scale.high });
check("C has its own stretch (mode per_frame)", C.display_scale.mode === "per_frame", C.display_scale);
check("case display_requirements says A/B shared, C own stretch", /A and B share one asinh stretch/.test(caseDoc.display_requirements.stretch) && /C has its own stretch/.test(caseDoc.display_requirements.stretch), caseDoc.display_requirements.stretch);
// Optional: raw retained cutouts on disk hash to the recorded sha256.
if (dataRoot) {
  const manifest = readJson(path.join(dataRoot, "manifest.json"));
  for (const cf of caseDoc.frames) {
    const ent = manifest.files.find((e) => e.sha256 === cf.sha256_of_retained_cutout && e.status !== "failed");
    const p = ent && path.join(dataRoot, ent.file);
    const ok = p && existsSync(p) && sha256(readFileSync(p)) === cf.sha256_of_retained_cutout;
    check(`frame ${cf.ref}: retained raw cutout on disk hashes to sha256_of_retained_cutout`, ok, ent ? ent.file : "no manifest entry");
  }
} else {
  check("raw cutout hashes (skipped: no --data-root)", true, "skipped");
}

// ---------------------------------------------------------------------------
// 2. Illustrative evidence cards built with the shipped card code
const NOW0 = new Date("2026-11-15T00:00:00.000Z"); // fixed, so the fixture is deterministic
const NOW1 = new Date("2026-11-15T00:05:00.000Z");
const NOW2 = new Date("2026-11-15T00:12:00.000Z");
const base = createEvidenceCard({
  id: "00000000-0000-4000-8000-illustrative1",
  case_id: caseDoc.case_id,
  preset_id: caseDoc.target_id,
  title: caseDoc.title,
  case_limitations: caseDoc.limitations,
  query: null,
  sources: [{ label: "SPHEREx data at NASA/IPAC IRSA", url: "https://irsa.ipac.caltech.edu/Missions/spherex.html" }],
  app_version: "fixture",
  data_origin: "fixture",
  now: NOW0,
});
let card = toggleEvidenceFrame(base, normByKey[A.frame_key], "A", NOW0);
card = toggleEvidenceFrame(card, normByKey[B.frame_key], "B", NOW0);

const initialText = {
  claim: "A bright dot moved between 7 and 10 November while the stars stayed still, so something near WISE 0855 may be moving.",
  observations: "Blinking A and B, one dot above and left of the centre jumps a few display pixels. Another dot near the left edge is only in A.",
  uncertainty: "I have not checked the dates, wavelengths or flagged pixels yet.",
};
let initial = card;
for (const [k, v] of Object.entries(initialText)) initial = updateEvidenceText(initial, k, v, NOW1);

const revisedText = {
  claim: "A and B match in wavelength, but the dot that jumps is one flagged detector pixel in both, and the dot only in A is flagged too. Among the dots I checked, nothing supports a new or moving object.",
  observations: "With 'Show flagged pixels' on, the jumping dot is covered in A and B and is one native pixel wide (NONFUNC, TRANSIENT, SUR_ERROR). The dot only in A is flagged (TRANSIENT, OUTLIER, HALO, SUR_ERROR) and B shows background there. The dot by the marker lines up with a catalogued star. B is flagged PERSIST at the marker.",
  uncertainty: "I only checked the bright dots, using display images and flags. The flags do not tell me what caused those pixels. WISE 0855 should be too faint at these wavelengths, so these images cannot show whether it moved.",
};
let revised = initial;
for (const [k, v] of Object.entries(revisedText)) revised = updateEvidenceText(revised, k, v, NOW2);

for (const [name, c] of [["initial", initial], ["revised", revised]]) {
  const v = validateEvidenceCard(JSON.parse(serializeEvidenceCard(c)));
  check(`${name} card passes the shipped validateEvidenceCard`, v.ok, v.ok ? "ok" : v.errors);
  check(`${name} claim within CLAIM_MAX (${CLAIM_MAX})`, c.claim.length <= CLAIM_MAX, c.claim.length);
  check(`${name} card claim is not the case's reference example_claim`, c.claim !== caseDoc.conclusion_guide.example_claim, "learner text is separate from the reference answer");
  check(`${name} card meets evidence_requirements (A and B attached)`, ["A", "B"].every((r) => c.frames.some((f) => f.ref === r)), c.frames.map((f) => f.ref));
  for (const f of c.frames) {
    const rec = byRef[f.ref];
    check(`${name} card frame ${f.ref}: fields equal the record`, f.frame_key === rec.frame_key && f.observed_at_utc === rec.observed_at_utc && f.wavelength_um === rec.wavelength_um && f.quality_status === rec.quality.status && f.display_scale_mode === rec.display_scale.mode && f.processing.file_sha256 === rec.provenance.sha256 && f.source_url === rec.source_url, { frame_key: f.frame_key, quality_status: f.quality_status, display_scale_mode: f.display_scale_mode });
  }
}

const aeIds = (answerEvidence.answers || []).map((r) => r.id);
const fixture = {
  label: "ILLUSTRATIVE LEARNER RECORD. The claim, observations and uncertainty text were written by the coordinator to show the shape of an initial and a revised claim. They are not from a real participant and must never be presented as user feedback.",
  generated_by: "qa/ui-fixtures/make_case_evidence_fixture.mjs (cards built with frontend/src/evidence/card.ts, schema_version 1)",
  case_id: caseDoc.case_id,
  case_status: caseDoc.status,
  initial_card: JSON.parse(serializeEvidenceCard(initial)),
  revised_card: JSON.parse(serializeEvidenceCard(revised)),
  revision: {
    what_changed: "The learner turned on 'Show flagged pixels' (case steps jumping_dot and only_in_a) and read the flag names; the claim moved from 'something may be moving' to 'nothing among the checked dots supports a new or moving object'.",
    justifying_observation: "The flag overlay covers the jumping dot in both A and B, and the dot is one native pixel wide.",
    computed_facts_backing_the_reference_answer: [
      { fact: "Jumping dot = detector pixel (1709, 1364) in both frames; display (114.9, 82.9) in A, (117.9, 80.6) in B; apparent shift 3.81 display px = 5.36 arcsec, matching the 5.38 arcsec predicted from the field-star pointing shift.", source: "science/reviews/overnight-controls/results/B_features.csv; science/reviews/transfer-exercise/answer_evidence.json A2_jumping_dot" },
      { fact: "Dot only in A = detector pixel (1689, 1364), display (32.4, 111.8), flagged HALO, OUTLIER, SUR_ERROR, TRANSIENT; B at the same detector pixel reads 0.27 MJy/sr with no adverse flag.", source: "science/reviews/overnight-controls/results/B_features.csv (F2)" },
      { fact: "Dot near the marker, first moment about (132.3, 125.8) display px, lies within about 1 arcsec of Gaia DR3 5756956644387831296.", source: "science/reviews/transfer-exercise/answer_evidence.json" },
    ],
    answer_evidence_ids: aeIds,
    author_text_vs_computed: "Everything in initial_card/revised_card claim, observations and uncertainty is learner text (here illustrative). Frame fields (dates, wavelengths, quality, sha256, display_scale_mode) are copied from the API FrameRecord by frameToEvidence. The reference answer lives only in case.json conclusion_guide and must not be written into the learner's card.",
  },
};

writeFileSync(path.join(HERE, "evidence_card.wise_0855_quality_trap.illustrative.json"), JSON.stringify(fixture, null, 1) + "\n");
const failed = checks.filter((c) => !c.ok);
writeFileSync(
  path.join(HERE, "case_evidence_check.json"),
  JSON.stringify({ generated_by: "qa/ui-fixtures/make_case_evidence_fixture.mjs", data_root_checked: Boolean(dataRoot), passed: checks.length - failed.length, failed: failed.length, checks }, null, 1) + "\n",
);
console.log(`${checks.length - failed.length}/${checks.length} checks passed${dataRoot ? " (raw cutouts checked)" : ""}`);
for (const f of failed) console.log("FAIL", f.name, JSON.stringify(f.detail));
process.exit(failed.length ? 1 : 0);
