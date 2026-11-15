import { readFileSync } from "node:fs";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { normalizeFrameRecord } from "../src/api/client";
import type { CaseContent } from "../src/api/types";
import { Notebook } from "../src/components/Notebook";
import { Plate } from "../src/components/Plate";
import { attachPair, createEvidenceCard, emptyStore, normalizeEvidenceCard, resolveDraft, serializeEvidenceCard, upsertCard } from "../src/evidence/card";
import { completionIssues, reviewStep } from "../src/evidence/completion";
import { presetContextKey, reopenTarget } from "../src/evidence/reopen";
import { parseRoute, routeToSearch } from "../src/lib/route";

const content = JSON.parse(readFileSync(new URL("../../backend/content/cases/wise_0855_quality_trap.json", import.meta.url), "utf8")) as CaseContent;
const frames = content.frames.map((ref) => ({ ref: ref.ref, frame: normalizeFrameRecord(JSON.parse(readFileSync(
  new URL(`../../backend/content/presets/wise_0855/case-wise_0855_quality_trap/${ref.frame_key}.json`, import.meta.url), "utf8"))) }));
const draft = () => attachPair(createEvidenceCard({ case_id: content.case_id, preset_id: "wise_0855", app_version: "test", data_origin: "api" }), frames.slice(0, 2), ["A", "B", "C"]);
const complete = () => ({ ...content.steps.reduce((c, s) => reviewStep(c, s.id, true), draft()), claim: "My own claim", observations: "The overlay covers the moving dot.", uncertainty: "The physical cause is unknown." });

describe("third investigation release", () => {
  it("ships A/B on identical shared scales, C on its own scale, and all flag overlays", () => {
    const [a, b, c] = frames.map((f) => f.frame);
    expect(a.display_scale).toEqual(b.display_scale);
    expect(a.display_scale?.mode).toBe("shared");
    expect(c.display_scale?.mode).toBe("per_frame");
    expect(frames.every(({ frame }) => frame.flag_image && frame.marker?.kind === "catalog_prediction")).toBe(true);
    expect(content.display_requirements?.reference_line).toBeUndefined();
    const html = renderToStaticMarkup(createElement(Plate, { frame: c, heading: "C", letter: "C", showMarker: true }));
    expect(html).toContain("Brightness not directly comparable");
  });

  it("does not call a loaded image, auto draft, or reference click completion", () => {
    expect(completionIssues({ ...draft(), reference_shown: true }, content, true)).not.toEqual([]);
    expect(completionIssues(complete(), content, false)).toContain("Save this card on your device.");
    expect(completionIssues(reviewStep(complete(), content.steps[0].id, false), content, true)).not.toEqual([]);
    expect(completionIssues({ ...complete(), uncertainty: " " }, content, true)).toContain("Record what remains uncertain.");
    const wrongPair = attachPair(complete(), [frames[0], frames[2]], ["A", "B", "C"]);
    expect(completionIssues(wrongPair, content, true)).toContain("Include frames A and B.");
    expect(completionIssues(complete(), content, true)).toEqual([]);
  });

  it("hides the reference until a saved, completed claim requests it, and keeps learner text", () => {
    const render = (card = complete(), saved = true) => renderToStaticMarkup(createElement(Notebook, {
      card, caseContent: content, saveState: saved ? { kind: "saved", at: "now" } : { kind: "saving" }, onChange: () => {}, onRemoveFrame: () => {},
    }));
    expect(render()).not.toContain("Reference answer (from the case)");
    expect(render(complete(), false)).not.toContain("Reference answer (from the case)");
    expect(render({ ...complete(), reference_shown: true }, false)).toContain("Reference answer (from the case)");
    const card = { ...complete(), reference_shown: true };
    const html = render(card);
    expect(html).toContain("Reference answer (from the case)");
    expect(html).toContain("Your claim");
    expect(html).toContain("My own claim");
    expect(JSON.parse(serializeEvidenceCard(card)).claim).toBe("My own claim");
    expect(normalizeEvidenceCard({ ...card, reviewed_step_ids: undefined, reference_shown: undefined }).reviewed_step_ids).toEqual([]);
  });

  it("keeps an older free-exploration card separate and reopens both with their own notes", () => {
    const free = { ...createEvidenceCard({ preset_id: "wise_0855", app_version: "test", data_origin: "api" }), claim: "Old free exploration" };
    const guided = complete();
    const freeKey = presetContextKey("api", "wise_0855");
    const guidedKey = presetContextKey("api", "wise_0855", content.case_id);
    expect(freeKey).not.toBe(guidedKey);
    const store = upsertCard(upsertCard(emptyStore(), freeKey, free), guidedKey, guided);
    for (const [card, key] of [[free, freeKey], [guided, guidedKey]] as const) {
      const target = reopenTarget(card, key)!;
      expect(target.contextKey).toBe(key);
      expect(parseRoute(routeToSearch(target.route, false))).toEqual(target.route);
      expect(resolveDraft(key, store, new Map())?.card.claim).toBe(card.claim);
    }
    expect(reopenTarget(free, freeKey)?.route).toMatchObject({ caseId: "none" });
  });
});
