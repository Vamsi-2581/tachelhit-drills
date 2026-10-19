import type { Drill } from '../types';

export type DraftVerdict = 'yes' | 'roughly' | 'no' | 'unchecked';

/** The current draft's verdict from the server-side meaning check (draft_check.py).
 *  A verdict only counts for the draft it was computed on; if the draft changed, it is
 *  'unchecked' again. */
export function draftVerdict(d?: Pick<Drill, 'draft_check' | 'text_tachelhit_suggested'> | null): DraftVerdict {
  const draft = (d?.text_tachelhit_suggested || '').trim();
  if (!d?.draft_check || !draft) return 'unchecked';
  try {
    const rec = JSON.parse(d.draft_check) as { draft?: string; verdict?: string };
    const clean = draft.replace('[?', ' ').replace(/[[\]]/g, ' ').split('|')[0].split(' · ')[0].replace(/\s+/g, ' ').trim();
    if (rec.draft !== clean) return 'unchecked';
    return rec.verdict === 'yes' || rec.verdict === 'roughly' || rec.verdict === 'no' ? rec.verdict : 'unchecked';
  } catch {
    return 'unchecked';
  }
}

/** A draft a learner may be shown: anything but a draft the meaning check rejected. */
export function draftUsable(d?: Pick<Drill, 'draft_check' | 'text_tachelhit_suggested'> | null): boolean {
  return draftVerdict(d) !== 'no';
}

export const DRAFT_REJECTED_LABEL = 'lectura automàtica descartada · cal un parlant';
