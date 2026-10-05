import type { CSSProperties } from 'react';

const paths = {
  arrow: 'M5 12h14M13 6l6 6-6 6',
  compare: 'M8 3v18M16 3v18M4 8h8M12 16h8',
  clock: 'M12 8v4l3 2M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0',
  chevron: 'm9 5 7 7-7 7',
  code: 'm8 7-5 5 5 5m8-10 5 5-5 5m-3-12-2 14',
  info: 'M12 11v6M12 7h.01M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0',
  close: 'm6 6 12 12M6 18 18 6',
  check: 'm5 12 4 4L19 6',
  copy: 'M9 8h11v13H9zM15 8V3H4v13h5',
  plus: 'M12 5v14M5 12h14',
  activity: 'M3 12h4l3-8 4 16 3-8h4',
} as const;

export function Icon({ name, size = 18, style }: { name: keyof typeof paths; size?: number; style?: CSSProperties }) {
  return <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={style}><path d={paths[name]} /></svg>;
}
