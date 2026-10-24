import { Link } from 'react-router-dom';
import type { components } from '@deepinsight/shared';
import { t } from '../../i18n';

type MissionView = components['schemas']['MissionView'];

function actionFor(status: string): { to: string; label: string } {
  if (status === 'Berjalan') return { to: '/live', label: t('dashboard.resume') };
  if (status === 'Direncanakan') return { to: '/misi', label: t('dashboard.open') };
  return { to: '/laporan', label: t('dashboard.report') };
}

const SHOWN = 5;

export function MissionTable({ missions }: { missions: MissionView[] }) {
  if (missions.length === 0) return <p className="text-sm text-muted">{t('dashboard.empty')}</p>;
  return (
    <>
      <table className="mt-1 w-full text-left text-sm">
        <thead className="text-muted">
          <tr>
            <th className="px-2 py-1 font-medium">{t('dashboard.colMission')}</th>
            <th className="px-2 py-1 font-medium">{t('dashboard.colPipe')}</th>
            <th className="px-2 py-1 font-medium">{t('dashboard.colDate')}</th>
            <th className="px-2 py-1 font-medium">{t('dashboard.colStatus')}</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {missions.slice(0, SHOWN).map((mission) => {
            const action = actionFor(mission.status);
            return (
              <tr key={mission.id} className="border-t border-line">
                <td className="px-2 py-1">{mission.name}</td>
                <td className="px-2 py-1">{mission.diameter}</td>
                <td className="px-2 py-1">{mission.survey_date}</td>
                <td className="px-2 py-1">{mission.status}</td>
                <td className="px-2 py-1">
                  <Link to={action.to} className="text-info">
                    {action.label}
                  </Link>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {missions.length > SHOWN && (
        <Link to="/arsip" className="text-xs text-info">
          {t('dashboard.moreMissions')}
        </Link>
      )}
    </>
  );
}
