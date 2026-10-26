import React from 'react';
import { createRoot } from 'react-dom/client';
import StructureApp from './StructureApp';

const container = document.getElementById('root');
if (container) {
  createRoot(container).render(
    <React.StrictMode>
      <StructureApp />
    </React.StrictMode>
  );
}
