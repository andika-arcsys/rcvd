import { useNavigate } from 'react-router-dom';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { t } from '../../i18n';
const ACTION = 'rounded px-4 py-2 text-sm disabled:bg-line disabled:text-muted';

export function ActionBar({
  lost,
  note,
  confirmEnd,
  onFreeze,
  onSnapshot,
  onMark,
  setConfirmEnd,
}: {
  lost: boolean;
  note: string | null;
  confirmEnd: boolean;
  onFreeze: () => void;
  onSnapshot?: () => void;
  onMark: () => void;
  setConfirmEnd: (open: boolean) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <ShotButtons lost={lost} onFreeze={onFreeze} onSnapshot={onSnapshot} onMark={onMark} />
      <button
        type="button"
        onClick={() => setConfirmEnd(true)}
        className={`${ACTION} ml-auto border border-danger text-danger`}
      >
        {t('live.end')}
      </button>
      {note && <p className="text-sm text-ok">{note}</p>}
      {confirmEnd && <EndDialog onClose={() => setConfirmEnd(false)} />}
    </div>
  );
}

function ShotButtons({
  lost,
  onFreeze,
  onSnapshot,
  onMark,
}: {
  lost: boolean;
  onFreeze: () => void;
  onSnapshot?: () => void;
  onMark: () => void;
}) {
  return (
    <>
      <button
        type="button"
        disabled={lost}
        onClick={onFreeze}
        className={`${ACTION} bg-action text-bg`}
      >
        {t('live.freeze')}
      </button>
      {onSnapshot ? (
        <button
          type="button"
          disabled={lost}
          onClick={onSnapshot}
          className={`${ACTION} bg-action text-bg`}
        >
          {t('live.snapshot')}
        </button>
      ) : null}
      <button
        type="button"
        disabled={lost}
        onClick={onMark}
        className={`${ACTION} border border-line`}
      >
        {t('live.mark')}
      </button>
    </>
  );
}

function EndDialog({ onClose }: { onClose: () => void }) {
  const navigate = useNavigate();
  return (
    <ConfirmDialog
      title={t('live.endTitle')}
      actions={[
        { label: t('common.cancel'), onSelect: onClose },
        {
          label: t('live.confirmEnd'),
          tone: 'danger',
          onSelect: () => {
            onClose();
            navigate('/penutupan');
          },
        },
      ]}
    >
      {t('live.endBody')}
    </ConfirmDialog>
  );
}
