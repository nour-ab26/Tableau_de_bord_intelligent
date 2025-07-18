//import { useCallback } from 'react';
import React, { useState, useEffect } from 'react';
import './App.css'; 

// Importez vos composants de graphiques
import KpiBarChart from './components/KpiBarChart';
import DowntimeDoughnutChart from './components/DowntimeDoughnutChart';


function App() {
  const [kpis, setKpis] = useState([]);
  const [downtimeReasons, setDowntimeReasons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // État pour la liste dynamique des équipements
  const [equipmentOptions, setEquipmentOptions] = useState([{ id: '', name: 'Tous les équipements' }]);
  // États pour les sélecteurs de date et d'équipement
  const [startDate, setStartDate] = useState('2023-01-01'); // Valeur par défaut
  const [endDate, setEndDate] = useState('2023-02-01');   // Valeur par défaut (fin janvier)
  const [selectedEquipment, setSelectedEquipment] = useState(''); // Pour filtrer par équipement (vide pour tous)

  const API_BASE_URL = 'http://127.0.0.1:5000/api';


  const fetchEquipmentList = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/equipments`);
      if (!response.ok) {
        throw new Error(`Erreur HTTP: ${response.status} pour équipements`);
      }
      const data = await response.json();
      // Mappez les données pour qu'elles correspondent au format {id, name} du sélecteur
      const options = [{ id: '', name: 'Tous les équipements' }, ...data.map(eq => ({ id: eq.equipment_id, name: eq.equipment_name }))];
      setEquipmentOptions(options);
    } catch (err) {
      console.error("Erreur lors de la récupération de la liste des équipements:", err);
      // Gérer l'erreur, potentiellement afficher un message à l'utilisateur
    }
  };
  

  const fetchData = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        start_date: startDate,
        end_date: endDate,
      });
      if (selectedEquipment) {
        params.append('equipment_id', selectedEquipment);
      }

      const kpisResponse = await fetch(`${API_BASE_URL}/kpis?${params.toString()}`);
      if (!kpisResponse.ok) {
        throw new Error(`Erreur HTTP: ${kpisResponse.status} pour KPIs`);
      }
      const kpisData = await kpisResponse.json();
      setKpis(kpisData);

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
    fetchEquipmentList();
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]); 
  // Supposons que vous ayez une liste d'équipements pour le sélecteur
  // Idéalement, cette liste viendrait aussi d'une API (ex: /api/equipments)
  


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