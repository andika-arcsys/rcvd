export type MenuId =
  | 'dashboard'
  | 'misi'
  | 'live_operation'
  | 'review'
  | 'gallery'
  | 'laporan'
  | 'pims_rbi'
  | 'analisis_ai'
  | 'sustainability'
  | 'arsip'
  | 'pengaturan'
  | 'keluar';

export interface MenuItem {
  id: MenuId;
  path: string;
}

/** 12 menu sidebar (SPEC: Sidebar global). */
export const MENU_ITEMS: readonly MenuItem[] = [
  { id: 'dashboard', path: '/dashboard' },
  { id: 'misi', path: '/misi' },
  { id: 'live_operation', path: '/live' },
  { id: 'review', path: '/review' },
  { id: 'gallery', path: '/gallery' },
  { id: 'laporan', path: '/laporan' },
  { id: 'pims_rbi', path: '/pims' },
  { id: 'analisis_ai', path: '/analisis-ai' },
  { id: 'sustainability', path: '/sustainability' },
  { id: 'arsip', path: '/arsip' },
  { id: 'pengaturan', path: '/pengaturan' },
  { id: 'keluar', path: '/penutupan' },
];

export type BackTarget = { label: string; to: string | 'history' };

export interface ScreenDef {
  /** Kode layar pada SPEC dan flow map, mis. "3.4". */
  code: string;
  path: string;
  /** Berkas mockup di folder mockups/. */
  mockup: string;
  /** Menu sidebar yang disorot; null = layar tanpa sidebar (pra-login, dialog, penutupan). */
  menu: MenuId | null;
  kind: 'screen' | 'dialog';
  back?: BackTarget;
}

export const SCREENS: readonly ScreenDef[] = [
  { code: '0', path: '/splash', mockup: 'Splash', menu: null, kind: 'screen' },
  { code: '0.1', path: '/login', mockup: 'Login', menu: null, kind: 'screen' },
  { code: '0.2', path: '/peran', mockup: 'Peran', menu: null, kind: 'screen' },
  { code: '1', path: '/dashboard', mockup: 'Dashboard', menu: 'dashboard', kind: 'screen' },
  { code: '2', path: '/misi', mockup: 'Misi', menu: 'misi', kind: 'screen' },
  { code: '3', path: '/live', mockup: 'Main', menu: 'live_operation', kind: 'screen' },
  { code: '3.0', path: '/live/ganti-window', mockup: 'GantiWindow', menu: null, kind: 'dialog' },
  {
    code: '3.1',
    path: '/live/aquaclear',
    mockup: 'AquaClear',
    menu: 'live_operation',
    kind: 'screen',
  },
  {
    code: '3.2',
    path: '/live/hydrodetect',
    mockup: 'HydroDetect',
    menu: 'live_operation',
    kind: 'screen',
  },
  {
    code: '3.3',
    path: '/live/spatialsight',
    mockup: 'SpatialSight',
    menu: 'live_operation',
    kind: 'screen',
  },
  { code: '3.9', path: '/live/performa', mockup: 'Performa', menu: null, kind: 'dialog' },
  {
    code: '3.4',
    path: '/live/canvas',
    mockup: 'CanvasAnotasi',
    menu: 'live_operation',
    kind: 'screen',
    back: { label: '← Optical', to: '/live' },
  },
  {
    code: '3.5',
    path: '/live/snapshot',
    mockup: 'Snapshot',
    menu: 'live_operation',
    kind: 'screen',
    back: { label: '← Optical', to: '/live' },
  },
  {
    code: '3.5.3',
    path: '/live/snapshot/simpan',
    mockup: 'SimpanSnapshot',
    menu: null,
    kind: 'dialog',
  },
  {
    code: '4',
    path: '/review',
    mockup: 'Review',
    menu: 'review',
    kind: 'screen',
    back: { label: '← Kembali', to: 'history' },
  },
  { code: '5', path: '/gallery', mockup: 'Gallery', menu: 'gallery', kind: 'screen' },
  {
    code: '5.2',
    path: '/gallery/span',
    mockup: 'Span',
    menu: 'gallery',
    kind: 'screen',
    back: { label: '← Gallery', to: '/gallery' },
  },
  { code: '6', path: '/laporan', mockup: 'Laporan', menu: 'laporan', kind: 'screen' },
  { code: '7', path: '/pims', mockup: 'Pims', menu: 'pims_rbi', kind: 'screen' },
  { code: '8', path: '/analisis-ai', mockup: 'AnalisisAI', menu: 'analisis_ai', kind: 'screen' },
  {
    code: '9',
    path: '/sustainability',
    mockup: 'Sustainability',
    menu: 'sustainability',
    kind: 'screen',
  },
  { code: '10', path: '/arsip', mockup: 'Arsip', menu: 'arsip', kind: 'screen' },
  { code: '11', path: '/pengaturan', mockup: 'Pengaturan', menu: 'pengaturan', kind: 'screen' },
  { code: '12', path: '/penutupan', mockup: 'Penutupan', menu: null, kind: 'screen' },
];

export const START_PATH = '/splash';
export const DASHBOARD_PATH = '/dashboard';

const BY_CODE = new Map(SCREENS.map((screen) => [screen.code, screen]));
const BY_PATH = new Map(SCREENS.map((screen) => [screen.path, screen]));

export function screenByCode(code: string): ScreenDef {
  const screen = BY_CODE.get(code);
  if (!screen) throw new Error(`Kode layar tidak dikenal: ${code}`);
  return screen;
}

export function screenByPath(path: string): ScreenDef | undefined {
  return BY_PATH.get(path);
}
