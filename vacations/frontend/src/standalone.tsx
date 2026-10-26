import React from 'react';
import { createRoot } from 'react-dom/client';
import VacationsApp from './VacationsApp';

const container = document.getElementById('root');
if (container) {
  createRoot(container).render(
    <React.StrictMode>
      <VacationsApp />
    </React.StrictMode>
  );
}
