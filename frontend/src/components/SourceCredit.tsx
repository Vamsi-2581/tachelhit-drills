import { FaExternalLinkAlt } from 'react-icons/fa';
import { sourceCredit, sourceLink } from '../utils/media';
import type { Drill } from '../types';

/** Credit line for drills captured from an external source: author/channel, title,
 *  and a link to the original at the exact second. Renders nothing for own content. */
export default function SourceCredit({ drill, compact = false, style }: { drill: Partial<Drill>; compact?: boolean; style?: React.CSSProperties }) {
  const credit = sourceCredit(drill);
  const link = sourceLink(drill);
  if (!credit || !link) return null;
  return (
    <a href={link} target="_blank" rel="noopener noreferrer" title={`Font original: ${credit}`}
      onClick={(e) => e.stopPropagation()}
      style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', fontSize: compact ? '11px' : '12.5px', color: 'var(--text-muted)', textDecoration: 'none', maxWidth: '100%', ...style }}>
      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{compact ? '' : 'Font: '}{credit}</span>
      <FaExternalLinkAlt size={compact ? 9 : 10} style={{ flex: 'none' }} />
    </a>
  );
}
