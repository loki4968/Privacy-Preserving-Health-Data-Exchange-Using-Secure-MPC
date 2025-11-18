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
import ChartDataLabels from 'chartjs-plugin-datalabels';
import { Activity } from 'lucide-react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from '../../../../components/ui/card';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Tooltip,
  Legend,
  ChartDataLabels
);

const COLORS = {
  blue: 'rgba(59,130,246,0.8)',
  green: 'rgba(34,197,94,0.8)',
};

const RISK_BAR_OPTIONS = {
  responsive: true,
  maintainAspectRatio: false,
  indexAxis: 'y',
  animation: {
    duration: 900,
    easing: 'easeOutCubic',
  },
  plugins: {
    legend: { display: false },
    tooltip: {
      mode: 'index',
      intersect: false,
      backgroundColor: 'rgba(15,23,42,0.9)',
      borderWidth: 0,
      titleFont: { weight: '600' },
    },
    datalabels: {
      anchor: 'end',
      align: 'end',
      offset: 6,
      color: '#0f172a',
      font: {
        weight: '600',
        size: 12,
      },
      formatter: (value) => value,
    },
  },
  elements: {
    line: {
      tension: 0.4,
    },
    bar: {
      borderRadius: 12,
      borderSkipped: false,
    },
  },
  scales: {
    x: {
      grid: {
        display: false,
        drawBorder: false,
      },
      ticks: {
        display: false,
      },
    },
    y: {
      grid: {
        display: false,
        drawBorder: false,
      },
      ticks: {
        color: '#64748b',
      },
    },
  },
};

function buildRiskData(canvas, normalCount, highCount) {
  const ctx = canvas.getContext('2d');

  const gradientBlue = ctx.createLinearGradient(0, 0, canvas.width, 0);
  gradientBlue.addColorStop(0, COLORS.blue);
  gradientBlue.addColorStop(1, 'rgba(59,130,246,0.4)');

  const gradientGreen = ctx.createLinearGradient(0, 0, canvas.width, 0);
  gradientGreen.addColorStop(0, COLORS.green);
  gradientGreen.addColorStop(1, 'rgba(34,197,94,0.4)');

  return {
    labels: ['Normal', 'High'],
    datasets: [
      {
        data: [normalCount, highCount],
        backgroundColor: [gradientBlue, gradientGreen],
        borderWidth: 0,
        borderRadius: 12,
        borderSkipped: false,
        barThickness: 32,
        maxBarThickness: 36,
        hoverBackgroundColor: [
          'rgba(59,130,246,0.9)',
          'rgba(34,197,94,0.9)',
        ],
      },
    ],
  };
}

function RiskLevelChart({ result }) {
  if (!result) { // Add a guard clause for initial render
    return null;
  }

  const records = Array.isArray(result.patient_records)
    ? result.patient_records
    : [];

  let normalCount = 0;
  let highCount = 0;

  records.forEach((p) => {
    const raw = (p.risk_level || '').toString().toLowerCase();

    if (!raw) {
      if (p.above_threshold) {
        highCount += 1;
      }
      return;
    }

    if (
      raw.includes('high') ||
      raw.includes('very_high') ||
      raw.includes('very high') ||
      raw.includes('hyper')
    ) {
      highCount += 1;
    } else if (
      raw.includes('normal') ||
      raw.includes('low') ||
      raw.includes('target') ||
      raw.includes('within')
    ) {
      normalCount += 1;
    }
  });

  const hasData = normalCount > 0 || highCount > 0;

  // Precompute chart data
  const chartData = React.useMemo(() => ({
    labels: ['Normal Risk', 'High Risk'],
    datasets: [
      {
        label: 'Patients',
        data: [normalCount, highCount],
        backgroundColor: [
          'rgba(34, 197, 94, 0.8)',
          'rgba(239, 68, 68, 0.8)',
        ],
        borderColor: [
          'rgba(34, 197, 94, 1)',
          'rgba(239, 68, 68, 1)',
        ],
        borderWidth: 1,
        borderRadius: 8,
        borderSkipped: false,
        // Disable data labels on the bars since we'll show them in the y-axis
        datalabels: {
          display: false
        }
      },
    ],
  }), [normalCount, highCount]);

  return (
    <Card className="p-6 rounded-2xl shadow-sm border border-gray-200 bg-white/80 backdrop-blur">
      <CardHeader>
        <CardTitle className="text-xl font-semibold flex items-center gap-2">
          <Activity className="w-5 h-5 text-sky-500" />
          Risk Level Distribution
        </CardTitle>
        <CardDescription>
          Horizontal distribution of patients in normal vs high-risk bands.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {hasData ? (
          <div className="h-64">
            <Bar
              data={chartData}
              options={{
                ...RISK_BAR_OPTIONS,
                indexAxis: 'y',
                plugins: {
                  legend: {
                    display: false // Hide the legend since we have clear labels
                  },
                  tooltip: {
                    callbacks: {
                      label: function(context) {
                        return `${context.dataset.label}: ${context.raw}`;
                      }
                    }
                  }
                },
                scales: {
                  x: {
                    beginAtZero: true,
                    grid: {
                      display: false,
                    },
                    ticks: {
                      precision: 0,
                      // Show the count as part of the x-axis label
                      callback: function(value) {
                        return value;
                      }
                    },
                    title: {
                      display: true,
                      text: 'Number of Patients',
                      color: '#6b7280',
                      font: {
                        weight: '500',
                        size: 12
                      }
                    }
                  },
                  y: {
                    grid: {
                      display: false,
                    },
                    // Add the count to the y-axis labels
                    ticks: {
                      callback: function(value, index, values) {
                        const label = this.getLabelForValue(value);
                        const count = [normalCount, highCount][index];
                        return `${label} (${count})`;
                      },
                      font: {
                        weight: '500'
                      }
                    }
                  }
                }
              }}
            />
          </div>
        ) : (
          <p className="text-sm text-gray-500">No risk level data available.</p>
        )}
      </CardContent>
    </Card>
  );
}

export default RiskLevelChart;
