export const TEAM_ROLES = [
  'ketua_tim',
  'pilot_drone',
  'ahli_ukur',
  'pengelola_data',
  'teknisi_program',
  'pemeriksa_teknik',
] as const;

export type TeamRole = (typeof TEAM_ROLES)[number];

export function emptyTeam(): Record<TeamRole, string> {
  return {
    ketua_tim: '',
    pilot_drone: '',
    ahli_ukur: '',
    pengelola_data: '',
    teknisi_program: '',
    pemeriksa_teknik: '',
  };
}
