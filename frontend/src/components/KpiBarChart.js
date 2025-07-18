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

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

function KpiBarChart({ data, title, label, valueKey }) {
  // S'assurer que les données sont valides
  if (!data || data.length === 0) {
    return <p>Aucune donnée disponible pour {title}.</p>;
  }

  const chartData = {
    labels: data.map(item => item.equipment_id),
    datasets: [
      {
        label: label,
        data: data.map(item => (item[valueKey] * 100).toFixed(2)),
        backgroundColor: 'rgba(75, 192, 192, 0.7)', 
        borderColor: 'rgba(75, 192, 192, 1)',
        borderWidth: 1,
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
            return `${context.dataset.label}: ${context.raw}%`;
          }
        }
      }
    },
    scales: {
        x: {
            ticks: {
                font: {
                    size: 12 
                }
            }
        },
        y: {
            beginAtZero: true,
            max: 100, 
            ticks: {
                callback: function(value) {
                    return value + '%';
                },
                font: {
                    size: 12 // Agrandir la police des labels de l'axe Y
                }
            }
        }
    }
  };
  return (
    <div style={{ height: '350px', width: '100%' }}> {/* Conteneur pour le graphique */}
      <Bar data={chartData} options={options} />
    </div>
  );
}

export default KpiBarChart;