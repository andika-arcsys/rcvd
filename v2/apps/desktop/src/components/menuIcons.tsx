import type { MenuId } from '../navigation/registry';

const PATH: Record<MenuId, string> = {
  dashboard: 'M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z',
  misi: 'M12 21s7-6.2 7-11a7 7 0 1 0-14 0c0 4.8 7 11 7 11zM12 10.5h.01',
  kalibrasi_kamera: 'M4 8h3.2L8.6 5.5h6.8L16.8 8H20v11H4zM12 10.2a3.2 3.2 0 1 0 .01 0z',
  live_operation: 'M4 7h11v10H4zM15 10.5l5-2.5v8l-5-2.5z',
  review: 'M9 11.5l2.2 2.2L20 6M4 7h4M4 12h4M4 17h11',
  gallery: 'M4 5h16v14H4zM4 15l4.2-4 3 3 2.6-2.6L20 16',
  laporan: 'M7 3h7l5 5v13H7zM14 3v5h5M10 12h6M10 16h4',
  pims_rbi: 'M12 3l8 3.5v6.2c0 4.6-3.2 7.4-8 8.3-4.8-.9-8-3.7-8-8.3V6.5z',
  analisis_ai:
    'M12 3v3M12 18v3M4.8 4.8l2.1 2.1M17.1 17.1l2.1 2.1M3 12h3M18 12h3M4.8 19.2l2.1-2.1M17.1 6.9l2.1-2.1M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z',
  sustainability: 'M12 21c4-2.8 6.5-6 6.5-9.2A6.5 6.5 0 0 0 5.5 11.8C5.5 15 8 18.2 12 21z',
  arsip: 'M4 8h16v12H4zM3 8l2.2-3h13.6L21 8M9 12h6',
  pengaturan:
    'M12 15.2a3.2 3.2 0 1 0 0-6.4 3.2 3.2 0 0 0 0 6.4zM12 3.2v2.2M12 18.6V21M4.7 4.7l1.6 1.6M17.7 17.7l1.6 1.6M3.2 12h2.2M18.6 12H21M4.7 19.3l1.6-1.6M17.7 6.3l1.6-1.6',
  keluar: 'M10 7V4h10v16H10v-3M4 12h11M12 9l3 3-3 3',
};

export function MenuIcon({ id }: { id: MenuId }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className="h-5 w-5 shrink-0"
      aria-hidden="true"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d={PATH[id]} />
    </svg>
  );
}

export function PanelIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      className="h-5 w-5 shrink-0"
      aria-hidden="true"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M4 5h16v14H4zM9 5v14" />
    </svg>
  );
}
