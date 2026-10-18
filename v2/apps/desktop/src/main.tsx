import React from 'react';
import ReactDOM from 'react-dom/client';
import { HashRouter } from 'react-router-dom';
import { AppRoutes } from './App';
import { EngineProvider } from './engine/EngineProvider';
import { SessionProvider } from './session/SessionContext';
import './styles.css';

const root = document.getElementById('root');
if (!root) throw new Error('Elemen #root tidak ditemukan');

ReactDOM.createRoot(root).render(
  <React.StrictMode>
    <EngineProvider>
      <SessionProvider>
        <HashRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <AppRoutes />
        </HashRouter>
      </SessionProvider>
    </EngineProvider>
  </React.StrictMode>,
);
