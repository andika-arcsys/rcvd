import { describe, expect, it } from 'vitest';
import { SCREENS, MENU_ITEMS } from '../navigation/registry';
import { screenTitle, t } from './index';

describe('i18n', () => {
  it('semua layar dan menu punya teks', () => {
    for (const screen of SCREENS) expect(screenTitle(screen.code)).not.toBe(screen.code);
    for (const menu of MENU_ITEMS) expect(t(`menu.${menu.id}`)).not.toBe(`menu.${menu.id}`);
  });

  it('kunci yang tidak ada dikembalikan apa adanya', () => {
    expect(t('tidak.ada')).toBe('tidak.ada');
  });
});
