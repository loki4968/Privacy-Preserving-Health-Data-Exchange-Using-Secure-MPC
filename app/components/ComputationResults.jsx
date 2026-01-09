import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { toast } from 'react-hot-toast';

const ComputationResults = ({ computationId }) => {
  const [result, setResult] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [exportFormat, setExportFormat] = useState('json');
  const [isExporting, setIsExporting] = useState(false);
  const [showRawResult, setShowRawResult] = useState(false);
  const [visualInsights, setVisualInsights] = useState(null);
  const { user } = useAuth();
  const token = user?.token;

  useEffect(() => {
    if (computationId) {
      fetchResult();
    }
  }, [computationId]);

  const fetchResult = async () => {
    if (!token) {
      toast.error('Authentication required. Please log in.');
      setIsLoading(false);
      return;
    }

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/secure-computations/computations/${computationId}/result`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch computation result');
      }

      const data = await response.json();
      
      // Debug: Log the actual response data
      console.log('Computation result data:', data);
      console.log('Status:', data.status);
      console.log('Result object:', data.result);
      
      // Check if computation is still in progress or has error
      if (data.status && data.status !== 'completed') {
        if (data.status === 'error') {
          toast.error(`Computation error: ${data.error_message || 'Unknown error'}`);
        } else if (data.status === 'ready_to_compute') {
          toast.success('All data submitted! Ready to compute results.');
        } else {
          toast(`Computation status: ${data.status_message || data.status}`);
          // If still processing, set up polling
          if (data.status === 'processing' || data.status === 'computing' || data.status === 'initialized' || data.status === 'waiting_for_data') {
            setTimeout(fetchResult, 5000); // Poll every 5 seconds
          }
        }
      }
      
      // Handle result structure - it might be in data.result or directly in data
      if (data.status === 'completed' && data.result) {
        // Merge result data into main data object for easier access
        const mergedResult = {
          ...data,
          ...data.result, // Spread result properties to top level
          result: data.result, // Keep original result structure
          formatted: data.formatted_result || data.formatted || data.result?.formatted_result || data.result?.formatted // Include formatted result if available
        };
        setResult(mergedResult);
        setVisualInsights(extractVisualInsights(mergedResult));
      } else {
      setResult(data);
        setVisualInsights(extractVisualInsights(data));
      }
    } catch (error) {
      toast.error(error.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleExport = async (format) => {
    if (!token) {
      toast.error('Authentication required. Please log in.');
      return;
    }

    setIsExporting(true);
    try {
      // Use the export endpoint
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/secure-computations/computations/${computationId}/export?format=${format}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error(`Failed to export computation result: ${response.statusText}`);
      }

      // Get the filename from the Content-Disposition header if available
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = `computation_${computationId}.${format}`;
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename=([^;]+)/);
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1].replace(/"/g, '');
        }
      }

      // Create a blob from the response
      const blob = await response.blob();
      
      // Create a download link and trigger the download
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      
      // Clean up
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      toast.success(`Exported computation result as ${format.toUpperCase()}`);
    } catch (error) {
      toast.error(error.message);
    } finally {
      setIsExporting(false);
    }
  };

  const extractMatchingPatients = (resultData) => {
    if (!resultData) return [];
    const nested = resultData.result || resultData;
    const patients = [];

    if (Array.isArray(nested?.patients_above_threshold)) {
      patients.push(...nested.patients_above_threshold);
    }

    if (nested?.operations) {
      Object.values(nested.operations).forEach((op) => {
        if (op && typeof op === 'object') {
          if (Array.isArray(op.patients_above_threshold)) {
            patients.push(...op.patients_above_threshold);
          }
          if (Array.isArray(op.matching_patients)) {
            patients.push(...op.matching_patients);
          }
        }
      });
    }

    return patients;
  };

  const extractVisualInsights = (resultData) => {
    const patients = extractMatchingPatients(resultData);
    if (!patients || patients.length === 0) return null;

    const normalize = (value) => (value !== undefined && value !== null ? String(value) : 'Unknown');

    const stageCounts = {};
    const treatmentCounts = {};
    const orgCounts = {};

    patients.forEach((patient) => {
      const stage = normalize(patient.Stage || patient.stage || patient.cancer_stage);
      const treatment = normalize(patient.Treatment || patient.treatment || patient.Therapy);
      const org = normalize(patient.org_id || patient.organization || patient.org);

      if (stage) stageCounts[stage] = (stageCounts[stage] || 0) + 1;
      if (treatment) treatmentCounts[treatment] = (treatmentCounts[treatment] || 0) + 1;
      if (org) orgCounts[org] = (orgCounts[org] || 0) + 1;
    });

    return {
      totalPatients: patients.length,
      stageCounts,
      treatmentCounts,
      orgCounts,
    };
  };

  const renderDistributionBar = (counts) => {
    if (!counts || Object.keys(counts).length === 0) {
      return <p className="text-sm text-gray-500">Not enough data to build visualization.</p>;
    }
    const maxVal = Math.max(...Object.values(counts));

    return (
      <div className="space-y-3">
        {Object.entries(counts).map(([label, value]) => (
          <div key={label}>
            <div className="flex justify-between text-xs text-gray-600 mb-1">
              <span>{label}</span>
              <span>{value}</span>
            </div>
            <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full"
                style={{ width: `${(value / maxVal) * 100}%` }}
              ></div>
            </div>
          </div>
        ))}
      </div>
    );
  };

  const renderVisualAnalyticsSection = () => {
    if (!visualInsights) return null;

    return (
      <div className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">Visual Analytics</h3>
          <p className="text-sm text-gray-500">{visualInsights.totalPatients} records analyzed</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <h4 className="text-sm font-semibold text-gray-700 mb-2">Cancer Stage Distribution</h4>
            {renderDistributionBar(visualInsights.stageCounts)}
          </div>
          <div>
            <h4 className="text-sm font-semibold text-gray-700 mb-2">Treatment Types</h4>
            {renderDistributionBar(visualInsights.treatmentCounts)}
          </div>
          <div>
            <h4 className="text-sm font-semibold text-gray-700 mb-2">Organizations</h4>
            {renderDistributionBar(visualInsights.orgCounts)}
          </div>
        </div>
      </div>
    );
  };



  const renderStatisticsCards = () => {
    // Check both top-level and nested result structure
    const resultData = result?.result || result;
    const spec = result?.spec || result?.result?.spec;
    const researchQuestion = spec?.research_question || result?.research_question;
    const variablesUsed = result?.variables_used || result?.result?.variables_used || spec?.variables;
    const analysisType = result?.analysis_type || spec?.analysis_type;
    const formatted = result?.formatted;
    
    // If we have LLM-formatted results, use those for display
    if (formatted && formatted.sections && formatted.sections.length > 0) {
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        {formatted.title && (
          <div>
            <h3 className="text-lg font-semibold text-gray-900">{formatted.title}</h3>
            {formatted.summary && <p className="text-sm text-gray-600">{formatted.summary}</p>}
          </div>
        )}
        <div className="flex items-center gap-3">
          {visualInsights?.totalPatients ? (
            <span className="text-sm text-gray-600">
              {visualInsights.totalPatients} patient records analyzed
            </span>
          ) : null}
          <button
            onClick={() => setShowRawResult((prev) => !prev)}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            {showRawResult ? 'Hide Raw Results' : 'Show Raw Results'}
          </button>
        </div>
      </div>

      {showRawResult && (
        <div className="bg-gray-900 rounded-lg p-4 text-gray-100 text-sm overflow-auto">
          <pre className="whitespace-pre-wrap">{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}

      {renderVisualAnalyticsSection()}
          
          {/* Research Question Context */}
          {researchQuestion && (
            <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded">
              <h4 className="text-sm font-semibold text-blue-900 mb-1">Research Question</h4>
              <p className="text-sm text-blue-800">{researchQuestion}</p>
            </div>
          )}
          
          {/* Variables Used */}
          {variablesUsed && variablesUsed.length > 0 && (
            <div className="bg-gray-50 p-3 rounded-lg">
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Variables Analyzed</h4>
              <div className="flex flex-wrap gap-2">
                {variablesUsed.map((varName, idx) => (
                  <span key={idx} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-200 text-gray-800">
                    {typeof varName === 'string' ? varName : varName.name || varName.id || 'Unknown'}
                  </span>
                ))}
              </div>
            </div>
          )}
          
          {/* Formatted Sections */}
          {formatted.sections.map((section, idx) => {
            // Handle patient_list with new content structure (headers/rows) or legacy data array
            if (section.type === 'patient_list') {
              const hasContentStructure = section.content && section.content.headers && section.content.rows;
              const hasDataArray = Array.isArray(section.data);
              
              if (hasContentStructure) {
                // New structure with headers and rows
                return (
                  <div key={idx} className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm">
                    <h4 className="text-lg font-semibold text-gray-900 mb-4">{section.title}</h4>
                    {section.data?.total_count && (
                      <p className="text-sm text-gray-600 mb-3">Total: {section.data.total_count} patients</p>
                    )}
                    <div className="bg-gray-50 rounded-lg border border-gray-200 max-h-96 overflow-y-auto">
                      <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-100">
                          <tr>
                            {section.content.headers.map((header, headerIdx) => (
                              <th key={headerIdx} className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                                {header}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                          {section.content.rows.map((row, rowIdx) => (
                            <tr key={rowIdx} className="hover:bg-gray-50">
                              {row.map((cell, cellIdx) => (
                                <td key={cellIdx} className="px-4 py-3 text-sm text-gray-900">
                                  {cell}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                );
              } else if (hasDataArray) {
                // Legacy structure with data array
                return (
                  <div key={idx} className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm">
                    <h4 className="text-lg font-semibold text-gray-900 mb-4">{section.title}</h4>
                    <div className="bg-gray-50 rounded-lg border border-gray-200 max-h-96 overflow-y-auto">
                      <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-100">
                          <tr>
                            {(section.columns || ['patient_id', 'value', 'risk_level']).map((col, colIdx) => (
                              <th key={colIdx} className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                                {col.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                          {section.data.map((patient, pIdx) => (
                            <tr key={pIdx} className="hover:bg-gray-50">
                              {(section.columns || ['patient_id', 'value', 'risk_level']).map((col, colIdx) => (
                                <td key={colIdx} className="px-4 py-3 text-sm text-gray-900">
                                  {patient[col] !== undefined ? (
                                    typeof patient[col] === 'number' ? Number(patient[col]).toFixed(2) : String(patient[col])
                                  ) : 'N/A'}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                );
              }
            } else if (section.type === 'statistics') {
              return (
                <div key={idx} className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm">
                  <h4 className="text-lg font-semibold text-gray-900 mb-4">{section.title}</h4>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {Object.entries(section.data || {}).map(([key, value]) => (
                      <div key={key} className="bg-blue-50 p-4 rounded-lg">
                        <p className="text-xs font-medium text-blue-700 mb-1">
                          {key.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                        </p>
                        <p className="text-2xl font-bold text-blue-900">
                          {typeof value === 'number' ? value.toFixed(2) : String(value)}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              );
            } else {
              return (
                <div key={idx} className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm">
                  <h4 className="text-lg font-semibold text-gray-900 mb-4">{section.title}</h4>
                  <pre className="text-xs text-gray-600 overflow-auto bg-gray-50 p-3 rounded">
                    {JSON.stringify(section.data, null, 2)}
                  </pre>
                </div>
              );
            }
          })}
          
          {/* Key Insights */}
          {formatted.key_insights && formatted.key_insights.length > 0 && (
            <div className="bg-green-50 border-l-4 border-green-500 p-4 rounded">
              <h4 className="text-sm font-semibold text-green-900 mb-2">Key Insights</h4>
              <ul className="list-disc list-inside space-y-1">
                {formatted.key_insights.map((insight, idx) => (
                  <li key={idx} className="text-sm text-green-800">{insight}</li>
                ))}
              </ul>
            </div>
          )}
          
          {/* Recommendations */}
          {/* Enhanced Recommendations with Priority */}
          {formatted.recommendations && formatted.recommendations.length > 0 && (
            <div className="bg-gradient-to-r from-yellow-50 to-orange-50 border-l-4 border-yellow-500 p-6 rounded-lg shadow-sm">
              <h4 className="text-lg font-semibold text-yellow-900 mb-4 flex items-center gap-2">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Clinical Recommendations
              </h4>
              <div className="space-y-3">
                {formatted.recommendations.map((rec, idx) => {
                  // Handle both old format (string) and new format (object)
                  const isObject = typeof rec === 'object' && rec !== null;
                  const priority = isObject ? rec.priority : 'medium';
                  const category = isObject ? rec.category : 'clinical';
                  const text = isObject ? rec.text : rec;
                  
                  const priorityColors = {
                    high: 'bg-red-100 border-red-300 text-red-900',
                    medium: 'bg-yellow-100 border-yellow-300 text-yellow-900',
                    low: 'bg-blue-100 border-blue-300 text-blue-900'
                  };
                  
                  const categoryIcons = {
                    clinical: '🏥',
                    monitoring: '📊',
                    treatment: '💊',
                    prevention: '🛡️',
                    research: '🔬'
                  };
                  
                  return (
                    <div
                      key={idx}
                      className={`border-l-4 p-4 rounded-lg ${priorityColors[priority] || priorityColors.medium}`}
                    >
                      <div className="flex items-start gap-3">
                        <span className="text-xl">{categoryIcons[category] || '📋'}</span>
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className={`text-xs font-semibold px-2 py-1 rounded ${
                              priority === 'high' ? 'bg-red-200 text-red-800' :
                              priority === 'medium' ? 'bg-yellow-200 text-yellow-800' :
                              'bg-blue-200 text-blue-800'
                            }`}>
                              {priority.toUpperCase()}
                            </span>
                            <span className="text-xs text-gray-600 capitalize">{category}</span>
                          </div>
                          <p className="text-sm leading-relaxed">{text}</p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
          
          {/* Clinical Significance */}
          {formatted.clinical_significance && (
            <div className="bg-indigo-50 border-l-4 border-indigo-500 p-4 rounded">
              <h4 className="text-sm font-semibold text-indigo-900 mb-2">Clinical Significance</h4>
              <p className="text-sm text-indigo-800 leading-relaxed">{formatted.clinical_significance}</p>
            </div>
          )}
          
          {/* Next Steps */}
          {formatted.next_steps && formatted.next_steps.length > 0 && (
            <div className="bg-green-50 border-l-4 border-green-500 p-4 rounded">
              <h4 className="text-sm font-semibold text-green-900 mb-2">Suggested Next Steps</h4>
              <ul className="list-disc list-inside space-y-1">
                {formatted.next_steps.map((step, idx) => (
                  <li key={idx} className="text-sm text-green-800">{step}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      );
    }
    
    // Check for spec-based results
    if (resultData?.operations) {
      return (
        <div className="space-y-6">
          {/* Research Question Context */}
          {researchQuestion && (
            <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded">
              <h4 className="text-sm font-semibold text-blue-900 mb-1">Research Question</h4>
              <p className="text-sm text-blue-800">{researchQuestion}</p>
            </div>
          )}
          
          {/* Variables Used */}
          {variablesUsed && variablesUsed.length > 0 && (
            <div className="bg-gray-50 p-3 rounded-lg">
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Variables Analyzed</h4>
              <div className="flex flex-wrap gap-2">
                {variablesUsed.map((varName, idx) => (
                  <span key={idx} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-200 text-gray-800">
                    {typeof varName === 'string' ? varName : varName.name || varName.id || 'Unknown'}
                  </span>
                ))}
              </div>
            </div>
          )}
          
          {/* Analysis Results */}
          <div>
            <h4 className="font-medium text-gray-900 mb-4">
              {analysisType ? `Analysis Results (${analysisType.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())})` : 'Analysis Results'}
            </h4>
            {Object.entries(resultData.operations).map(([opId, opResult]) => {
              const opType = opResult?.type || opId;
              const opValue = opResult?.value;
              const opCount = opResult?.count;
              
              return (
                <div key={opId} className="bg-white border border-gray-200 rounded-lg p-5 mb-4 shadow-sm">
                  <div className="flex items-center justify-between mb-3">
                    <h5 className="text-sm font-semibold text-gray-800">
                      Operation: {opId.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </h5>
                    <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                      {opType}
                    </span>
                  </div>
                  
                  {opValue !== undefined && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="bg-blue-50 p-4 rounded-lg">
                        <p className="text-xs font-medium text-blue-700 mb-1">Result Value</p>
                        <p className="text-2xl font-bold text-blue-900">
                          {typeof opValue === 'number' ? opValue.toFixed(2) : String(opValue)}
                        </p>
                      </div>
                      {opCount !== undefined && (
                        <div className="bg-purple-50 p-4 rounded-lg">
                          <p className="text-xs font-medium text-purple-700 mb-1">Data Points</p>
                          <p className="text-2xl font-bold text-purple-900">{opCount}</p>
                        </div>
                      )}
                    </div>
                  )}
                  
                  {/* Show full result if it's more complex */}
                  {opValue === undefined && (
                    <pre className="text-xs text-gray-600 overflow-auto bg-gray-50 p-3 rounded">
                      {JSON.stringify(opResult, null, 2)}
                    </pre>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      );
    }
    
    // Legacy format - show with context if available
    if (!resultData || (!resultData.mean && !resultData.sum && !resultData.count && !resultData.variance && !resultData.average)) {
      return <div className="text-center py-10 text-gray-500">No statistical data available</div>;
    }

    return (
      <div className="space-y-6">
        {/* Research Question Context */}
        {researchQuestion && (
          <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded">
            <h4 className="text-sm font-semibold text-blue-900 mb-1">Research Question</h4>
            <p className="text-sm text-blue-800">{researchQuestion}</p>
          </div>
        )}
        
        {/* Variables Used */}
        {variablesUsed && variablesUsed.length > 0 && (
          <div className="bg-gray-50 p-3 rounded-lg">
            <h4 className="text-sm font-semibold text-gray-700 mb-2">Variables Analyzed</h4>
            <div className="flex flex-wrap gap-2">
              {variablesUsed.map((varName, idx) => (
                <span key={idx} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-200 text-gray-800">
                  {typeof varName === 'string' ? varName : varName.name || varName.id || 'Unknown'}
                </span>
              ))}
            </div>
          </div>
        )}
        
        {/* Statistics Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {(resultData.mean || resultData.average) && (
            <div className="bg-blue-50 p-4 rounded-lg">
              <p className="text-sm font-medium text-blue-900">Average</p>
              <p className="text-2xl font-bold text-blue-700">
                {Number(resultData.mean || resultData.average).toFixed(2)}
              </p>
              {variablesUsed && variablesUsed.length > 0 && (
                <p className="text-xs text-blue-600 mt-1">
                  of {variablesUsed.map(v => typeof v === 'string' ? v : v.name || v.id).join(', ')}
                </p>
              )}
            </div>
          )}
          {resultData.sum && (
            <div className="bg-green-50 p-4 rounded-lg">
              <p className="text-sm font-medium text-green-900">Sum</p>
              <p className="text-2xl font-bold text-green-700">{Number(resultData.sum).toFixed(2)}</p>
            </div>
          )}
          {resultData.count && (
          <div className="bg-purple-50 p-4 rounded-lg">
            <p className="text-sm font-medium text-purple-900">Count</p>
              <p className="text-2xl font-bold text-purple-700">{resultData.count}</p>
              <p className="text-xs text-purple-600 mt-1">data points</p>
          </div>
        )}
          {resultData.variance && (
          <div className="bg-orange-50 p-4 rounded-lg">
            <p className="text-sm font-medium text-orange-900">Variance</p>
              <p className="text-2xl font-bold text-orange-700">{Number(resultData.variance).toFixed(2)}</p>
            </div>
          )}
        </div>
        
        {/* Threshold Analysis */}
        {resultData.threshold_value !== undefined && (
          <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4 rounded-lg mt-4">
            <h4 className="text-sm font-semibold text-yellow-900 mb-3">Threshold Analysis</h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              <div>
                <p className="text-xs text-yellow-700 mb-1">Threshold Value</p>
                <p className="text-lg font-bold text-yellow-900">{resultData.threshold_value}</p>
              </div>
              {resultData.above_threshold_count !== undefined && (
                <div>
                  <p className="text-xs text-yellow-700 mb-1">Above Threshold</p>
                  <p className="text-lg font-bold text-yellow-900">
                    {resultData.above_threshold_count} {resultData.above_threshold_count === 1 ? 'reading' : 'readings'}
                  </p>
                </div>
              )}
              {resultData.above_threshold_percentage !== undefined && (
                <div>
                  <p className="text-xs text-yellow-700 mb-1">Percentage</p>
                  <p className="text-lg font-bold text-yellow-900">
                    {Number(resultData.above_threshold_percentage).toFixed(1)}%
                  </p>
                </div>
              )}
            </div>
            
            {/* Patients Above Threshold List */}
            {resultData.patients_above_threshold && Array.isArray(resultData.patients_above_threshold) && resultData.patients_above_threshold.length > 0 && (
              <div className="mt-4">
                <h5 className="text-sm font-semibold text-yellow-900 mb-2">
                  Patients/Readings Above Threshold ({resultData.patients_above_threshold.length})
                </h5>
                <div className="bg-white rounded-lg border border-yellow-200 max-h-64 overflow-y-auto">
                  <table className="min-w-full divide-y divide-yellow-200">
                    <thead className="bg-yellow-100">
                      <tr>
                        <th className="px-3 py-2 text-left text-xs font-medium text-yellow-800">Patient ID</th>
                        <th className="px-3 py-2 text-left text-xs font-medium text-yellow-800">Value</th>
                        <th className="px-3 py-2 text-left text-xs font-medium text-yellow-800">Risk Level</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-yellow-100">
                      {resultData.patients_above_threshold.map((patient, idx) => (
                        <tr key={idx} className="hover:bg-yellow-50">
                          <td className="px-3 py-2 text-sm text-gray-900">
                            {patient.patient_id || patient.patientId || 'N/A'}
                          </td>
                          <td className="px-3 py-2 text-sm font-medium text-yellow-900">
                            {patient.value !== undefined ? Number(patient.value).toFixed(2) : 'N/A'}
                          </td>
                          <td className="px-3 py-2 text-sm">
                            <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${
                              patient.risk_level === 'very_high' ? 'bg-red-100 text-red-800' :
                              patient.risk_level === 'high' ? 'bg-orange-100 text-orange-800' :
                              patient.risk_level === 'normal' ? 'bg-green-100 text-green-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {patient.risk_level || 'N/A'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    );
  };


  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="text-center text-gray-500 py-8">
        No results available
      </div>
    );
  }

  return (
    <div className="bg-white shadow sm:rounded-lg p-6">
      <div className="mb-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">
          Computation Results
        </h3>
        
        <div className="flex justify-between items-center mb-4">
          <div className="flex flex-wrap gap-2 mb-2">
            <button
              onClick={() => handleExport('json')}
              disabled={isExporting}
              className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {isExporting ? 'Exporting...' : 'Export JSON'}
            </button>
            <button
              onClick={() => handleExport('csv')}
              disabled={isExporting}
              className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
            >
              {isExporting ? 'Exporting...' : 'Export CSV'}
            </button>
          </div>
        </div>

        <div className="space-y-6">
          {/* Statistics Cards */}
          {renderStatisticsCards()}
        </div>
      </div>

      <div className="mt-8">
        <h4 className="text-md font-medium text-gray-900 mb-4">
          Computation Details
        </h4>
        <div className="bg-gray-50 rounded-lg p-4">
          <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <dt className="text-sm font-medium text-gray-500">Type</dt>
              <dd className="mt-1 text-sm text-gray-900">{result.type || 'N/A'}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">Status</dt>
              <dd className="mt-1 text-sm text-gray-900">{result.status || 'Unknown'}</dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">Created At</dt>
              <dd className="mt-1 text-sm text-gray-900">
                {result.created_at ? new Date(result.created_at).toLocaleString() : 'N/A'}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500">Completed At</dt>
              <dd className="mt-1 text-sm text-gray-900">
                {result.completed_at ? new Date(result.completed_at).toLocaleString() : 'Pending'}
              </dd>
            </div>
            {result.participants_count !== undefined && (
              <div>
                <dt className="text-sm font-medium text-gray-500">Participants</dt>
                <dd className="mt-1 text-sm text-gray-900">{result.participants_count}</dd>
              </div>
            )}
            {result.submissions_count !== undefined && (
              <div>
                <dt className="text-sm font-medium text-gray-500">Submissions</dt>
                <dd className="mt-1 text-sm text-gray-900">{result.submissions_count}</dd>
              </div>
            )}
          </dl>
        </div>
      </div>
    </div>
  );
};

export default ComputationResults;