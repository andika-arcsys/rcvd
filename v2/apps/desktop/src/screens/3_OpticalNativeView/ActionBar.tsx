import { useNavigate } from 'react-router-dom';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { t } from '../../i18n';

const ACTION = 'rounded px-4 py-2 text-sm disabled:bg-line disabled:text-muted';

export function ActionBar({
  lost,
  dual,
  held,
  note,
  confirmEnd,
  onFreeze,
  onSnapshot,
  setConfirmEnd,
}: {
  lost: boolean;
  dual: boolean;
  held: boolean;
  note: string | null;
  confirmEnd: boolean;
  onFreeze: () => void;
  onSnapshot: () => void;
  setConfirmEnd: (open: boolean) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <FreezeButton lost={lost} dual={dual} held={held} onFreeze={onFreeze} />
      <button
        type="button"
        disabled={lost}
        onClick={onSnapshot}
        className={`${ACTION} bg-action text-bg`}
      >
        {t('live.snapshot')}
      </button>
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

function FreezeButton({
  lost,
  dual,
  held,
  onFreeze,
}: {
  lost: boolean;
  dual: boolean;
  held: boolean;
  onFreeze: () => void;
}) {
  const latched = dual && held;
  return (
    <button
      type="button"
      disabled={lost || !dual}
      aria-pressed={latched}
      onClick={onFreeze}
      className={`${ACTION} ${latched ? 'bg-danger text-bg' : 'border border-line text-ink'}`}
    >
      {t('live.freeze')}
    </button>
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
