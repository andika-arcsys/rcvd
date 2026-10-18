import type { FormEvent } from 'react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useEngine } from '../../engine/EngineProvider';
import { engineError } from '../../lib/engineError';
import { screenTitle, t } from '../../i18n';
import { useSession } from '../../session/SessionContext';

const FIELD = 'rounded border border-line bg-bg px-3 py-2 text-sm text-ink';

function LoginFields({
  userId,
  pin,
  setUserId,
  setPin,
}: {
  userId: string;
  pin: string;
  setUserId: (value: string) => void;
  setPin: (value: string) => void;
}) {
  return (
    <>
      <label className="flex flex-col gap-1 text-xs text-muted">
        {t('login.userId')}
        <input
          className={FIELD}
          value={userId}
          autoComplete="username"
          onChange={(event) => setUserId(event.target.value)}
        />
      </label>
      <label className="flex flex-col gap-1 text-xs text-muted">
        {t('login.pin')}
        <input
          className={`${FIELD} font-mono`}
          type="password"
          inputMode="numeric"
          maxLength={6}
          autoComplete="off"
          value={pin}
          onChange={(event) => setPin(event.target.value)}
        />
      </label>
    </>
  );
}

export default function LoginScreen() {
  const { client } = useEngine();
  const { setUser } = useSession();
  const navigate = useNavigate();
  const [userId, setUserId] = useState('');
  const [pin, setPin] = useState('');
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const result = await client.POST('/auth/login', { body: { user_id: userId, pin } });
    const failure = engineError(result.error);
    if (failure || !result.data) {
      setError(failure?.message ?? t('login.invalid'));
      setPin('');
      return;
    }
    setUser({ userId: result.data.user_id, name: result.data.name, roles: result.data.roles });
    navigate('/peran');
  };

  return (
    <main className="flex h-full items-center justify-center p-6">
      <form
        onSubmit={(event) => void submit(event)}
        className="flex w-full max-w-md flex-col gap-4 rounded-xl border border-line bg-panel p-7"
      >
        <h1 className="text-2xl font-semibold">{screenTitle('0.1')}</h1>
        <p className="text-sm text-muted">{t('login.hint')}</p>
        <button
          type="button"
          disabled
          className="rounded-lg bg-ink px-4 py-3 font-semibold text-bg opacity-40"
        >
          {t('login.sso')} · {t('login.soon')}
        </button>
        <p className="text-center text-xs text-muted">{t('login.orPin')}</p>
        <LoginFields userId={userId} pin={pin} setUserId={setUserId} setPin={setPin} />
        {error && (
          <p role="alert" className="text-sm text-danger">
            {error}
          </p>
        )}
        <button type="submit" className="rounded-lg bg-action px-4 py-3 font-semibold text-bg">
          {t('login.submit')}
        </button>
        <p className="text-xs text-muted">{t('login.lockNote')}</p>
      </form>
    </main>
  );
}
