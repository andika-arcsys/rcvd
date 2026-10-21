import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { MENU_ITEMS, SCREENS, START_PATH, screenByCode, screenByPath } from './registry';
import { TRANSITIONS, entriesTo, exitsFrom } from './transitions';

const V2_ROOT = resolve(__dirname, '../../../..');

describe('registry layar', () => {
  it('memuat 25 layar dengan kode dan path unik', () => {
    expect(SCREENS).toHaveLength(25);
    expect(new Set(SCREENS.map((s) => s.code)).size).toBe(25);
    expect(new Set(SCREENS.map((s) => s.path)).size).toBe(25);
  });

  it('setiap layar punya berkas mockup dan folder layar', () => {
    for (const screen of SCREENS) {
      expect(
        existsSync(resolve(V2_ROOT, 'mockups', `${screen.mockup}.dc.html`)),
        screen.mockup,
      ).toBe(true);
    }
  });

  it('layar tanpa sidebar sesuai SPEC', () => {
    const noSidebar = SCREENS.filter((s) => s.menu === null).map((s) => s.code);
    expect(noSidebar.sort()).toEqual(['0', '0.1', '0.2', '12', '3.0', '3.5.3', '3.9'].sort());
  });

  it('memuat 13 menu sidebar yang cocok dengan config/roles.yaml', () => {
    expect(MENU_ITEMS).toHaveLength(13);
    const yaml = readFileSync(resolve(V2_ROOT, 'config/roles.yaml'), 'utf-8');
    for (const item of MENU_ITEMS) expect(yaml).toContain(`  ${item.id}:`);
  });

  it('Canvas dan Mode Snapshot menyorot Live Operation; Kalkulator span menyorot Gallery', () => {
    expect(screenByCode('3.4').menu).toBe('live_operation');
    expect(screenByCode('3.5').menu).toBe('live_operation');
    expect(screenByCode('5.2').menu).toBe('gallery');
    expect(screenByPath('/review')?.back?.to).toBe('history');
  });
});

describe('transisi layar', () => {
  it('setiap transisi menunjuk layar yang ada dan berlabel', () => {
    for (const tr of TRANSITIONS) {
      expect(() => screenByCode(tr.from)).not.toThrow();
      expect(() => screenByCode(tr.to)).not.toThrow();
      expect(tr.label.trim()).not.toBe('');
    }
  });

  it('semua 25 layar dapat dicapai dari Splash lewat transisi dan sidebar', () => {
    const start = SCREENS.find((s) => s.path === START_PATH)?.code ?? '0';
    const menuTargets = MENU_ITEMS.map((m) => SCREENS.find((s) => s.path === m.path)?.code ?? '');
    const seen = new Set([start]);
    const queue = [start];
    while (queue.length > 0) {
      const code = queue.shift() as string;
      const next = exitsFrom(code).map((tr) => tr.to);
      if (screenByCode(code).menu !== null) next.push(...menuTargets);
      for (const target of next) {
        if (!seen.has(target)) {
          seen.add(target);
          queue.push(target);
        }
      }
    }
    expect([...seen].sort()).toEqual(SCREENS.map((s) => s.code).sort());
  });

  it('keputusan KONFLIK-N4 dan N5 diterapkan', () => {
    expect(
      exitsFrom('12')
        .map((tr) => tr.to)
        .sort(),
    ).toEqual(['0.1', '10']);
    expect(exitsFrom('5.2').find((tr) => tr.to === '3')?.label).toContain('FREEZE');
    expect(exitsFrom('5.2').some((tr) => tr.to === '3.5' && tr.label.includes('Ukur ulang'))).toBe(
      false,
    );
  });

  it('FREEZE hanya dari Optical, AquaClear, HydroDetect, dan SpatialSight', () => {
    const sources = TRANSITIONS.filter((tr) => tr.to === '3.5' && /FREEZE/i.test(tr.label)).map(
      (tr) => tr.from,
    );
    expect(sources.sort()).toEqual(['3', '3.1', '3.2', '3.3'].sort());
  });

  it('Simpan snapshot dapat dimasuki dari Mode Snapshot dan Canvas', () => {
    expect(
      entriesTo('3.5.3')
        .map((tr) => tr.from)
        .sort(),
    ).toEqual(['3.4', '3.5']);
  });
});
