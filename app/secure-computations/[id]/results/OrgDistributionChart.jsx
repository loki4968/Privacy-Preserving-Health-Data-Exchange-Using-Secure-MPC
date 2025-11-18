'use client';

import React from 'react';
import { Doughnut } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
} from 'chart.js';
import ChartDataLabels from 'chartjs-plugin-datalabels';
import { Users } from 'lucide-react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from '../../../../components/ui/card';

ChartJS.register(ArcElement, Tooltip, Legend, ChartDataLabels);

const COLORS = {
  green: 'rgba(34,197,94,0.8)',
  red: 'rgba(239,68,68,0.8)',
};

const doughnutShadowPlugin = {
  id: 'doughnutShadow',
  beforeDraw: (chart) => {
    const { ctx } = chart;
    ctx.save();
    ctx.shadowColor = 'rgba(15,23,42,0.12)';
    ctx.shadowBlur = 18;
    ctx.shadowOffsetX = 0;
    ctx.shadowOffsetY = 10;
  },
  afterDraw: (chart) => {
    chart.ctx.restore();
  },
};

ChartJS.register(doughnutShadowPlugin);

const ORG_DONUT_OPTIONS = {
  responsive: true,
  maintainAspectRatio: false,
  cutout: '60%',
  animation: {
    duration: 900,
    easing: 'easeOutCubic',
  },
  plugins: {
    legend: {
      display: true,
      position: 'bottom',
      labels: {
        usePointStyle: true,
        boxWidth: 10,
        color: '#64748b',
        padding: 16,
        font: {
          size: 12,
        },
        generateLabels: (chart) => {
          const data = chart.data;
          if (data.labels.length && data.datasets.length) {
            return data.labels.map((label, i) => {
              const dataset = data.datasets[0];
              const value = dataset.data[i];
              const total = dataset.data.reduce((a, b) => a + b, 0);
              const percentage = Math.round((value / total) * 100) || 0;
              
              return {
                text: `${label}: ${value} (${percentage}%)`,
                fillStyle: dataset.backgroundColor[i],
                strokeStyle: dataset.borderColor ? dataset.borderColor[i] : dataset.backgroundColor[i],
                lineWidth: 1,
                hidden: isNaN(dataset.data[i]) || chart.getDatasetMeta(0).data[i].hidden,
                index: i
              };
            });
          }
          return [];
        }
      },
    },
    tooltip: {
      callbacks: {
        label: (context) => {
          const label = context.label || '';
          const value = context.parsed ?? 0;
          const total = context.dataset.data.reduce((a, b) => a + b, 0);
          const percentage = Math.round((value / total) * 100) || 0;
          return `${label}: ${value} (${percentage}%)`;
        },
      },
      backgroundColor: 'rgba(15,23,42,0.9)',
      borderWidth: 0,
      titleFont: { weight: '600' },
      padding: 12,
    },
    datalabels: {
      display: false, // Disable center percentage since we show it in the legend
    },
  },
};

function OrgDistributionChart({ result }) {
  const orgCount = result?.organizations_count ?? 0;
  const dataPoints = result?.data_points_count ?? result?.count ?? 0;
  const avgPerOrg = orgCount > 0 ? Math.round(dataPoints / orgCount) : 0;

  const hasData = orgCount > 0 || avgPerOrg > 0;

  const data = {
    labels: ['Participating Orgs', 'Avg Data Points / Org'],
    datasets: [
      {
        data: [orgCount, avgPerOrg],
        backgroundColor: [COLORS.green, COLORS.red],
        borderWidth: 0,
        hoverOffset: 4,
      },
    ],
  };

  return (
    <Card className="p-6 rounded-2xl shadow-sm border border-gray-200 bg-white/80 backdrop-blur">
      <CardHeader>
        <CardTitle className="text-xl font-semibold flex items-center gap-2">
          <Users className="w-5 h-5 text-emerald-500" />
          Participation Analysis
        </CardTitle>
        <CardDescription>
          Relationship between participating organizations and average data
          contribution.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {hasData ? (
          <div className="h-64">
            <Doughnut data={data} options={ORG_DONUT_OPTIONS} />
          </div>
        ) : (
          <p className="text-sm text-gray-500">
            No organization participation data available yet.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

export default OrgDistributionChart;
