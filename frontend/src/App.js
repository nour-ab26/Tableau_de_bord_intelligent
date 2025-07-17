import React, { useState, useEffect } from 'react';
import './App.css'; // Pour le style, si vous voulez

function App() {
  const [kpis, setKpis] = useState([]);
  const [downtimeReasons, setDowntimeReasons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Définir l'URL de votre API Flask
  const API_BASE_URL = 'http://127.0.0.1:5000/api';

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Récupérer les KPIs
        const kpisResponse = await fetch(`${API_BASE_URL}/kpis?start_date=2023-01-01&end_date=2023-02-01`);
        if (!kpisResponse.ok) {
          throw new Error(`Erreur HTTP: ${kpisResponse.status} pour KPIs`);
        }
        const kpisData = await kpisResponse.json();
        setKpis(kpisData);

        // Récupérer les raisons d'arrêt
        const downtimeResponse = await fetch(`${API_BASE_URL}/downtime-reasons?start_date=2023-01-01&end_date=2023-02-01`);
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
    };

    fetchData();
  }, []); // Le tableau vide signifie que cet effet ne s'exécute qu'une fois après le premier rendu

  if (loading) return <div>Chargement des données...</div>;
  if (error) return <div>Erreur: {error}</div>;

  return (
    <div className="App">
      <header className="App-header">
        <h1>Tableau de Bord de Production</h1>
      </header>
      <main>
        <h2>KPIs par Équipement (Janvier 2023)</h2>
        {kpis.length > 0 ? (
          <ul>
            {kpis.map(kpi => (
              <li key={kpi.equipment_id}>
                <strong>{kpi.equipment_name} (Line: {kpi.production_line_id})</strong> - OEE: {(kpi.oee * 100).toFixed(2)}%, Disponibilité: {(kpi.availability * 100).toFixed(2)}%, Performance: {(kpi.performance * 100).toFixed(2)}%, Qualité: {(kpi.quality * 100).toFixed(2)}%
                <br/>
                Total Produit: {kpi.total_produced}, Arrêts (Heures): {kpi.total_downtime_hours.toFixed(2)}, MTBF (Heures): {kpi.mtbf_hours.toFixed(2)}, MTTR (Heures): {kpi.mttr_hours.toFixed(2)}
              </li>
            ))}
          </ul>
        ) : (
          <p>Aucun KPI trouvé pour cette période.</p>
        )}

        <h2>Arrêts par Raison (Janvier 2023)</h2>
        {downtimeReasons.length > 0 ? (
          <ul>
            {downtimeReasons.map((reason, index) => (
              <li key={index}>
                <strong>{reason.equipment_id}</strong> - {reason.downtime_category} - {reason.downtime_reason}: {reason.incident_count} incidents ({reason.duration_seconds.toFixed(2)} secondes)
              </li>
            ))}
          </ul>
        ) : (
          <p>Aucun arrêt trouvé pour cette période.</p>
        )}
      </main>
    </div>
  );
}

export default App;