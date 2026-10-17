import { useNavigate } from 'react-router-dom';
import { t } from '../i18n';
import { useSession } from '../session/SessionContext';
import { ConfirmDialog, type ConfirmAction } from './ConfirmDialog';

/** Keluar biasa, atau Simpan / Buang / Batal bila ada frame beku atau ukuran belum disimpan. */
export function ExitPrompt({ held, onClose }: { held: boolean; onClose: () => void }) {
  const navigate = useNavigate();
  const { setFrozen, setUnsavedMeasure } = useSession();
  const actions = held
    ? holdActions(onClose, navigate, setFrozen, setUnsavedMeasure)
    : plainActions(onClose, navigate);
  return (
    <ConfirmDialog title={t('common.exitTitle')} actions={actions}>
      {held ? t('common.exitHoldBody') : t('common.exitBody')}
    </ConfirmDialog>
  );
}

function plainActions(onClose: () => void, navigate: (path: string) => void): ConfirmAction[] {
  return [
    { label: t('common.cancel'), onSelect: onClose },
    {
      label: t('common.exit'),
      tone: 'danger',
      onSelect: () => {
        onClose();
        navigate('/penutupan');
      },
    },
  ];
}

function holdActions(
  onClose: () => void,
  navigate: (path: string) => void,
  setFrozen: (value: null) => void,
  setUnsavedMeasure: (value: boolean) => void,
): ConfirmAction[] {
  return [
    {
      label: t('common.saveExit'),
      tone: 'primary',
      onSelect: () => {
        onClose();
        navigate('/live/snapshot');
      },
    },
    {
      label: t('common.discard'),
      tone: 'danger',
      onSelect: () => {
        setFrozen(null);
        setUnsavedMeasure(false);
        onClose();
        navigate('/penutupan');
      },
    },
    { label: t('common.cancel'), onSelect: onClose },
  ];
}
