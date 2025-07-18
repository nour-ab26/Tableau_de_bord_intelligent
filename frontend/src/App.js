import React, { useState, useEffect } from 'react';

// Imports MUI
import {
  AppBar, Toolbar, Typography, Container, Box,
  Grid, Paper, Card, CardContent, CircularProgress,
  Alert, Button, FormControl, InputLabel, Select, MenuItem,
  TextField
} from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';


import KpiBarChart from './components/KpiBarChart';
import DowntimeDoughnutChart from './components/DowntimeDoughnutChart';
import SensorLineChart from './components/SensorLineChart';

function App() {
  const [kpis, setKpis] = useState([]);
  const [downtimeReasons, setDowntimeReasons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [equipmentOptions, setEquipmentOptions] = useState([{ id: '', name: 'Tous les équipements' }]);

  const [startDate, setStartDate] = useState(new Date(2023, 0, 1));
  const [endDate, setEndDate] = useState(new Date(2023, 1, 1));

  const [selectedEquipment, setSelectedEquipment] = useState('');
  const [sensorData, setSensorData] = useState([]);
  const [selectedSensorType, setSelectedSensorType] = useState('Temperature_Motor');
  const [sensorUnits, setSensorUnits] = useState({});


  const API_BASE_URL = 'http://127.0.0.1:5000/api';

  const formatDateForAPI = (date) => {
    if (!date) return '';
    return date.toISOString().split('T')[0]; // Format YYYY-MM-DD
  };
  const formatDateTimeForAPI = (date) => {
    if (!date) return '';
    return date.toISOString().slice(0, 19).replace('T', ' '); // Format YYYY-MM-DD HH:MM:SS
  };

  const fetchEquipmentList = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/equipments`);
      if (!response.ok) { throw new Error(`HTTP error! status: ${response.status} for equipments`); }
      const data = await response.json();
      const options = [{ id: '', name: 'Tous les équipements' }, ...data.map(eq => ({ id: eq.equipment_id, name: eq.equipment_name }))];
      setEquipmentOptions(options);

      const uniqueSensorTypes = [
          'Temperature_Motor', 'Vibration_Bearing', 'Pressure_Hydraulic', 'Current_Consumption'
      ];
      const unitsMap = {
          'Temperature_Motor': '°C',
          'Vibration_Bearing': 'g',
          'Pressure_Hydraulic': 'bar',
          'Current_Consumption': 'A'
      };
      setSensorUnits(unitsMap);

    } catch (err) {
      console.error("Error fetching equipment list:", err);
    }
  };

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const formattedStartDate = formatDateForAPI(startDate);
      const formattedEndDate = formatDateForAPI(endDate);

      const kpiParams = new URLSearchParams({
        start_date: formattedStartDate,
        end_date: formattedEndDate,
      });
      if (selectedEquipment) {
        kpiParams.append('equipment_id', selectedEquipment);
      }

      const kpisResponse = await fetch(`${API_BASE_URL}/kpis?${kpiParams.toString()}`);
      if (!kpisResponse.ok) { throw new Error(`HTTP error! status: ${kpisResponse.status} for KPIs`); }
      const kpisData = await kpisResponse.json();
      setKpis(kpisData);

      const downtimeResponse = await fetch(`${API_BASE_URL}/downtime-reasons?${kpiParams.toString()}`);
      if (!downtimeResponse.ok) { throw new Error(`HTTP error! status: ${downtimeResponse.status} for Downtime Reasons`); }
      const downtimeData = await downtimeResponse.json();
      setDowntimeReasons(downtimeData);

      if (selectedEquipment && selectedSensorType) {
        const sensorStartDate = new Date(startDate);
        sensorStartDate.setHours(7, 0, 0);
        const sensorEndDate = new Date(startDate);
        sensorEndDate.setHours(17, 0, 0);

        const sensorParams = new URLSearchParams({
            start_date: formatDateTimeForAPI(sensorStartDate),
            end_date: formatDateTimeForAPI(sensorEndDate),
            equipment_id: selectedEquipment,
            sensor_type: selectedSensorType,
        });

        const sensorResponse = await fetch(`${API_BASE_URL}/sensor-data?${sensorParams.toString()}`);
        if (!sensorResponse.ok) { throw new Error(`HTTP error! status: ${sensorResponse.status} for Sensor Data`); }
        const sensorDataFetched = await sensorResponse.json();
        setSensorData(sensorDataFetched);
      } else {
        setSensorData([]);
      }

    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEquipmentList();
  }, []);

  useEffect(() => {
    if (startDate && endDate) {
        fetchData();
    }
  }, [startDate, endDate, selectedEquipment, selectedSensorType]);


  return (
    <Box sx={{ flexGrow: 1 }}> {/* Utilisez Box comme conteneur principal pour le thème */}
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Tableau de Bord de Production Intelligent
          </Typography>
        </Toolbar>
      </AppBar>

      <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
        <Box component={Paper} sx={{ p: 3, mb: 4 }}>
          <Typography variant="h5" gutterBottom>Filtres de Données</Typography>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} sm={4} md={3}>
              <DatePicker
                label="Date de début"
                value={startDate}
                onChange={(newValue) => setStartDate(newValue)}
                renderInput={(params) => <TextField {...params} fullWidth />}
                format="yyyy-MM-dd"
              />
            </Grid>
            <Grid item xs={12} sm={4} md={3}>
              <DatePicker
                label="Date de fin"
                value={endDate}
                onChange={(newValue) => setEndDate(newValue)}
                renderInput={(params) => <TextField {...params} fullWidth />}
                format="yyyy-MM-dd"
              />
            </Grid>
            <Grid item xs={12} sm={4} md={3}>
              <FormControl fullWidth>
                <InputLabel>Équipement</InputLabel>
                <Select
                  value={selectedEquipment}
                  label="Équipement"
                  onChange={(e) => setSelectedEquipment(e.target.value)}
                >
                  {equipmentOptions.map(option => (
                    <MenuItem key={option.id} value={option.id}>{option.name}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            {selectedEquipment && (
              <Grid item xs={12} sm={4} md={3}>
                <FormControl fullWidth>
                  <InputLabel>Type de Capteur</InputLabel>
                  <Select
                    value={selectedSensorType}
                    label="Type de Capteur"
                    onChange={(e) => setSelectedSensorType(e.target.value)}
                  >
                    {Object.keys(sensorUnits).map(type => (
                      <MenuItem key={type} value={type}>{type.replace('_', ' ')}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
            )}
            <Grid item xs={12} sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                <Button variant="contained" onClick={fetchData} disabled={loading}>
                    {loading ? <CircularProgress size={24} /> : "Mettre à jour"}
                </Button>
            </Grid>
          </Grid>
        </Box>

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
            <CircularProgress />
            <Typography variant="h6" sx={{ ml: 2 }}>Chargement des données...</Typography>
          </Box>
        ) : error ? (
          <Alert severity="error" sx={{ my: 4 }}>{error}</Alert>
        ) : (
          <>
            {/* Section KPIs */}
            <Typography variant="h4" gutterBottom sx={{ mt: 4 }}>Indicateurs Clés de Performance</Typography>
            {kpis.length > 0 ? (
              <Grid container spacing={3}>
                {kpis.map(kpi => (
                  <Grid item xs={12} sm={6} md={6} lg={4} key={kpi.equipment_id}> {/* AJUSTÉ: 2 ou 3 cartes par ligne */}
                    <Card variant="outlined" sx={{ height: '100%' }}>
                      <CardContent>
                        <Typography variant="h6" component="div" sx={{ mb: 1.5 }}>
                          {kpi.equipment_name || kpi.equipment_id}
                        </Typography>
                        <Typography color="text.secondary">Ligne: {kpi.production_line_id}</Typography>
                        <Typography variant="h5" color="primary" sx={{ my: 1 }}>
                          OEE: {(kpi.oee * 100).toFixed(1)}%
                        </Typography>
                        <Typography>Disponibilité: {(kpi.availability * 100).toFixed(1)}%</Typography>
                        <Typography>Performance: {(kpi.performance * 100).toFixed(1)}%</Typography>
                        <Typography>Qualité: {(kpi.quality * 100).toFixed(1)}%</Typography>
                        <Typography variant="body2" sx={{ mt: 1 }}>
                          Produit: {kpi.total_produced}, Rejeté: {kpi.total_rejected}
                        </Typography>
                        <Typography variant="body2">
                          Arrêts (Heures): {kpi.total_downtime_hours.toFixed(1)}, MTBF (H): {kpi.mtbf_hours.toFixed(1)}, MTTR (H): {kpi.mttr_hours.toFixed(1)}
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            ) : (
              <Alert severity="info" sx={{ mt: 2 }}>Aucun KPI trouvé pour la période sélectionnée ou l'équipement.</Alert>
            )}

            {/* Graphiques de résumé global (si pas d'équipement sélectionné ou pour les résumés) */}
            {!selectedEquipment && kpis.length > 0 && (
                <Grid container spacing={3} sx={{ mt: 4 }}>
                    <Grid item xs={12} md={6}> {/* AJUSTÉ: 1 ou 2 graphiques par ligne */}
                        <Paper sx={{ p: 2 }}>
                            <KpiBarChart
                                data={kpis}
                                title="OEE par Équipement"
                                label="OEE"
                                valueKey="oee"
                            />
                        </Paper>
                    </Grid>
                    <Grid item xs={12} md={6}>
                         <Paper sx={{ p: 2 }}>
                            <KpiBarChart
                                data={kpis}
                                title="Disponibilité par Équipement"
                                label="Disponibilité"
                                valueKey="availability"
                            />
                        </Paper>
                    </Grid>
                     {/* Vous pouvez ajouter d'autres graphiques de résumé ici */}
                </Grid>
            )}


            {/* Section Raisons d'Arrêt */}
            <Typography variant="h4" gutterBottom sx={{ mt: 4 }}>Répartition des Arrêts</Typography>
            {downtimeReasons.length > 0 ? (
              <Box component={Paper} sx={{ p: 2, mx: 'auto', width: { xs: '100%', md: '80%', lg: '70%' } }}> {/* Largeur ajustée pour le Doughnut */}
                <DowntimeDoughnutChart
                  data={downtimeReasons}
                  title={`Répartition des Arrêts (${selectedEquipment ? equipmentOptions.find(opt => opt.id === selectedEquipment)?.name : 'Tous Équipements'})`}
                />
              </Box>
            ) : (
              <Alert severity="info" sx={{ mt: 2 }}>Aucun arrêt trouvé pour la période sélectionnée ou l'équipement.</Alert>
            )}

            {/* Section Données de Capteurs */}
            <Typography variant="h4" gutterBottom sx={{ mt: 4 }}>Données de Capteurs</Typography>
            {selectedEquipment && (
              <>
                <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
                  Capteur : {selectedSensorType.replace('_', ' ')} pour {equipmentOptions.find(opt => opt.id === selectedEquipment)?.name}
                </Typography>
                {sensorData.length > 0 ? (
                  <Box component={Paper} sx={{ p: 2, mx: 'auto', width: { xs: '100%', md: '90%', lg: '80%' } }}> {/* Largeur ajustée pour le graphique de capteurs */}
                    <SensorLineChart
                      data={sensorData}
                      title={`Relevés de Capteur: ${selectedSensorType.replace('_', ' ')}`}
                      sensorType={selectedSensorType}
                      unit={sensorUnits[selectedSensorType]}
                    />
                  </Box>
                ) : (
                  <Alert severity="info" sx={{ mt: 2 }}>Aucune donnée de capteur disponible pour cette sélection ou période.</Alert>
                )}
              </>
            )}
            {!selectedEquipment && (
                <Alert severity="info" sx={{ mt: 2 }}>Sélectionnez un équipement pour visualiser les données de capteurs spécifiques.</Alert>
            )}
          </>
        )}
      </Container>
    </Box>
  );
}

export default App;