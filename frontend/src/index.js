// frontend/src/index.js (ou équivalent)
import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css'; // Votre fichier CSS global si vous en avez un
import App from './App';

// Imports MUI pour le thème et les date pickers
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline'; // Pour un reset CSS propre de MUI
import { LocalizationProvider } from '@mui/x-date-pickers';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { fr } from 'date-fns/locale'; // Pour avoir les dates en français

// Créez un thème MUI simple (vous pouvez le personnaliser davantage)
const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2', // Un bleu standard Material Design
    },
    secondary: {
      main: '#dc004e', // Un rouge vif
    },
  },
  typography: {
    h1: { fontSize: '2.5rem' },
    h2: { fontSize: '2rem' },
    h3: { fontSize: '1.5rem' },
    // Ajoutez d'autres styles de typographie si besoin
  }
});


const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline /> {/* Applique les styles de base de Material Design */}
      <LocalizationProvider dateAdapter={AdapterDateFns} adapterLocale={fr}> {/* Pour les DatePicker */}
        <App />
      </LocalizationProvider>
    </ThemeProvider>
  </React.StrictMode>
);