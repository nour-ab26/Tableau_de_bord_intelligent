import React from 'react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

function SensorLineChart({ data, title, sensorType, unit }) {
  if (!data || data.length === 0) {
    return <p>Aucune donnée de capteur disponible pour {sensorType}.</p>;
  }

  data.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

  const chartData = {
    labels: data.map(item => new Date(item.timestamp).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })), // Format plus court
    datasets: [
      {
        label: `${sensorType} (${unit})`,
        data: data.map(item => item.value),
        fill: false,
        backgroundColor: 'rgba(255, 99, 132, 0.7)',
        borderColor: 'rgba(255, 99, 132, 1)',
        tension: 0.2, 
        pointRadius: 1, 
        pointHoverRadius: 5,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        labels: {
          font: {
            size: 14
          }
        }
      },
      title: {
        display: true,
        text: title,
        font: {
          size: 18
        }
      },
      tooltip: {
        callbacks: {
          label: function(context) {
            return `${context.dataset.label}: ${context.raw.toFixed(2)}`;
          }
        }
      }
    },
    scales: {
      x: {
        title: {
          display: true,
          text: 'Heure',
          font: {
            size: 14
          }
        },
        ticks: {
            font: {
                size: 12
            }
        }
      },
      y: {
        title: {
          display: true,
          text: `Valeur (${unit})`,
          font: {
            size: 14
          }
        },
        beginAtZero: false,
        ticks: {
            font: {
                size: 12
            }
        }
      },
    },
  };
  return (
    <div style={{ height: '400px', width: '100%' }}> {/* Conteneur pour le graphique */}
      <Line data={chartData} options={options} />
    </div>
  );
}

export default SensorLineChart;