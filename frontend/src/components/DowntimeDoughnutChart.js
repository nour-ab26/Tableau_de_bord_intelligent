import React from 'react';
import { Doughnut } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend
} from 'chart.js';

ChartJS.register(ArcElement, Tooltip, Legend);

function generateDistinctColors(numColors) {
    const colors = [];
    // Utiliser HSL pour varier le "hue" (teinte) de manière équitable
    for (let i = 0; i < numColors; i++) {
        const hue = (i * 360 / numColors) % 360; // Distribuer les teintes sur le cercle chromatique
        colors.push(`hsl(${hue}, 70%, 50%)`); // Saturation moyenne, luminosité moyenne
    }
    return colors;
}

function DowntimeDoughnutChart({ data, title }) {
  if (!data || data.length === 0) {
    return <p>Aucune donnée de répartition des arrêts disponible.</p>;
  }

  const labels = data.map(item => `${item.downtime_category} - ${item.downtime_reason}`);
  const durations = data.map(item => item.duration_seconds);
  const totalDuration = durations.reduce((sum, current) => sum + current, 0);

  // Générer les couleurs dynamiquement en fonction du nombre d'éléments
  const distinctColors = generateDistinctColors(labels.length);


  const chartData = {
    labels: labels,
    datasets: [
      {
        label: 'Durée des Arrêts (secondes)',
        data: durations,
        backgroundColor: distinctColors.map(color => color.replace('hsl(', 'hsla(').replace(')', ', 0.7)')), // Avec opacité
        borderColor: distinctColors.map(color => color.replace('hsl(', 'hsla(').replace(')', ', 1)')), // Couleurs pleines pour la bordure
        borderWidth: 1,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false, // Permet de mieux contrôler la taille
    plugins: {
      legend: {
        position: 'right',
        labels: {
          font: {
            size: 14 // Agrandir la police de la légende
          }
        }
      },
      title: {
        display: true,
        text: title,
        font: {
          size: 18 // Agrandir la police du titre
        }
      },
      tooltip: {
        callbacks: {
          label: function(context) {
            const label = context.label || '';
            const value = context.raw;
            const percentage = totalDuration > 0 ? ((value / totalDuration) * 100).toFixed(2) : 0;
            return `${label}: ${value.toFixed(0)} secondes (${percentage}%)`;
          }
        }
      }
    }
  };
    // Mettre la hauteur/largeur du conteneur pour que maintainAspectRatio: false fonctionne
  return (
    <div style={{ height: '400px', width: '100%' }}> {/* Conteneur pour le graphique */}
      <Doughnut data={chartData} options={options} />
    </div>
  );
}

export default DowntimeDoughnutChart;