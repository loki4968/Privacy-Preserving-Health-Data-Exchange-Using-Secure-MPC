'use client';

import React from 'react';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Tooltip,
  Legend,
} from 'chart.js';
import { Gauge } from 'lucide-react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from '../../../../components/ui/card';

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

const COLORS = {
  green: 'rgba(34,197,94,0.8)',
  red: 'rgba(239,68,68,0.8)',
};

const THRESHOLD_BAR_OPTIONS = {
  responsive: true,
  maintainAspectRatio: false,
  indexAxis: 'y',
  animation: {
    duration: 850,
    easing: 'easeOutQuint',
  },
  plugins: {
    legend: { 
      display: false 
    },
    tooltip: {
      callbacks: {
        label: function(context) {
          return `${context.dataset.label || ''}: ${context.parsed.x}`;
        }
      },
      backgroundColor: 'rgba(15,23,42,0.9)',
      borderWidth: 0,
      titleFont: { weight: '600' },
    },
  },
  elements: {
    line: {
      tension: 0.4,
    },
    bar: {
      borderRadius: 8,
      borderSkipped: false,
    },
  },
  scales: {
    x: {
      beginAtZero: true,
      grid: {
        display: false,
      },
      title: {
        display: true,
        text: 'Number of Patients',
        color: '#6b7280',
        font: {
          weight: '500',
          size: 12
        }
      },
      ticks: {
        precision: 0,
        callback: function(value) {
          return value;
        }
      }
    },
    y: {
      grid: {
        display: false,
      },
      ticks: {
        callback: function(value, index, values) {
          const label = this.getLabelForValue(value);
          const data = this.chart.data.datasets[0].data;
          return `${label} (${data[index]})`;
        },
        font: {
          weight: '500'
        }
      }
    },
  },
};

function ThresholdChart({ result }) {
  const records = Array.isArray(result?.patient_records)
    ? result.patient_records
    : [];

  const below = records.filter((p) => !p.above_threshold).length;
  const above = records.filter((p) => p.above_threshold).length;
  const hasData = above + below > 0;

  const data = {
    labels: ['Below threshold', 'Above threshold'],
    datasets: [
      {
        label: 'Patients',
        data: [below, above],
        backgroundColor: [COLORS.green, COLORS.red],
        borderColor: [COLORS.green, COLORS.red],
        borderWidth: 1,
        barThickness: 30,
        maxBarThickness: 40,
        borderRadius: 8,
        borderSkipped: false,
        hoverBackgroundColor: ['rgba(34,197,94,0.9)', 'rgba(239,68,68,0.9)'],
      },
    ],
  };

  const thresholdValue = result?.threshold_value;

  return (
    <Card className="p-6 rounded-2xl shadow-sm border border-gray-200 bg-white/80 backdrop-blur">
      <CardHeader>
        <CardTitle className="text-xl font-semibold flex items-center gap-2">
          <Gauge className="w-5 h-5 text-red-500" />
          Threshold Distribution
        </CardTitle>
        <CardDescription>
          Patients below vs above the configured threshold
          {typeof thresholdValue === 'number' ? ` (${thresholdValue})` : ''}.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {hasData ? (
          <>
            <div className="h-64">
              <Bar data={data} options={THRESHOLD_BAR_OPTIONS} />
            </div>
            <div className="mt-4 flex items-center justify-center gap-6 text-xs text-gray-500">
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-[rgba(34,197,94,0.8)]" />
                <span>Below threshold</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-[rgba(239,68,68,0.8)]" />
                <span>Above threshold</span>
              </div>
            </div>
          </>
        ) : (
          <p className="text-sm text-gray-500">No threshold distribution data available.</p>
        )}
      </CardContent>
    </Card>
  );
}

export default ThresholdChart;
