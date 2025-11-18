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
import { BarChart3 } from 'lucide-react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from '../../../../components/ui/card';

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

const COLORS = {
  blue: 'rgba(59,130,246,0.8)',
  gray: 'rgba(148,163,184,0.4)',
};

const STATS_BAR_OPTIONS = {
  responsive: true,
  maintainAspectRatio: false,
  indexAxis: 'y',
  animation: {
    duration: 800,
    easing: 'easeOutQuart',
  },
  plugins: {
    legend: { display: false },
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
        text: 'Value',
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

function buildMetrics(result) {
  if (!result) return [];

  const metrics = [];

  if (result.mean || result.average) {
    metrics.push({
      label: 'Average',
      value: Number(result.mean || result.average) || 0,
    });
  }
  if (result.sum) {
    metrics.push({
      label: 'Sum',
      value: Number(result.sum) || 0,
    });
  }
  if (result.variance) {
    metrics.push({
      label: 'Variance',
      value: Number(result.variance) || 0,
    });
  }
  if (result.std_dev) {
    metrics.push({
      label: 'Std Dev',
      value: Number(result.std_dev) || 0,
    });
  }

  return metrics;
}

function StatsMetricsChart({ result }) {
  const metrics = buildMetrics(result);

  const labels = metrics.map((m) => m.label);
  const values = metrics.map((m) => m.value);

  const hasData = values.length > 0 && values.some((v) => v !== 0);

  const data = {
    labels,
    datasets: [
      {
        label: 'Value',
        data: values,
        backgroundColor: COLORS.blue,
        borderColor: COLORS.blue,
        borderWidth: 1,
        borderRadius: 8,
        borderSkipped: false,
        barThickness: 30,
        maxBarThickness: 40,
        hoverBackgroundColor: 'rgba(59,130,246,0.9)',
      },
    ],
  };

  return (
    <Card className="p-6 rounded-2xl shadow-sm border border-gray-200 bg-white/80 backdrop-blur">
      <CardHeader>
        <CardTitle className="text-xl font-semibold flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-blue-500" />
          Statistical Metrics
        </CardTitle>
        <CardDescription>
          Aggregated cohort metrics rendered as smooth, rounded bars.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {hasData ? (
          <div className="h-64">
            <Bar data={data} options={STATS_BAR_OPTIONS} />
          </div>
        ) : (
          <p className="text-sm text-gray-500">No statistical metrics available.</p>
        )}
      </CardContent>
    </Card>
  );
}

export default StatsMetricsChart;
