'use client';

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '../../../context/AuthContext';
import { toast } from 'react-hot-toast';
import { 
  ArrowLeft, 
  Download, 
  BarChart3, 
  TrendingUp, 
  Users, 
  Database,
  Shield,
  Activity,
  Eye,
  AlertCircle,
  PieChart,
  LineChart
} from 'lucide-react';
import Link from 'next/link';
import { secureComputationService } from '../../../services/secureComputationService';
import { Bar, Pie, Line, Doughnut } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import SecureAnalysisChartsSection from './SecureAnalysisChartsSection';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

export default function ResultsVisualizationPage() {
  const { id } = useParams();
  const router = useRouter();
  const { user } = useAuth();
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [computation, setComputation] = useState(null);
  const [activeView, setActiveView] = useState('overview');
  const [showCharts, setShowCharts] = useState(true);

  // Check if user has permission to access secure computations
  if (user?.role === 'patient') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Access Denied</h1>
          <p className="text-gray-600 mb-6">You don't have permission to access secure computations.</p>
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Return to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  useEffect(() => {
    if (!user) {
      router.push('/login');
      return;
    }
    fetchResultsData();
  }, [id, user]);

  const fetchResultsData = async () => {
    try {
      setLoading(true);
      const token = user?.token || localStorage.getItem('token');
      
      // Fetch computation details
      const computationData = await secureComputationService.getComputationDetails(id, token);
      setComputation(computationData);
      
      // Fetch results
      const resultData = await secureComputationService.getComputationResult(id, token);
      // Normalize payload: backend may return a wrapper with `result` nested
      const normalized = resultData && resultData.result
        ? {
            ...resultData.result,
            // bubble up useful meta for UI
            status: resultData.status || resultData.result.status || 'completed',
            completed_at: resultData.completed_at || resultData.result.completed_at,
            organizations_count: resultData.organizations_count || resultData.participants_count || resultData.result.organizations_count,
            data_points_count: resultData.data_points_count || resultData.result.data_points_count || resultData.result.count,
          }
        : resultData;
      setResult(normalized);
      
    } catch (err) {
      console.error('Error fetching results data:', err);
      setError(err.message);
      toast.error('Failed to load results data');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (format) => {
    try {
      const token = user?.token || localStorage.getItem('token');
      const { blob, filename } = await secureComputationService.exportResults(id, { format }, token);
      
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      toast.success(`Results exported as ${format.toUpperCase()}`);
    } catch (err) {
      console.error('Export failed:', err);
      toast.error('Failed to export results');
    }
  };

  // Chart generation functions
  const generateBarChart = () => {
    if (!result) return null;

    const metrics = [];
    const values = [];
    const colors = [];

    if (result.mean || result.average) {
      metrics.push('Average');
      values.push(Number(result.mean || result.average));
      colors.push('rgba(59, 130, 246, 0.8)');
    }
    if (result.sum) {
      metrics.push('Sum');
      values.push(Number(result.sum));
      colors.push('rgba(16, 185, 129, 0.8)');
    }
    if (result.variance) {
      metrics.push('Variance');
      values.push(Number(result.variance));
      colors.push('rgba(245, 158, 11, 0.8)');
    }
    if (result.std_dev) {
      metrics.push('Std Dev');
      values.push(Number(result.std_dev));
      colors.push('rgba(139, 92, 246, 0.8)');
    }

    if (metrics.length === 0) return null;

    return {
      labels: metrics,
      datasets: [{
        label: 'Statistical Metrics',
        data: values,
        backgroundColor: colors,
        borderColor: colors.map(color => color.replace('0.8', '1')),
        borderWidth: 2,
        borderRadius: 8,
        borderSkipped: false,
      }]
    };
  };

  const generatePieChart = () => {
    if (!result || !result.organizations_count) return null;

    const orgCount = result.organizations_count;
    const dataPoints = result.count || result.data_points_count || 0;
    const avgPerOrg = orgCount > 0 ? Math.round(dataPoints / orgCount) : 0;

    return {
      labels: ['Participating Organizations', 'Average Data Points per Org'],
      datasets: [{
        data: [orgCount, avgPerOrg],
        backgroundColor: [
          'rgba(239, 68, 68, 0.8)',
          'rgba(34, 197, 94, 0.8)'
        ],
        borderColor: [
          'rgba(239, 68, 68, 1)',
          'rgba(34, 197, 94, 1)'
        ],
        borderWidth: 2
      }]
    };
  };

  const generateCorrelationChart = () => {
    if (!result?.correlation_coefficient) return null;

    const correlation = Number(result.correlation_coefficient);
    const strength = Math.abs(correlation);
    
    return {
      labels: ['Negative Correlation', 'No Correlation', 'Positive Correlation'],
      datasets: [{
        label: 'Correlation Strength',
        data: [
          correlation < 0 ? strength : 0,
          1 - strength,
          correlation > 0 ? strength : 0
        ],
        backgroundColor: [
          'rgba(239, 68, 68, 0.8)',
          'rgba(156, 163, 175, 0.8)',
          'rgba(34, 197, 94, 0.8)'
        ],
        borderWidth: 0
      }]
    };
  };

  const generateTimeSeriesChart = () => {
    if (!result?.time_series_data) return null;

    const timeData = result.time_series_data;
    return {
      labels: timeData.map(point => point.timestamp || point.date),
      datasets: [{
        label: 'Value Over Time',
        data: timeData.map(point => point.value),
        borderColor: 'rgba(59, 130, 246, 1)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        fill: true,
        tension: 0.4,
        pointBackgroundColor: 'rgba(59, 130, 246, 1)',
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
        pointRadius: 6
      }]
    };
  };

  const generateThresholdDistributionChart = () => {
    if (!result || !Array.isArray(result.patient_records) || result.patient_records.length === 0) return null;

    const below = result.patient_records.filter(p => !p.above_threshold).length;
    const above = result.patient_records.filter(p => p.above_threshold).length;

    if (above + below === 0) return null;

    return {
      labels: ['Below Threshold', 'Above Threshold'],
      datasets: [{
        data: [below, above],
        backgroundColor: [
          'rgba(34, 197, 94, 0.8)',
          'rgba(239, 68, 68, 0.8)'
        ],
        borderColor: [
          'rgba(34, 197, 94, 1)',
          'rgba(239, 68, 68, 1)'
        ],
        borderWidth: 2
      }]
    };
  };

  const generateRiskLevelChart = () => {
    if (!result || !Array.isArray(result.patient_records) || result.patient_records.length === 0) return null;

    const counts = {};
    result.patient_records.forEach(p => {
      const levelRaw = (p.risk_level || 'unknown').toString();
      const levelKey = levelRaw.toLowerCase();
      counts[levelKey] = (counts[levelKey] || 0) + 1;
    });

    const labels = Object.keys(counts).map(key => {
      return key
        .split('_')
        .map(part => part.charAt(0).toUpperCase() + part.slice(1))
        .join(' ');
    });
    const values = Object.values(counts);

    if (labels.length === 0) return null;

    return {
      labels,
      datasets: [{
        label: 'Patients by Risk Level',
        data: values,
        backgroundColor: [
          'rgba(59, 130, 246, 0.8)',
          'rgba(34, 197, 94, 0.8)',
          'rgba(249, 115, 22, 0.8)',
          'rgba(239, 68, 68, 0.8)',
          'rgba(148, 163, 184, 0.8)'
        ],
        borderColor: [
          'rgba(59, 130, 246, 1)',
          'rgba(34, 197, 94, 1)',
          'rgba(249, 115, 22, 1)',
          'rgba(239, 68, 68, 1)',
          'rgba(148, 163, 184, 1)'
        ],
        borderWidth: 2,
        borderRadius: 8,
        borderSkipped: false,
      }]
    };
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom',
        labels: {
          usePointStyle: true,
          padding: 16,
        },
      },
      tooltip: {
        backgroundColor: 'rgba(15, 23, 42, 0.9)',
        titleColor: '#fff',
        bodyColor: '#e5e7eb',
        borderColor: 'transparent',
        borderWidth: 0,
        cornerRadius: 10,
        displayColors: true,
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
      y: {
        beginAtZero: true,
        grid: {
          color: 'rgba(148,163,184,0.15)',
          drawBorder: false,
        },
        ticks: {
          color: '#9ca3af',
        },
      },
      x: {
        grid: {
          color: 'rgba(148,163,184,0.08)',
          drawBorder: false,
        },
        ticks: {
          color: '#9ca3af',
        },
      },
    },
  };

  const renderStatisticsCards = () => {
    if (!result) {
      return (
        <div className="text-center py-12 text-gray-500">
          <BarChart3 className="w-16 h-16 mx-auto mb-4 text-gray-300" />
          <p>No statistical data available</p>
        </div>
      );
    }

    const cards = [];

    if (result.threshold_value !== undefined && result.above_threshold_count !== undefined) {
      cards.push(
        <div key="threshold" className="bg-gradient-to-br from-red-50 to-red-100 p-6 rounded-xl border border-red-200">
          <div className="flex items-center justify-between mb-3">
            <AlertCircle className="w-8 h-8 text-red-600" />
            <span className="text-xs font-medium text-red-600 bg-red-200 px-2 py-1 rounded-full">THRESHOLD</span>
          </div>
          <p className="text-sm font-medium text-red-900 mb-1">Above {result.threshold_value}</p>
          <p className="text-3xl font-bold text-red-700">{result.above_threshold_count}</p>
          {typeof result.above_threshold_percentage === 'number' && (
            <p className="text-xs text-red-700 mt-1">{result.above_threshold_percentage.toFixed(1)}% of patients</p>
          )}
        </div>
      );
    }

    // Basic Statistics
    if (result.mean || result.average) {
      cards.push(
        <div key="mean" className="bg-gradient-to-br from-blue-50 to-blue-100 p-6 rounded-xl border border-blue-200">
          <div className="flex items-center justify-between mb-3">
            <TrendingUp className="w-8 h-8 text-blue-600" />
            <span className="text-xs font-medium text-blue-600 bg-blue-200 px-2 py-1 rounded-full">AVG</span>
          </div>
          <p className="text-sm font-medium text-blue-900 mb-1">Average</p>
          <p className="text-3xl font-bold text-blue-700">{Number(result.mean || result.average).toFixed(2)}</p>
        </div>
      );
    }

    if (result.sum) {
      cards.push(
        <div key="sum" className="bg-gradient-to-br from-green-50 to-green-100 p-6 rounded-xl border border-green-200">
          <div className="flex items-center justify-between mb-3">
            <Database className="w-8 h-8 text-green-600" />
            <span className="text-xs font-medium text-green-600 bg-green-200 px-2 py-1 rounded-full">SUM</span>
          </div>
          <p className="text-sm font-medium text-green-900 mb-1">Total Sum</p>
          <p className="text-3xl font-bold text-green-700">{Number(result.sum).toFixed(2)}</p>
        </div>
      );
    }

    if (result.count || result.data_points_count) {
      cards.push(
        <div key="count" className="bg-gradient-to-br from-purple-50 to-purple-100 p-6 rounded-xl border border-purple-200">
          <div className="flex items-center justify-between mb-3">
            <Users className="w-8 h-8 text-purple-600" />
            <span className="text-xs font-medium text-purple-600 bg-purple-200 px-2 py-1 rounded-full">COUNT</span>
          </div>
          <p className="text-sm font-medium text-purple-900 mb-1">Data Points</p>
          <p className="text-3xl font-bold text-purple-700">{result.count || result.data_points_count}</p>
        </div>
      );
    }

    if (result.variance) {
      cards.push(
        <div key="variance" className="bg-gradient-to-br from-orange-50 to-orange-100 p-6 rounded-xl border border-orange-200">
          <div className="flex items-center justify-between mb-3">
            <Activity className="w-8 h-8 text-orange-600" />
            <span className="text-xs font-medium text-orange-600 bg-orange-200 px-2 py-1 rounded-full">VAR</span>
          </div>
          <p className="text-sm font-medium text-orange-900 mb-1">Variance</p>
          <p className="text-3xl font-bold text-orange-700">{Number(result.variance).toFixed(2)}</p>
        </div>
      );
    }

    // Advanced Statistics - Correlation
    if (result.correlation_coefficient) {
      cards.push(
        <div key="correlation" className="bg-gradient-to-br from-indigo-50 to-indigo-100 p-6 rounded-xl border border-indigo-200">
          <div className="flex items-center justify-between mb-3">
            <TrendingUp className="w-8 h-8 text-indigo-600" />
            <span className="text-xs font-medium text-indigo-600 bg-indigo-200 px-2 py-1 rounded-full">CORR</span>
          </div>
          <p className="text-sm font-medium text-indigo-900 mb-1">Correlation</p>
          <p className="text-3xl font-bold text-indigo-700">{Number(result.correlation_coefficient).toFixed(3)}</p>
          <p className="text-xs text-indigo-600 mt-1">{result.interpretation}</p>
        </div>
      );
    }

    // Machine Learning Results
    if (result.accuracy) {
      cards.push(
        <div key="accuracy" className="bg-gradient-to-br from-emerald-50 to-emerald-100 p-6 rounded-xl border border-emerald-200">
          <div className="flex items-center justify-between mb-3">
            <Shield className="w-8 h-8 text-emerald-600" />
            <span className="text-xs font-medium text-emerald-600 bg-emerald-200 px-2 py-1 rounded-full">ML</span>
          </div>
          <p className="text-sm font-medium text-emerald-900 mb-1">Model Accuracy</p>
          <p className="text-3xl font-bold text-emerald-700">{(Number(result.accuracy) * 100).toFixed(1)}%</p>
        </div>
      );
    }

    // Regression Results
    if (result.r_squared) {
      cards.push(
        <div key="r_squared" className="bg-gradient-to-br from-cyan-50 to-cyan-100 p-6 rounded-xl border border-cyan-200">
          <div className="flex items-center justify-between mb-3">
            <BarChart3 className="w-8 h-8 text-cyan-600" />
            <span className="text-xs font-medium text-cyan-600 bg-cyan-200 px-2 py-1 rounded-full">R²</span>
          </div>
          <p className="text-sm font-medium text-cyan-900 mb-1">R-Squared</p>
          <p className="text-3xl font-bold text-cyan-700">{Number(result.r_squared).toFixed(3)}</p>
        </div>
      );
    }

    // Organizations Count
    if (result.organizations_count) {
      cards.push(
        <div key="orgs" className="bg-gradient-to-br from-rose-50 to-rose-100 p-6 rounded-xl border border-rose-200">
          <div className="flex items-center justify-between mb-3">
            <Users className="w-8 h-8 text-rose-600" />
            <span className="text-xs font-medium text-rose-600 bg-rose-200 px-2 py-1 rounded-full">ORGS</span>
          </div>
          <p className="text-sm font-medium text-rose-900 mb-1">Organizations</p>
          <p className="text-3xl font-bold text-rose-700">{result.organizations_count}</p>
        </div>
      );
    }

    if (cards.length === 0) {
      return (
        <div className="text-center py-12 text-gray-500">
          <BarChart3 className="w-16 h-16 mx-auto mb-4 text-gray-300" />
          <p>No statistical data available</p>
        </div>
      );
    }

    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {cards}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading results...</p>
        </div>
      </div>
    );
  }

  if (error || !result) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Error Loading Results</h1>
          <p className="text-gray-600 mb-6">{error || 'Results not found'}</p>
          <Link
            href={`/secure-computations/${id}`}
            className="inline-flex items-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Computation
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <Link
            href={`/secure-computations/${id}`}
            className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-700 mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Computation
          </Link>
          
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
                <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
                  <BarChart3 className="w-6 h-6 text-white" />
                </div>
                Results Visualization
              </h1>
              <p className="text-gray-600 mt-1">
                Computation {id?.slice(0, 8)}... • {computation?.type || 'health_statistics'}
              </p>
            </div>
            
            <div className="flex items-center gap-3">
              <button
                onClick={() => handleExport('json')}
                className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
              >
                <Download className="w-4 h-4" />
                Export JSON
              </button>
              <button
                onClick={() => handleExport('csv')}
                className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors"
              >
                <Download className="w-4 h-4" />
                Export CSV
              </button>
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="border-b border-gray-200 mb-8">
          <nav className="-mb-px flex space-x-8">
            <button
              className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm ${
                activeView === 'overview' 
                  ? 'border-blue-500 text-blue-600' 
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
              onClick={() => setActiveView('overview')}
            >
              Overview
            </button>
            <button
              className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm ${
                activeView === 'charts' 
                  ? 'border-blue-500 text-blue-600' 
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
              onClick={() => setActiveView('charts')}
            >
              <BarChart3 className="w-4 h-4 inline mr-1" />
              Visual Analysis
            </button>
            <button
              className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm ${
                activeView === 'detailed' 
                  ? 'border-blue-500 text-blue-600' 
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
              onClick={() => setActiveView('detailed')}
            >
              Detailed Analysis
            </button>
            <button
              className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm ${
                activeView === 'raw' 
                  ? 'border-blue-500 text-blue-600' 
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
              onClick={() => setActiveView('raw')}
            >
              Raw Data
            </button>
          </nav>
        </div>

        {/* Content */}
        {activeView === 'overview' && (
          <div className="space-y-8">
            {/* Statistics Cards */}
            <div>
              <h2 className="text-xl font-semibold text-gray-900 mb-6">Statistical Summary</h2>
              {renderStatisticsCards()}
            </div>

            {(result.risk_score !== undefined || (result.patient_records && result.patient_records.length > 0)) && (
              <div className="bg-white rounded-lg shadow-sm border p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <AlertCircle className="w-5 h-5 text-red-500" />
                  Risk Summary & Patient Data
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-4">
                  {result.risk_score !== undefined && (
                    <div>
                      <label className="text-sm font-medium text-gray-500">Cohort Risk Score</label>
                      <p className="text-2xl font-bold text-gray-900 mt-1">{Number(result.risk_score).toFixed(0)}</p>
                    </div>
                  )}
                  {result.risk_category && (
                    <div>
                      <label className="text-sm font-medium text-gray-500">Cohort Risk Category</label>
                      <p className="text-lg font-semibold text-gray-900 mt-1 capitalize">{String(result.risk_category)}</p>
                    </div>
                  )}
                  {result.metric_name && (
                    <div>
                      <label className="text-sm font-medium text-gray-500">Metric</label>
                      <p className="text-lg font-semibold text-gray-900 mt-1">{result.metric_name}</p>
                    </div>
                  )}
                </div>

                {Array.isArray(result.risk_recommendations) && result.risk_recommendations.length > 0 && (
                  <div className="mb-4">
                    <label className="text-sm font-medium text-gray-500 block mb-2">Recommendations</label>
                    <ul className="list-disc list-inside text-sm text-gray-700 space-y-1">
                      {result.risk_recommendations.map((rec, idx) => (
                        <li key={idx}>{rec}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {result.patient_records && result.patient_records.length > 0 && (
                  <div className="mt-4">
                    <label className="text-sm font-medium text-gray-500 block mb-2">All Patient Records</label>
                    <div className="overflow-x-auto border border-gray-200 rounded-lg">
                      <table className="min-w-full divide-y divide-gray-200 text-sm">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-4 py-2 text-left font-medium text-gray-600">Patient ID</th>
                            <th className="px-4 py-2 text-left font-medium text-gray-600">Value</th>
                            <th className="px-4 py-2 text-left font-medium text-gray-600">Risk Level</th>
                            <th className="px-4 py-2 text-left font-medium text-gray-600">Threshold Status</th>
                            <th className="px-4 py-2 text-left font-medium text-gray-600">Consequences</th>
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-100">
                          {result.patient_records.slice(0, 200).map((p, idx) => (
                            <tr key={idx} className={p.above_threshold ? 'bg-red-50' : ''}>
                              <td className="px-4 py-2 font-mono text-gray-800">{p.patient_id}</td>
                              <td className="px-4 py-2 text-gray-800">{Number(p.value).toFixed(2)}</td>
                              <td className="px-4 py-2 text-gray-800 capitalize">{p.risk_level || 'unknown'}</td>
                              <td className="px-4 py-2">
                                <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                                  p.above_threshold 
                                    ? 'bg-red-100 text-red-800' 
                                    : 'bg-green-100 text-green-800'
                                }`}>
                                  {p.above_threshold ? 'Above' : 'Below'}
                                </span>
                              </td>
                              <td className="px-4 py-2 text-gray-700 text-xs max-w-xs whitespace-normal">
                                {p.consequences || (p.above_threshold ? 'Above threshold level may increase complication risk; clinical review is recommended.' : '')}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      {result.patient_records.length > 200 && (
                        <p className="text-xs text-gray-500 px-4 py-2">Showing first 200 patients out of {result.patient_records.length}.</p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Computation Info */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <Shield className="w-5 h-5" />
                Computation Information
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                  <label className="text-sm font-medium text-gray-500">Status</label>
                  <p className="text-gray-900 mt-1 capitalize">{result.status || 'completed'}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">Security Method</label>
                  <p className="text-gray-900 mt-1">{computation?.security_method || 'SMPC'}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">Completed At</label>
                  <p className="text-gray-900 mt-1">
                    {result.completed_at ? new Date(result.completed_at).toLocaleString() : 'Recently'}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeView === 'detailed' && (
          <div className="space-y-6">
            {/* Basic Statistical Details */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Statistical Details</h3>
              <div className="space-y-4">
                {result.std_dev && (
                  <div className="flex justify-between items-center py-3 border-b border-gray-100">
                    <span className="text-gray-600">Standard Deviation</span>
                    <span className="font-semibold text-gray-900">{Number(result.std_dev).toFixed(4)}</span>
                  </div>
                )}
                {result.min && (
                  <div className="flex justify-between items-center py-3 border-b border-gray-100">
                    <span className="text-gray-600">Minimum Value</span>
                    <span className="font-semibold text-gray-900">{Number(result.min).toFixed(2)}</span>
                  </div>
                )}
                {result.max && (
                  <div className="flex justify-between items-center py-3 border-b border-gray-100">
                    <span className="text-gray-600">Maximum Value</span>
                    <span className="font-semibold text-gray-900">{Number(result.max).toFixed(2)}</span>
                  </div>
                )}
                {result.sample_size && (
                  <div className="flex justify-between items-center py-3 border-b border-gray-100">
                    <span className="text-gray-600">Sample Size</span>
                    <span className="font-semibold text-gray-900">{result.sample_size}</span>
                  </div>
                )}
                {result.quartiles && (
                  <div className="py-3">
                    <span className="text-gray-600 block mb-2">Quartiles</span>
                    <div className="grid grid-cols-3 gap-4">
                      <div className="text-center">
                        <p className="text-sm text-gray-500">Q1</p>
                        <p className="font-semibold">{Number(result.quartiles[0]).toFixed(2)}</p>
                      </div>
                      <div className="text-center">
                        <p className="text-sm text-gray-500">Q2 (Median)</p>
                        <p className="font-semibold">{Number(result.quartiles[1]).toFixed(2)}</p>
                      </div>
                      <div className="text-center">
                        <p className="text-sm text-gray-500">Q3</p>
                        <p className="font-semibold">{Number(result.quartiles[2]).toFixed(2)}</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {(result.threshold_value !== undefined || (result.patient_records && result.patient_records.length > 0)) && (
              <div className="bg-white rounded-lg shadow-sm border p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Threshold & Patient Distribution</h3>
                <div className="space-y-4">
                  {result.threshold_value !== undefined && (
                    <div className="flex justify-between items-center py-3 border-b border-gray-100">
                      <span className="text-gray-600">Threshold</span>
                      <span className="font-semibold text-gray-900">{result.threshold_value}</span>
                    </div>
                  )}
                  {result.above_threshold_count !== undefined && (
                    <div className="flex justify-between items-center py-3 border-b border-gray-100">
                      <span className="text-gray-600">Patients Above Threshold</span>
                      <span className="font-semibold text-gray-900">{result.above_threshold_count}</span>
                    </div>
                  )}
                  {typeof result.above_threshold_percentage === 'number' && (
                    <div className="flex justify-between items-center py-3 border-b border-gray-100">
                      <span className="text-gray-600">Percentage Above Threshold</span>
                      <span className="font-semibold text-gray-900">{result.above_threshold_percentage.toFixed(1)}%</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Advanced Analysis Results */}
            {(result.correlation_coefficient || result.p_value || result.confidence_interval) && (
              <div className="bg-white rounded-lg shadow-sm border p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Correlation Analysis</h3>
                <div className="space-y-4">
                  {result.p_value && (
                    <div className="flex justify-between items-center py-3 border-b border-gray-100">
                      <span className="text-gray-600">P-Value</span>
                      <span className="font-semibold text-gray-900">{Number(result.p_value).toFixed(6)}</span>
                    </div>
                  )}
                  {result.confidence_interval && (
                    <div className="py-3 border-b border-gray-100">
                      <span className="text-gray-600 block mb-2">95% Confidence Interval</span>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-500">Lower: {Number(result.confidence_interval.lower).toFixed(3)}</span>
                        <span className="text-sm text-gray-500">Upper: {Number(result.confidence_interval.upper).toFixed(3)}</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Machine Learning Results */}
            {(result.feature_importance || result.cross_validation_score || result.model_parameters) && (
              <div className="bg-white rounded-lg shadow-sm border p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Machine Learning Analysis</h3>
                <div className="space-y-4">
                  {result.cross_validation_score && (
                    <div className="flex justify-between items-center py-3 border-b border-gray-100">
                      <span className="text-gray-600">Cross-Validation Score</span>
                      <span className="font-semibold text-gray-900">{(Number(result.cross_validation_score) * 100).toFixed(1)}%</span>
                    </div>
                  )}
                  {result.feature_importance && result.feature_importance.length > 0 && (
                    <div className="py-3">
                      <span className="text-gray-600 block mb-3">Feature Importance</span>
                      <div className="space-y-2">
                        {result.feature_importance.slice(0, 5).map((feature, index) => (
                          <div key={index} className="flex justify-between items-center">
                            <span className="text-sm text-gray-600">Feature {feature.feature_index || index}</span>
                            <div className="flex items-center gap-2">
                              <div className="w-20 bg-gray-200 rounded-full h-2">
                                <div 
                                  className="bg-blue-600 h-2 rounded-full" 
                                  style={{ width: `${(feature.relative_importance || feature.importance || 0) * 100}%` }}
                                ></div>
                              </div>
                              <span className="text-sm font-semibold text-gray-900 w-12">
                                {((feature.relative_importance || feature.importance || 0) * 100).toFixed(1)}%
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Regression Analysis */}
            {(result.coefficients || result.intercept) && (
              <div className="bg-white rounded-lg shadow-sm border p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Regression Analysis</h3>
                <div className="space-y-4">
                  {result.intercept && (
                    <div className="flex justify-between items-center py-3 border-b border-gray-100">
                      <span className="text-gray-600">Intercept</span>
                      <span className="font-semibold text-gray-900">{Number(result.intercept).toFixed(4)}</span>
                    </div>
                  )}
                  {result.coefficients && result.coefficients.length > 0 && (
                    <div className="py-3">
                      <span className="text-gray-600 block mb-3">Coefficients</span>
                      <div className="space-y-2">
                        {result.coefficients.map((coeff, index) => (
                          <div key={index} className="flex justify-between items-center">
                            <span className="text-sm text-gray-600">Variable {index + 1}</span>
                            <span className="text-sm font-semibold text-gray-900">{Number(coeff).toFixed(4)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Healthcare-Specific Results */}
            {(result.cohort_size || result.survival_rates || result.demographics) && (
              <div className="bg-white rounded-lg shadow-sm border p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Healthcare Analysis</h3>
                <div className="space-y-4">
                  {result.cohort_size && (
                    <div className="flex justify-between items-center py-3 border-b border-gray-100">
                      <span className="text-gray-600">Cohort Size</span>
                      <span className="font-semibold text-gray-900">{result.cohort_size}</span>
                    </div>
                  )}
                  {result.survival_rates && (
                    <div className="py-3 border-b border-gray-100">
                      <span className="text-gray-600 block mb-2">Survival Rates</span>
                      <div className="grid grid-cols-3 gap-4">
                        {result.survival_rates['1_year'] && (
                          <div className="text-center">
                            <p className="text-sm text-gray-500">1 Year</p>
                            <p className="font-semibold">{(Number(result.survival_rates['1_year']) * 100).toFixed(1)}%</p>
                          </div>
                        )}
                        {result.survival_rates['3_year'] && (
                          <div className="text-center">
                            <p className="text-sm text-gray-500">3 Year</p>
                            <p className="font-semibold">{(Number(result.survival_rates['3_year']) * 100).toFixed(1)}%</p>
                          </div>
                        )}
                        {result.survival_rates['5_year'] && (
                          <div className="text-center">
                            <p className="text-sm text-gray-500">5 Year</p>
                            <p className="font-semibold">{(Number(result.survival_rates['5_year']) * 100).toFixed(1)}%</p>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                  {result.demographics && (
                    <div className="py-3">
                      <span className="text-gray-600 block mb-2">Demographics</span>
                      <div className="space-y-2">
                        {result.demographics.average_age && (
                          <div className="flex justify-between items-center">
                            <span className="text-sm text-gray-600">Average Age</span>
                            <span className="text-sm font-semibold text-gray-900">{Number(result.demographics.average_age).toFixed(1)} years</span>
                          </div>
                        )}
                        {result.demographics.gender_distribution && (
                          <div className="flex justify-between items-center">
                            <span className="text-sm text-gray-600">Gender Distribution</span>
                            <span className="text-sm font-semibold text-gray-900">
                              M: {(Number(result.demographics.gender_distribution.male || 0) * 100).toFixed(1)}% / 
                              F: {(Number(result.demographics.gender_distribution.female || 0) * 100).toFixed(1)}%
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {activeView === 'charts' && (
          <div className="space-y-8">
            {/* Chart Controls */}
            <div className="bg-white rounded-lg shadow-sm border p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                  <BarChart3 className="w-5 h-5" />
                  Visual Data Analysis
                </h3>
                <button
                  onClick={() => setShowCharts(!showCharts)}
                  className="text-sm text-blue-600 hover:text-blue-700"
                >
                  {showCharts ? 'Hide Charts' : 'Show Charts'}
                </button>
              </div>
              <p className="text-gray-600 text-sm">
                Interactive visualizations of your secure computation results with enhanced analytics.
              </p>
            </div>

            {showCharts && (
              <div className="space-y-8">
                <SecureAnalysisChartsSection result={result} />

                {/* Correlation Visualization */}
                {generateCorrelationChart() && (
                  <div className="bg-white rounded-lg shadow-sm border p-6">
                    <h4 className="text-lg font-medium text-gray-900 mb-4 flex items-center gap-2">
                      <TrendingUp className="w-5 h-5 text-purple-600" />
                      Correlation Analysis
                    </h4>
                    <div className="h-80">
                      <Doughnut data={generateCorrelationChart()} options={{
                        ...chartOptions,
                        scales: undefined,
                        cutout: '60%'
                      }} />
                    </div>
                    <div className="mt-4 text-center">
                      <p className="text-2xl font-bold text-gray-900">
                        {Number(result.correlation_coefficient).toFixed(3)}
                      </p>
                      <p className="text-sm text-gray-500">
                        Correlation Coefficient
                      </p>
                      {result.interpretation && (
                        <p className="text-sm text-blue-600 mt-1">
                          {result.interpretation}
                        </p>
                      )}
                    </div>
                  </div>
                )}

                {/* Time Series Chart */}
                {generateTimeSeriesChart() && (
                  <div className="bg-white rounded-lg shadow-sm border p-6">
                    <h4 className="text-lg font-medium text-gray-900 mb-4 flex items-center gap-2">
                      <LineChart className="w-5 h-5 text-indigo-600" />
                      Temporal Analysis
                    </h4>
                    <div className="h-80">
                      <Line data={generateTimeSeriesChart()} options={{
                        ...chartOptions,
                        interaction: {
                          intersect: false,
                          mode: 'index'
                        },
                        plugins: {
                          ...chartOptions.plugins,
                          tooltip: {
                            ...chartOptions.plugins.tooltip,
                            callbacks: {
                              title: (context) => {
                                return `Time: ${context[0].label}`;
                              },
                              label: (context) => {
                                return `Value: ${context.parsed.y.toFixed(2)}`;
                              }
                            }
                          }
                        }
                      }} />
                    </div>
                    <p className="text-sm text-gray-500 mt-3">
                      Temporal trends and patterns in the computation results.
                    </p>
                  </div>
                )}

                {/* Correlation, temporal, and feature importance visualizations remain below */}

                {/* Feature Importance Chart */}
                {result.feature_importance && result.feature_importance.length > 0 && (
                  <div className="bg-white rounded-lg shadow-sm border p-6 lg:col-span-2">
                    <h4 className="text-lg font-medium text-gray-900 mb-4 flex items-center gap-2">
                      <Activity className="w-5 h-5 text-orange-600" />
                      Feature Importance Analysis
                    </h4>
                    <div className="h-80">
                      <Bar data={{
                        labels: result.feature_importance.slice(0, 10).map((_, idx) => `Feature ${idx + 1}`),
                        datasets: [{
                          label: 'Importance Score',
                          data: result.feature_importance.slice(0, 10).map(f => f.relative_importance || f.importance || 0),
                          backgroundColor: 'rgba(249, 115, 22, 0.8)',
                          borderColor: 'rgba(249, 115, 22, 1)',
                          borderWidth: 2,
                          borderRadius: 8
                        }]
                      }} options={{
                        ...chartOptions,
                        indexAxis: 'y',
                        plugins: {
                          ...chartOptions.plugins,
                          tooltip: {
                            ...chartOptions.plugins.tooltip,
                            callbacks: {
                              label: (context) => {
                                return `Importance: ${(context.parsed.x * 100).toFixed(1)}%`;
                              }
                            }
                          }
                        }
                      }} />
                    </div>
                    <p className="text-sm text-gray-500 mt-3">
                      Relative importance of features in the machine learning model.
                    </p>
                  </div>
                )}

                {/* No Charts Available Message */}
                {!generateBarChart() && !generatePieChart() && !generateCorrelationChart() && !generateTimeSeriesChart() && !generateThresholdDistributionChart() && !generateRiskLevelChart() && !result.feature_importance && (
                  <div className="lg:col-span-2 text-center py-12 text-gray-500">
                    <BarChart3 className="w-16 h-16 mx-auto mb-4 text-gray-300" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">No Visual Data Available</h3>
                    <p className="text-gray-600">
                      This computation doesn't have sufficient data for visual analysis.
                      Try switching to the Overview or Detailed Analysis tabs.
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {activeView === 'raw' && (
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Eye className="w-5 h-5" />
              Raw Results Data
            </h3>
            <div className="bg-gray-50 rounded-lg p-4 overflow-auto max-h-96">
              <pre className="text-sm text-gray-800 whitespace-pre-wrap">
                {JSON.stringify(result, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
