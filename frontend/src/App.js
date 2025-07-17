import { useCallback } from 'react';
import React, { useState, useEffect } from 'react';
import './App.css'; // Si vous avez un fichier CSS pour un style global

// Importez vos composants de graphiques
import KpiBarChart from './components/KpiBarChart';
import DowntimeDoughnutChart from './components/DowntimeDoughnutChart';

// ... (Reste des imports si vous avez d'autres composants) ...

function App() {
  const [kpis, setKpis] = useState([]);
  const [downtimeReasons, setDowntimeReasons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // États pour les sélecteurs de date et d'équipement
  const [startDate, setStartDate] = useState('2023-01-01'); // Valeur par défaut
  const [endDate, setEndDate] = useState('2023-02-01');   // Valeur par défaut (fin janvier)
  const [selectedEquipment, setSelectedEquipment] = useState(''); // Pour filtrer par équipement (vide pour tous)

  const API_BASE_URL = 'http://127.0.0.1:5000/api';

  

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Construire les paramètres de requête
      const params = new URLSearchParams({
        start_date: startDate,
        end_date: endDate,
      });
      if (selectedEquipment) {
        params.append('equipment_id', selectedEquipment);
      }

      // Récupérer les KPIs
      const kpisResponse = await fetch(`${API_BASE_URL}/kpis?${params.toString()}`);
      if (!kpisResponse.ok) {
        throw new Error(`Erreur HTTP: ${kpisResponse.status} pour KPIs`);
      }
      const kpisData = await kpisResponse.json();
      setKpis(kpisData);

      // Récupérer les raisons d'arrêt
      const downtimeResponse = await fetch(`${API_BASE_URL}/downtime-reasons?${params.toString()}`);
      if (!downtimeResponse.ok) {
        throw new Error(`Erreur HTTP: ${downtimeResponse.status} pour Raisons d'arrêt`);
      }
      const downtimeData = await downtimeResponse.json();
      setDowntimeReasons(downtimeData);

    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [startDate, endDate, selectedEquipment, API_BASE_URL]);

  useEffect(() => {
    fetchData();
  }, [fetchData]); // Re-déclencher la récupération des données quand ces états changent

  // Supposons que vous ayez une liste d'équipements pour le sélecteur
  // Idéalement, cette liste viendrait aussi d'une API (ex: /api/equipments)
  const equipmentOptions = [
    { id: '', name: 'Tous les équipements' }, // Option pour ne pas filtrer
    { id: 'MCH001', name: 'Machine MCH001' },
    { id: 'MCH002', name: 'Machine MCH002' },
    // ... ajoutez tous vos IDs d'équipement ici ...
    { id: 'MCH010', name: 'Machine MCH010' },
  ];


  if (loading) return <div>Chargement des données...</div>;
  if (error) return <div>Erreur: {error}</div>;

  return (
    <div className="App">
      <header className="App-header">
        <h1>Tableau de Bord de Production Intelligent</h1>
      </header>
      <main style={{ padding: '20px' }}>
        {/* Contrôles de Filtre */}
        <div style={{ marginBottom: '20px', display: 'flex', gap: '10px', alignItems: 'center' }}>
          <label>Date de début :
            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
          </label>
          <label>Date de fin :
            <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
          </label>
          <label>Équipement :
            <select value={selectedEquipment} onChange={(e) => setSelectedEquipment(e.target.value)}>
              {equipmentOptions.map(option => (
                <option key={option.id} value={option.id}>{option.name}</option>
              ))}
            </select>
          </label>
          <button onClick={fetchData}>Mettre à jour</button> {/* Ajouté pour un contrôle manuel si besoin */}
        </div>

        {kpis.length > 0 ? (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
            {/* Graphique OEE */}
            <div style={{ border: '1px solid #ccc', padding: '15px' }}>
                <KpiBarChart
                  data={kpis}
                  title="OEE par Équipement"
                  label="OEE"
                  valueKey="oee"
                />
            </div>
            {/* Graphique Disponibilité */}
            <div style={{ border: '1px solid #ccc', padding: '15px' }}>
                <KpiBarChart
                  data={kpis}
                  title="Disponibilité par Équipement"
                  label="Disponibilité"
                  valueKey="availability"
                />
            </div>
             {/* Graphique Performance */}
            <div style={{ border: '1px solid #ccc', padding: '15px' }}>
                <KpiBarChart
                  data={kpis}
                  title="Performance par Équipement"
                  label="Performance"
                  valueKey="performance"
                />
            </div>
             {/* Graphique Qualité */}
            <div style={{ border: '1px solid #ccc', padding: '15px' }}>
                <KpiBarChart
                  data={kpis}
                  title="Qualité par Équipement"
                  label="Qualité"
                  valueKey="quality"
                />
            </div>
          </div>
        ) : (
          <p>Aucun KPI trouvé pour la période sélectionnée.</p>
        )}

        {/* Graphique des Raisons d'Arrêt */}
        {downtimeReasons.length > 0 ? (
          <div style={{ marginTop: '30px', border: '1px solid #ccc', padding: '15px', maxWidth: '600px', margin: '30px auto' }}>
            <DowntimeDoughnutChart
              data={downtimeReasons}
              title={`Répartition des Arrêts (${selectedEquipment ? selectedEquipment : 'Tous Équipements'})`}
            />
          </div>
        ) : (
          <p>Aucun arrêt trouvé pour la période sélectionnée.</p>
        )}

      </main>
    </div>
  );
}

export default App;