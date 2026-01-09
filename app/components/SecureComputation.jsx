import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { toast } from 'react-hot-toast';
import ComputationResults from './ComputationResults';
import SecureEncryption from './SecureEncryption';

const SecureComputation = () => {
  const [computations, setComputations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedComputation, setSelectedComputation] = useState(null);
  const [showEncryption, setShowEncryption] = useState(false);
  const [selectedComputationForEncryption, setSelectedComputationForEncryption] = useState(null);
  const [encryptedData, setEncryptedData] = useState(null);
  const [newComputation, setNewComputation] = useState({
    computation_type: '',
    data_points: [{ value: '' }],
    security_method: 'standard'
  });
  const { user } = useAuth();
  const token = user?.token;

  useEffect(() => {
    fetchComputations();
  }, []);

  const fetchComputations = async () => {
    setLoading(true);
    try {
      // Try enhanced endpoint first, fallback to legacy
      let response;
      try {
        response = await fetch('http://localhost:8000/secure-computations/enhanced/computations', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (!response.ok) {
          throw new Error('Enhanced endpoint failed');
        }
      } catch (enhancedError) {
        console.warn('Enhanced endpoint failed, trying legacy endpoint:', enhancedError);
        response = await fetch('http://localhost:8000/secure-computations/computations', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (!response.ok) {
          throw new Error('Failed to fetch computations');
        }
      }

      const data = await response.json();

      // Sort computations by created_at (newest first)
      const sortedData = data.sort((a, b) => {
        return new Date(b.created_at) - new Date(a.created_at);
      });

      setComputations(sortedData);
    } catch (error) {
      toast.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleInitiateComputation = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await fetch('http://localhost:8000/secure-computation', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          computation_type: newComputation.computation_type,
          security_method: newComputation.security_method,
          min_participants: newComputation.security_method === 'hybrid' ? 3 : undefined,
          threshold: newComputation.security_method === 'hybrid' ? 2 : undefined,
          data_points: newComputation.data_points
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to initiate computation');
      }

      toast.success('Computation initiated successfully');
      setNewComputation({
        computation_type: '',
        data_points: [{ value: '' }],
        security_method: 'standard'
      });
      fetchComputations();
    } catch (error) {
      toast.error(error.message);
    } finally {
      setLoading(false);
    }
  };
  
  const handleClientEncryption = (computationId) => {
    setSelectedComputationForEncryption(computationId);
    setShowEncryption(true);
  };
  
  const handleEncryptionComplete = (encryptedResult) => {
    setEncryptedData(encryptedResult);
    toast('Data encrypted successfully. You can now submit it.');
  };

  const handleAddDataPoint = () => {
    setNewComputation(prev => ({
      ...prev,
      data_points: [...prev.data_points, { value: 0, type: 'numeric' }]
    }));
  };

  const handleDataPointChange = (index, field, value) => {
    setNewComputation(prev => ({
      ...prev,
      data_points: prev.data_points.map((point, i) => 
        i === index ? { ...point, [field]: value } : point
      )
    }));
  };

  const handleRemoveDataPoint = (index) => {
    setNewComputation(prev => ({
      ...prev,
      data_points: prev.data_points.filter((_, i) => i !== index)
    }));
  };

  const handleViewResults = (computationId) => {
    setSelectedComputation(computationId);
  };

  const handleVerifyComputation = async (computationId) => {
    setIsLoading(true);
    try {
      const response = await fetch(`http://localhost:8000/secure-computations/computations/${computationId}/verify`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to verify computation');
      }

      if (data.verified) {
        toast.success('Computation verified successfully');
      } else {
        toast.error(`Verification failed: ${data.error || 'Unknown error'}`);
      }
      
      fetchComputations();
    } catch (error) {
      toast.error(error.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleTriggerComputation = async (computationId) => {
    setIsLoading(true);
    try {
      const response = await fetch(`http://localhost:8000/secure-computations/computations/${computationId}/compute`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to trigger computation');
      }

      toast.success(data.message || 'Computation triggered successfully');
      fetchComputations();
    } catch (error) {
      toast.error(error.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        <div className="bg-white shadow sm:rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h2 className="text-2xl font-bold text-gray-900 mb-6">
              Secure Computations
            </h2>

            {/* New Computation Form */}
            <form onSubmit={handleInitiateComputation} className="space-y-6 mb-8">
              <div>
                <label htmlFor="computation_type" className="block text-sm font-medium text-gray-700">
                  Computation Type
                </label>
                <select
                  id="computation_type"
                  name="computation_type"
                  required
                  value={newComputation.computation_type}
                  onChange={(e) => setNewComputation(prev => ({
                    ...prev,
                    computation_type: e.target.value
                  }))}
                  className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                >
                  <option value="">Select a type</option>
                  <option value="statistics">Statistical Analysis</option>
                  <option value="aggregation">Data Aggregation</option>
                  <option value="comparison">Data Comparison</option>
                </select>
              </div>

              <div>
                <label htmlFor="security_method" className="block text-sm font-medium text-gray-700">
                  Security Method
                </label>
                <select
                  id="security_method"
                  name="security_method"
                  required
                  value={newComputation.security_method}
                  onChange={(e) => setNewComputation(prev => ({
                    ...prev,
                    security_method: e.target.value
                  }))}
                  className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                >
                  <option value="standard">Standard</option>
                  <option value="homomorphic">Homomorphic Encryption</option>
                  <option value="hybrid">Hybrid (SMPC + Homomorphic)</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Data Points
                </label>
                {newComputation.data_points.map((point, index) => (
                  <div key={index} className="flex items-center space-x-4 mb-2">
                    <input
                      type="number"
                      value={point.value}
                      onChange={(e) => handleDataPointChange(index, 'value', parseFloat(e.target.value))}
                      className="block w-32 border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                      placeholder="Value"
                    />
                    <select
                      value={point.type}
                      onChange={(e) => handleDataPointChange(index, 'type', e.target.value)}
                      className="block w-32 border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                    >
                      <option value="numeric">Numeric</option>
                      <option value="categorical">Categorical</option>
                    </select>
                    <button
                      type="button"
                      onClick={() => handleRemoveDataPoint(index)}
                      className="text-red-600 hover:text-red-800"
                    >
                      Remove
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  onClick={handleAddDataPoint}
                  className="mt-2 inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-indigo-700 bg-indigo-100 hover:bg-indigo-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                  Add Data Point
                </button>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
              >
                {loading ? 'Initiating...' : 'Initiate Computation'}
              </button>
            </form>

            {/* Computations List */}
            <div className="mt-8">
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                Recent Computations
              </h3>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        ID
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Type
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Created At
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {computations.map((computation) => (
                      <tr key={computation.computation_id}>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          {computation.computation_id.substring(0, 8)}...
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {computation.type}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                            computation.status === 'completed' ? 'bg-green-100 text-green-800' : 
                            computation.status === 'error' ? 'bg-red-100 text-red-800' : 
                            computation.status === 'processing' ? 'bg-blue-100 text-blue-800' : 
                            'bg-yellow-100 text-yellow-800'
                          }`}>
                            {computation.status}
                          </span>
                          {computation.progress_percentage !== undefined && (
                            <div className="mt-1">
                              <div className="w-full bg-gray-200 rounded-full h-2.5">
                                <div 
                                  className="bg-blue-600 h-2.5 rounded-full" 
                                  style={{ width: `${computation.progress_percentage}%` }}
                                ></div>
                              </div>
                              <span className="text-xs text-gray-500">{computation.progress_percentage}%</span>
                            </div>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {new Date(computation.created_at).toLocaleString()}
                          {computation.status_message && (
                            <div className="text-xs text-gray-500 mt-1">{computation.status_message}</div>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          <div className="flex space-x-2">
                            <button
                              onClick={() => handleViewResults(computation.computation_id)}
                              className="text-indigo-600 hover:text-indigo-900"
                              disabled={computation.status !== 'completed'}
                            >
                              View Results
                            </button>
                            {computation.security_method !== 'standard' && computation.status !== 'completed' && (
                              <button
                                onClick={() => handleClientEncryption(computation.computation_id)}
                                className="text-purple-600 hover:text-purple-900 mr-2"
                              >
                                Encrypt
                              </button>
                            )}
                            {computation.status !== 'completed' && computation.status !== 'processing' && (
                              <>
                                <button
                                  onClick={() => handleVerifyComputation(computation.computation_id)}
                                  className="text-blue-600 hover:text-blue-900 mr-2"
                                >
                                  Verify
                                </button>
                                <button
                                  onClick={() => handleTriggerComputation(computation.computation_id)}
                                  className="text-green-600 hover:text-green-900"
                                >
                                  Compute
                                </button>
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Results Visualization */}
            {selectedComputation && (
              <div className="mt-8">
                <ComputationResults computationId={selectedComputation} />
              </div>
            )}
            
            {showEncryption && selectedComputationForEncryption && (
              <div className="fixed inset-0 bg-gray-600 bg-opacity-75 flex items-center justify-center z-50">
                <div className="bg-white rounded-lg shadow-xl p-6 max-w-2xl w-full max-h-screen overflow-y-auto">
                  <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-bold">Client-Side Encryption</h2>
                    <button
                      onClick={() => {
                        setShowEncryption(false);
                        setSelectedComputationForEncryption(null);
                      }}
                      className="text-gray-500 hover:text-gray-700"
                    >
                      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                  <SecureEncryption 
                    computationId={selectedComputationForEncryption} 
                    onEncryptionComplete={handleEncryptionComplete} 
                  />
                  {encryptedData && (
                    <div className="mt-4">
                      <button
                        onClick={async () => {
                    try {
                      setLoading(true);
                      const response = await fetch(`http://localhost:8000/secure-computations/computations/${selectedComputationForEncryption}/submit`, {
                        method: 'POST',
                        headers: {
                          'Content-Type': 'application/json',
                          'Authorization': `Bearer ${token}`
                        },
                        body: JSON.stringify({
                          value: encryptedData,
                          encryption_type: encryptedData.encryption_type
                        })
                      });
                      
                      if (!response.ok) {
                        const errorData = await response.json();
                        throw new Error(errorData.detail || 'Failed to submit encrypted data');
                      }
                      
                      toast.success('Encrypted data submitted successfully');
                      setShowEncryption(false);
                      setSelectedComputationForEncryption(null);
                      setEncryptedData(null);
                      fetchComputations();
                    } catch (error) {
                      toast.error(error.message);
                    } finally {
                      setLoading(false);
                    }
                  }}
                        className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                      >
                        Submit Encrypted Data
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SecureComputation;