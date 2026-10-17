import { useEffect, useState } from 'react';

/**
 * Mobile layout decision shared by the drill list, grid and dashboards.
 *
 * Width alone misses iPads (768-1366 px) and a user-agent test misses them
 * too: iPadOS reports a Mac UA. A coarse-pointer touch device below a
 * laptop-ish width gets the touch layout; everything else gets the desktop
 * layout (AG Grid, hover affordances, double-click editing).
 */
export function isMobileLayout(): boolean {
  const w = window.innerWidth;
  if (w < 768) return true;
  const touch = (navigator.maxTouchPoints || 0) > 1 || window.matchMedia?.('(pointer: coarse)').matches;
  return touch && w < 1200;
}

export function useIsMobileLayout(): boolean {
  const [isMobile, setIsMobile] = useState(isMobileLayout);
  useEffect(() => {
    const onResize = () => setIsMobile(isMobileLayout());
    window.addEventListener('resize', onResize);
    window.addEventListener('orientationchange', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
      window.removeEventListener('orientationchange', onResize);
    };
  }, []);
  return isMobile;
}
