// frontend/src/components/DowntimeDoughnutChart.js
import React from 'react';
import { Doughnut } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend
} from 'chart.js';

ChartJS.register(ArcElement, Tooltip, Legend);

function DowntimeDoughnutChart({ data, title }) {
  const labels = data.map(item => `${item.downtime_category} - ${item.downtime_reason}`);
  const durations = data.map(item => item.duration_seconds);
  const totalDuration = durations.reduce((sum, current) => sum + current, 0);

  const chartData = {
    labels: labels,
    datasets: [
      {
        label: 'Durée des Arrêts (secondes)',
        data: durations,
        backgroundColor: [
          'rgba(255, 99, 132, 0.6)', 'rgba(54, 162, 235, 0.6)', 'rgba(255, 206, 86, 0.6)',
          'rgba(75, 192, 192, 0.6)', 'rgba(153, 102, 255, 0.6)', 'rgba(255, 159, 64, 0.6)',
          'rgba(199, 199, 199, 0.6)', 'rgba(83, 102, 255, 0.6)', 'rgba(255, 99, 255, 0.6)',
          'rgba(255, 159, 64, 0.6)'
        ],
        borderColor: [
          'rgba(255, 99, 132, 1)', 'rgba(54, 162, 235, 1)', 'rgba(255, 206, 86, 1)',
          'rgba(75, 192, 192, 1)', 'rgba(153, 102, 255, 1)', 'rgba(255, 159, 64, 1)',
          'rgba(199, 199, 199, 1)', 'rgba(83, 102, 255, 1)', 'rgba(255, 99, 255, 1)',
          'rgba(255, 159, 64, 1)'
        ],
        borderWidth: 1,
      },
    ],
  };

  const options = {
    responsive: true,
    plugins: {
      legend: {
        position: 'right',
      },
      title: {
        display: true,
        text: title,
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

  return <Doughnut data={chartData} options={options} />;
}

export default DowntimeDoughnutChart;