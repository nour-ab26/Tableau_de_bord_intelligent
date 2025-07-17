import React from 'react';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

// Enregistrez les composants Chart.js nécessaires
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

function KpiBarChart({ data, title, label, valueKey }) {
  const chartData = {
    labels: data.map(item => item.equipment_id), // Noms des équipements
    datasets: [
      {
        label: label,
        data: data.map(item => (item[valueKey] * 100).toFixed(2)), // Les KPIs sont des pourcentages (0-1), afficher en 0-100
        backgroundColor: 'rgba(75, 192, 192, 0.6)',
        borderColor: 'rgba(75, 192, 192, 1)',
        borderWidth: 1,
      },
    ],
  };

  const options = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: title,
      },
      tooltip: {
        callbacks: {
          label: function(context) {
            return `${context.dataset.label}: ${context.raw}%`;
          }
        }
      }
    },
    scales: {
        y: {
            beginAtZero: true,
            max: 100, // Les pourcentages vont jusqu'à 100
            ticks: {
                callback: function(value) {
                    return value + '%';
                }
            }
        }
    }
  };

  return <Bar data={chartData} options={options} />;
}

export default KpiBarChart;