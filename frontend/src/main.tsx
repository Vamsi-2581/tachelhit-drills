// src/main.tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'
import { BrowserRouter } from 'react-router-dom';
import { restoreUserIdentity } from './config';

// AG Grid registration lives in src/agGridSetup.ts, imported only by the
// grid components so the library stays out of the entry bundle.

// Restore the identity from the native store before the first request fires.
restoreUserIdentity().finally(() => {
  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </React.StrictMode>,
  );
});