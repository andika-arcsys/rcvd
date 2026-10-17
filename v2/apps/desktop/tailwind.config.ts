import type { Config } from 'tailwindcss';

// Warna mengikuti mockup dan bahasa warna SPEC (oranye aksi, hijau lolos, kuning perhatian,
// merah kritis, biru informasi). Warna tidak pernah menjadi satu-satunya penanda.
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0B131B',
        panel: '#101B25',
        line: '#22313F',
        ink: '#E6EDF3',
        muted: '#93A4B5',
        active: '#1C2C3B',
        action: '#F28C28',
        ok: '#3FB97C',
        warn: '#E5B33A',
        danger: '#E5534B',
        info: '#4EA8DE',
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
} satisfies Config;
