import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import App from './App.jsx';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
      <Toaster
        position="top-right"
        reverseOrder={false}
        gutter={8}
        containerClassName=""
        containerStyle={{}}
        toastOptions={{
          duration: 4000,
          style: {
            background: '#1A1A2E',
            color: '#E2E8F0',
            border: '1px solid rgba(108, 99, 255, 0.3)',
            borderRadius: '12px',
            backdropFilter: 'blur(20px)',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.37)',
          },
          success: {
            iconTheme: {
              primary: '#43D9AD',
              secondary: '#1A1A2E',
            },
          },
          error: {
            iconTheme: {
              primary: '#FF6584',
              secondary: '#1A1A2E',
            },
          },
        }}
      />
    </BrowserRouter>
  </React.StrictMode>
);
