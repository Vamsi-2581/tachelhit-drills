// Media helpers shared by the creator, editor and player.
//
// iOS (Safari / WKWebView) records audio as audio/mp4 (AAC) and video as
// video/mp4; Chrome records webm. The backend validates by file extension, so
// the name we give a Blob must follow its real MIME type, never a hard-coded
// ".webm" / ".m4a".

export type MediaKind = 'audio' | 'video' | 'image';

const EXT_BY_MIME: Record<string, string> = {
  'audio/mp4': 'm4a',
  'audio/x-m4a': 'm4a',
  'audio/aac': 'aac',
  'audio/mpeg': 'mp3',
  'audio/mp3': 'mp3',
  'audio/wav': 'wav',
  'audio/x-wav': 'wav',
  'audio/ogg': 'ogg',
  'audio/webm': 'webm',
  'video/mp4': 'mp4',
  'video/quicktime': 'mov',
  'video/webm': 'webm',
  'video/x-m4v': 'm4v',
  'image/jpeg': 'jpg',
  'image/png': 'png',
  'image/gif': 'gif',
  'image/webp': 'webp',
  'image/heic': 'heic',
  'image/heif': 'heif',
};

const DEFAULT_EXT: Record<MediaKind, string> = { audio: 'm4a', video: 'mp4', image: 'jpg' };

/** Strip codec parameters: "audio/webm;codecs=opus" -> "audio/webm". */
export function baseMime(type: string | undefined | null): string {
  return (type || '').split(';')[0].trim().toLowerCase();
}

/** File extension (without dot) for a Blob/File, derived from its MIME type. */
export function extensionFor(blob: Blob, kind: MediaKind): string {
  const mime = baseMime(blob.type);
  if (EXT_BY_MIME[mime]) return EXT_BY_MIME[mime];
  // A File picked from the gallery may carry a useful name even when the
  // browser reports an empty/odd MIME type.
  const name = (blob as File).name;
  const m = name && /\.([a-z0-9]{2,5})$/i.exec(name);
  if (m) return m[1].toLowerCase();
  return DEFAULT_EXT[kind];
}

/** Media kind from a Blob's MIME type (falls back to `fallback`). */
export function kindOf(blob: Blob, fallback: MediaKind = 'audio'): MediaKind {
  const mime = baseMime(blob.type);
  if (mime.startsWith('image/')) return 'image';
  if (mime.startsWith('video/')) return 'video';
  if (mime.startsWith('audio/')) return 'audio';
  return fallback;
}

/** A filename whose extension matches the blob's real type. */
export function fileNameFor(blob: Blob, kind: MediaKind, prefix?: string): string {
  return `${prefix || kind}_${Date.now()}.${extensionFor(blob, kind)}`;
}

/** MIME type for a filename (used when re-reading queued uploads from disk). */
export function mimeForFileName(fileName: string): string {
  const ext = (/\.([a-z0-9]{2,5})$/i.exec(fileName)?.[1] || '').toLowerCase();
  for (const [mime, e] of Object.entries(EXT_BY_MIME)) if (e === ext) return mime;
  return 'application/octet-stream';
}

/** Pick the MediaRecorder MIME type the current browser can actually produce. */
export function preferredRecorderMime(kind: 'audio' | 'video'): string | undefined {
  if (typeof MediaRecorder === 'undefined') return undefined;
  const candidates = kind === 'audio'
    ? ['audio/mp4', 'audio/webm;codecs=opus', 'audio/webm', 'audio/ogg']
    : ['video/mp4', 'video/webm;codecs=vp9', 'video/webm'];
  return candidates.find((c) => MediaRecorder.isTypeSupported(c));
}

/**
 * Safari/AVPlayer cannot play WebM. Recordings made by Chrome on the web were
 * stored as .webm on Cloudinary; asking Cloudinary for the same asset with an
 * .m4a extension transcodes it on the fly (Cloudinary "video" resource type).
 */
export function toPlayableAudioUrl(url: string): string {
  if (!url) return url;
  if (/res\.cloudinary\.com\/.+\/video\/upload\/.+\.webm(\?.*)?$/i.test(url)) {
    return url.replace(/\.webm(\?.*)?$/i, '.m4a$1');
  }
  return url;
}
