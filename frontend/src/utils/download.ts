import { Filesystem, Directory } from '@capacitor/filesystem';
import { Share } from '@capacitor/share';
import { isNativeApp } from '../config';

const blobToBase64 = (blob: Blob) =>
  new Promise<string>((resolve, reject) => {
    const r = new FileReader();
    r.onloadend = () => resolve((r.result as string).split(',')[1]);
    r.onerror = reject;
    r.readAsDataURL(blob);
  });

/**
 * Save a file for the user. In a browser this is a normal download; inside the
 * Capacitor shell `<a download>` and `window.open(blob:)` do nothing useful,
 * so the file is written to the app cache and handed to the native share
 * sheet (Save to Files / AirDrop / Photos…).
 */
export async function downloadOrShare(url: string, fileName: string, title = fileName): Promise<void> {
  if (!isNativeApp()) {
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    a.rel = 'noopener';
    document.body.appendChild(a);
    a.click();
    a.remove();
    return;
  }
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Descàrrega fallida (${res.status})`);
  const blob = await res.blob();
  const data = await blobToBase64(blob);
  const written = await Filesystem.writeFile({ path: `share/${fileName}`, data, directory: Directory.Cache, recursive: true });
  await Share.share({ title, url: written.uri });
}
