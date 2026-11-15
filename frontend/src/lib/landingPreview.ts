import type { CaseContent, FrameRecord } from "../api/types";

/** Match the investigation's unsaved initial pair by authored refs, never array order. */
export function landingPreview(frames: FrameRecord[], caseContent: CaseContent | null) {
  if (!caseContent) return [frames[0], frames[frames.length - 1]] as const;
  const firstRef = caseContent.frames[0]?.ref;
  const required = caseContent.evidence_requirements?.must_include_refs_any_of?.[0];
  const otherRef = required?.find(ref => ref !== firstRef) ?? caseContent.frames[1]?.ref;
  const byRef = (ref: string | undefined) => {
    const key = caseContent.frames.find(frame => frame.ref === ref)?.frame_key;
    return frames.find(frame => frame.frame_key === key);
  };
  return [byRef(firstRef), byRef(otherRef)] as const;
}
