import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { jsonResponse, renderApp } from '../../test/renderApp';

describe('Login', () => {
  it('SSO nonaktif dan PIN salah menampilkan pesan yang sama', async () => {
    renderApp('/login', {
      routes: {
        'POST /auth/login': () =>
          Promise.resolve(
            jsonResponse(401, { code: 'AUTH-001', message: 'Pengguna atau PIN tidak valid.' }),
          ),
      },
    });
    expect(screen.getByRole('button', { name: /Masuk dengan SSO/ })).toBeDisabled();
    expect(screen.getByRole('button', { name: /Segera/ })).toBeDisabled();
    await userEvent.type(screen.getByLabelText('ID pengguna'), 'tidak-ada');
    await userEvent.type(screen.getByLabelText('PIN (6 digit)'), '000000');
    await userEvent.click(screen.getByRole('button', { name: 'Masuk' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Pengguna atau PIN tidak valid.');
    expect(screen.getByLabelText('PIN (6 digit)')).toHaveValue('');
  });

  it('mengunci setelah batas percobaan', async () => {
    let tries = 0;
    renderApp('/login', {
      routes: {
        'POST /auth/login': () => {
          tries += 1;
          const locked = tries >= 5;
          return Promise.resolve(
            jsonResponse(locked ? 423 : 401, {
              code: locked ? 'AUTH-002' : 'AUTH-001',
              message: locked ? 'Akun terkunci sementara.' : 'Pengguna atau PIN tidak valid.',
            }),
          );
        },
      },
    });
    const user = userEvent.setup();
    await user.type(screen.getByLabelText('ID pengguna'), 'uji');
    for (let i = 0; i < 5; i += 1) {
      await user.type(screen.getByLabelText('PIN (6 digit)'), '000000');
      await user.click(screen.getByRole('button', { name: 'Masuk' }));
    }
    expect(await screen.findByRole('alert')).toHaveTextContent('Akun terkunci sementara.');
  });

  it('masuk yang sah membuka pilih peran', async () => {
    renderApp('/login', {
      routes: {
        'POST /auth/login': {
          user_id: 'uji',
          name: 'Akun uji',
          roles: ['ahli_ukur'],
        },
        'GET /cameras': [],
      },
    });
    await userEvent.type(screen.getByLabelText('ID pengguna'), 'uji');
    await userEvent.type(screen.getByLabelText('PIN (6 digit)'), '135790');
    await userEvent.click(screen.getByRole('button', { name: 'Masuk' }));
    expect(await screen.findByText(/Akun uji/)).toBeInTheDocument();
  });
});
