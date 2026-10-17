import { Link } from 'react-router-dom';
import { t } from '../../i18n';
import { useSession } from '../../session/SessionContext';

/** Stub sampai Fase 7. Menampilkan frame yang dibekukan; pengukuran belum dihitung di sini. */
export default function SnapshotScreen() {
  const { frozen } = useSession();
  return (
    <section className="p-6">
      <p className="text-sm text-muted">{frozen ? t('live.snapshotWait') : t('live.noFreeze')}</p>
      <p className="mt-3 font-mono">
        {t('live.frame')} {frozen?.frameId ?? t('common.dash')}
      </p>
      <Link to="/live" className="mt-4 inline-block text-sm text-info">
        {t('live.resume')}
      </Link>
    </section>
  );
}
