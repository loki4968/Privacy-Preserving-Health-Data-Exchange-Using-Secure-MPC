'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '../../context/AuthContext';
import { toast } from 'react-hot-toast';
import SecureEncryption from '../../components/SecureEncryption';
import ComputationResults from '../../components/ComputationResults';
import { 
  ArrowLeft, 
  Clock, 
  CheckCircle, 
  AlertCircle, 
  Activity,
  RefreshCw,
  Eye,
  Play,
  BarChart3,
  Users,
  UserCheck,
  UserX,
  Calculator,
  Download,
  Upload
} from 'lucide-react';
import Link from 'next/link';

export default function ComputationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { user } = useAuth();
  const computationId = params.id;
  
  const [computation, setComputation] = useState(null);
  const [participants, setParticipants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showEncryption, setShowEncryption] = useState(false);
  const [encryptedData, setEncryptedData] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [computing, setComputing] = useState(false);
  const [rawDataPoints, setRawDataPoints] = useState([]);
  const [csvUploading, setCsvUploading] = useState(false);
  const [selectedCsvFile, setSelectedCsvFile] = useState(null);
  const csvFileInputRef = useRef(null);

  useEffect(() => {
    if (!user) {
      router.push('/login');
      return;
    }
    
    if (computationId) {
      fetchComputationDetails();
      fetchParticipants();
    }
  }, [computationId, user, router]);

  const fetchComputationDetails = async () => {
    try {
      setLoading(true);
      const token = user?.token || localStorage.getItem('token');
      
      if (!token) {
        throw new Error('Authentication required');
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/secure-computations/computations/${computationId}/result`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );

      if (!response.ok) {
        let errorData = {};
        try {
          const text = await response.text();
          errorData = text ? JSON.parse(text) : {};
        } catch (e) {
          console.warn("Failed to parse error response:", e);
        }
        
        if (response.status === 404) {
          throw new Error(errorData.detail || 'Computation not found');
        }
        if (response.status === 429) {
          throw new Error('Too many requests. Please wait a moment and try again.');
        }
        throw new Error(errorData.detail || errorData.message || 'Failed to fetch computation details');
      }

      let data = {};
      try {
        const text = await response.text();
        data = text ? JSON.parse(text) : {};
      } catch (e) {
        console.error("Failed to parse computation response:", e);
        throw new Error('Invalid response from server');
      }
      
      console.log('Computation details fetched:', data);
      setComputation(data);
      
      // If computation is in error state, log the error
      if (data.status === 'error') {
        console.error('Computation error:', {
          status: data.status,
          error_message: data.error_message,
          error_code: data.error_code,
          computation_id: computationId,
          full_data: data
        });
      }
    } catch (err) {
      console.error('Error fetching computation:', err);
      setError(err.message || 'Failed to load computation details');
      toast.error(err.message || 'Failed to load computation details');
    } finally {
      setLoading(false);
    }
  };

  const fetchParticipants = async () => {
    try {
      const token = user?.token || localStorage.getItem('token');
      
      if (!token) return;

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/secure-computations/computations/${computationId}/active-participants`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );

      if (response.ok) {
        const data = await response.json();
        // The endpoint returns { participants: [...], total_count: ..., ... }
        setParticipants(Array.isArray(data.participants) ? data.participants : (Array.isArray(data) ? data : []));
      }
    } catch (err) {
      console.error('Error fetching participants:', err);
    }
  };

  const handleEncryptionComplete = (encryptedResult, rawDataPoints) => {
    setEncryptedData(encryptedResult);
    setRawDataPoints(rawDataPoints);
    toast.success('Data encrypted successfully. You can now submit it.');
  };

  const handleSubmitEncryptedData = async () => {
    if (!encryptedData || !rawDataPoints || rawDataPoints.length === 0) {
      toast.error('No data to submit');
      return;
    }

    try {
      setSubmitting(true);
      const token = user?.token || localStorage.getItem('token');
      
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/secure-computations/computations/${computationId}/submit`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            value: rawDataPoints,
            encryption_type: encryptedData.encryption_type
          })
        }
      );

      if (!response.ok) {
        let errorMessage = `Failed to submit encrypted data (Status: ${response.status})`;
        try {
          const text = await response.text();
          if (text) {
            try {
              const errorData = JSON.parse(text);
              errorMessage = errorData.detail || 
                            errorData.message || 
                            (errorData.error && (typeof errorData.error === 'string' ? errorData.error : errorData.error.message)) ||
                            errorData.msg ||
                            text ||
                            errorMessage;
            } catch (parseError) {
              errorMessage = text || errorMessage;
            }
          }
        } catch (readError) {
          console.error('Error reading response:', readError);
        }
        throw new Error(errorMessage);
      }

      toast.success('Data submitted successfully');
      setShowEncryption(false);
      setEncryptedData(null);
      setRawDataPoints([]);
      fetchComputationDetails();
      fetchParticipants();
    } catch (err) {
      console.error('Error submitting data:', err);
      toast.error(err.message || 'Failed to submit data');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCsvFileChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.csv')) {
      toast.error('Please select a CSV file');
      e.target.value = '';
      return;
    }
    setSelectedCsvFile(file);
  };

  const handleCsvUpload = async () => {
    if (!selectedCsvFile) {
      toast.error('Please choose a CSV file first');
      return;
    }

    try {
      setCsvUploading(true);
      const file = selectedCsvFile;
      const token = user?.token || localStorage.getItem('token');
      
      const formData = new FormData();
      formData.append('file', file);
      formData.append('description', `CSV upload: ${file.name}`);
      formData.append('has_header', 'true');
      formData.append('delimiter', ',');
      // Let backend auto-detect the blood sugar column
      // Or specify: formData.append('column', 'BloodSugar_mg_dL');
      
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(
        `${apiUrl}/secure-computations/computations/${computationId}/submit-csv`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
            // Don't set Content-Type - let browser set it with boundary
          },
          body: formData
        }
      );
      
      if (!response.ok) {
        let errorMessage = `CSV upload failed (${response.status})`;
        try {
          const text = await response.text();
          if (text) {
            try {
              const errorData = JSON.parse(text);
              // Handle error message extraction - check if values are objects
              const detail = errorData.detail;
              const message = errorData.message;
              const error = errorData.error;
              
              // Convert to string if it's an object
              if (typeof detail === 'string') {
                errorMessage = detail;
              } else if (typeof detail === 'object' && detail !== null) {
                errorMessage = JSON.stringify(detail);
              } else if (typeof message === 'string') {
                errorMessage = message;
              } else if (typeof message === 'object' && message !== null) {
                errorMessage = JSON.stringify(message);
              } else if (typeof error === 'string') {
                errorMessage = error;
              } else if (typeof error === 'object' && error !== null) {
                errorMessage = JSON.stringify(error);
              } else if (text) {
                errorMessage = text;
              }
            } catch (parseError) {
              // If JSON parsing fails, use the text as-is
              errorMessage = text || errorMessage;
            }
          }
        } catch (readError) {
          console.error('Error reading response:', readError);
        }
        throw new Error(errorMessage);
      }
      
      const result = await response.json();
      toast.success(`CSV uploaded successfully! ${result.data_points_count ?? 0} records submitted.`);
      
      // Reset file input
      setSelectedCsvFile(null);
      if (csvFileInputRef.current) {
        csvFileInputRef.current.value = '';
      }
      
      // Refresh computation details
      fetchComputationDetails();
      fetchParticipants();
    } catch (err) {
      console.error('Error uploading CSV:', err);
      toast.error(err.message || 'Failed to upload CSV file');
    } finally {
      setCsvUploading(false);
    }
  };

  const handleCompute = async () => {
    try {
      setComputing(true);
      const token = user?.token || localStorage.getItem('token');
      
      console.log('Triggering computation for:', computationId);
      
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/secure-computations/computations/${computationId}/compute`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );

      if (!response.ok) {
        let errorMessage = 'Failed to compute';
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorData.message || errorData.error || errorMessage;
        } catch (e) {
          const text = await response.text();
          errorMessage = text || errorMessage;
        }
        throw new Error(errorMessage);
      }

      const result = await response.json();
      console.log('Compute result:', result);
      
      // Handle different result statuses
      if (result.status === 'error') {
        toast.error(result.error_message || result.message || 'Computation failed');
        // Refresh to get updated error state
        setTimeout(() => {
          fetchComputationDetails();
          fetchParticipants();
        }, 500);
        return;
      }
      
      if (result.status === 'completed') {
        toast.success(result.message || 'Computation completed successfully');
        // Refresh and redirect to results
        setTimeout(() => {
          fetchComputationDetails();
          fetchParticipants();
          router.push(`/secure-computations/${computationId}/results`);
        }, 1000);
        return;
      }
      
      // Processing or other status
      toast.success(result.message || 'Computation started successfully');
      
      // Refresh data after a short delay to allow backend to process
      setTimeout(() => {
        fetchComputationDetails();
        fetchParticipants();
      }, 1000);
    } catch (err) {
      console.error('Error computing:', err);
      toast.error(err.message || 'Failed to start computation');
    } finally {
      setComputing(false);
    }
  };

  const isCreator = () => {
    if (!computation || !user) return false;
    const userId = user.id || user.user_id || user.org_id;
    const creatorId = computation.org_id || computation.creator_id;
    
    // Debug logging
    console.log('isCreator check:', {
      userId,
      creatorId,
      computation_org_id: computation.org_id,
      computation_creator_id: computation.creator_id,
      user_id: user.id,
      user_user_id: user.user_id,
      user_org_id: user.org_id
    });
    
    // Check if user is the creator
    if (userId && creatorId) {
      return String(userId) === String(creatorId);
    }
    
    // Fallback: if we can't determine, allow if user has permission (for now)
    // In production, you'd want stricter checks
    return true; // Temporarily allow all authenticated users to see compute button
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'processing':
      case 'computing':
        return <Activity className="w-5 h-5 text-blue-500 animate-pulse" />;
      case 'error':
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      case 'waiting_for_data':
        return <Clock className="w-5 h-5 text-yellow-500" />;
      case 'ready_to_compute':
        return <Calculator className="w-5 h-5 text-green-500" />;
      default:
        return <Clock className="w-5 h-5 text-gray-500" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'processing':
      case 'computing':
        return 'bg-blue-100 text-blue-800';
      case 'error':
        return 'bg-red-100 text-red-800';
      case 'waiting_for_data':
        return 'bg-yellow-100 text-yellow-800';
      case 'ready_to_compute':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading computation details...</p>
        </div>
      </div>
    );
  }

  if (error || !computation) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Error</h1>
          <p className="text-gray-600 mb-6">{error || 'Computation not found'}</p>
          <Link
            href="/secure-computations"
            className="inline-flex items-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Computations
          </Link>
        </div>
      </div>
    );
  }

  const participantsCount = computation.participants || computation.participants_count || (Array.isArray(participants) ? participants.length : 0);
  const derivedSubmissions = Array.isArray(participants) ? participants.filter(p => p.has_submitted).length : 0;
  const submissionsCount = computation.submissions || computation.submissions_count || derivedSubmissions || 0;
  const progress = `${submissionsCount}/${participantsCount}`;
  
  // Check if ready to compute - multiple conditions
  const isReadyToCompute = 
    computation.status === 'ready_to_compute' || 
    computation.status === 'ready_to_compute_results' ||
    (computation.status === 'waiting_for_data' && participantsCount > 0 && submissionsCount >= participantsCount) ||
    (participantsCount > 0 && submissionsCount >= participantsCount && computation.status !== 'completed' && computation.status !== 'processing' && computation.status !== 'computing');
  
  // Debug logging
  console.log('Computation status check:', {
    status: computation.status,
    participantsCount,
    submissionsCount,
    isReadyToCompute,
    allSubmitted: participantsCount > 0 && submissionsCount >= participantsCount,
    computation
  });

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <Link
            href="/secure-computations"
            className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Computations
          </Link>
          
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex justify-between items-start">
              <div className="flex-1">
                <h1 className="text-3xl font-bold text-gray-900 mb-2">
                  {computation.title || `Computation ${computationId.substring(0, 8)}`}
                </h1>
                <p className="text-gray-600 mb-4">
                  {computation.description || computation.research_question || 'No description provided'}
                </p>
                <div className="flex items-center gap-3 flex-wrap">
                  <div className="flex items-center gap-2">
                    {getStatusIcon(computation.status)}
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(computation.status)}`}>
                      {computation.status?.replace(/_/g, ' ') || 'Unknown'}
                    </span>
                  </div>
                  {computation.progress && (
                    <span className="text-sm text-gray-600">
                      {computation.progress}
                    </span>
                  )}
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    fetchComputationDetails();
                    fetchParticipants();
                  }}
                  className="p-2 text-blue-500 hover:text-blue-700 hover:bg-blue-50 rounded-full transition-colors"
                  title="Refresh"
                >
                  <RefreshCw className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
          <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-sm font-medium text-gray-500 mb-2">Computation ID</h3>
            <p className="text-lg font-mono text-gray-900 break-all">{computationId.substring(0, 16)}...</p>
          </div>
          
          {computation.created_at && (
            <div className="bg-white rounded-lg shadow-md p-6">
              <h3 className="text-sm font-medium text-gray-500 mb-2">Created At</h3>
              <p className="text-lg text-gray-900">
                {new Date(computation.created_at).toLocaleString()}
              </p>
            </div>
          )}
          
          <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-sm font-medium text-gray-500 mb-2 flex items-center gap-2">
              <Users className="w-4 h-4" />
              Participants
            </h3>
            <p className="text-2xl font-bold text-gray-900">{participantsCount}</p>
          </div>

          <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-sm font-medium text-gray-500 mb-2">Submissions</h3>
            <p className="text-2xl font-bold text-gray-900">{submissionsCount} / {participantsCount}</p>
            <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
              <div 
                className="bg-blue-600 h-2 rounded-full transition-all"
                style={{ width: `${participantsCount > 0 ? (submissionsCount / participantsCount) * 100 : 0}%` }}
              ></div>
            </div>
          </div>
        </div>

        {/* Participants List */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
              <Users className="w-6 h-6" />
              Participants & Submission Status
            </h2>
          </div>
          
          {participants && participants.length > 0 ? (
            <div className="space-y-3">
              {participants.map((participant, index) => (
                <div 
                  key={participant.org_id || participant.id || index}
                  className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    {participant.has_submitted ? (
                      <UserCheck className="w-5 h-5 text-green-500" />
                    ) : (
                      <UserX className="w-5 h-5 text-gray-400" />
                    )}
                    <div>
                      <p className="font-medium text-gray-900">
                        {participant.organization_name || participant.org_name || `Organization ${participant.org_id || participant.id}`}
                      </p>
                      <p className="text-sm text-gray-500">
                        {participant.organization_type && `${participant.organization_type} • `}
                        ID: {participant.org_id || participant.id}
                        {participant.submitted_at && (
                          <span className="ml-2">• Submitted: {new Date(participant.submitted_at).toLocaleDateString()}</span>
                        )}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    {participant.has_submitted ? (
                      <span className="inline-flex items-center gap-2 px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">
                        <CheckCircle className="w-4 h-4" />
                        Submitted
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-2 px-3 py-1 bg-yellow-100 text-yellow-800 rounded-full text-sm font-medium">
                        <Clock className="w-4 h-4" />
                        Pending
                      </span>
                    )}
                    {participant.data_points_count !== undefined && (
                      <span className="text-sm text-gray-600">
                        {participant.data_points_count} data points
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <Users className="w-12 h-12 mx-auto mb-2 text-gray-400" />
              <p>No participants found</p>
            </div>
          )}
        </div>

        {/* Actions Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Submit Data Section */}
          {computation.status === 'waiting_for_data' && (
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                <Play className="w-6 h-6" />
                Submit Data
              </h2>
              
              {/* CSV Upload Option */}
              <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <h3 className="text-sm font-semibold text-blue-900 mb-2">Option 1: Upload CSV File</h3>
                <p className="text-xs text-blue-700 mb-3">
                  Upload a CSV file with patient data. The system will automatically detect patient IDs and numeric values.
                </p>
                <input
                  type="file"
                  accept=".csv"
                  onChange={handleCsvFileChange}
                  ref={csvFileInputRef}
                  className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-700"
                />
                {selectedCsvFile && (
                  <p className="text-xs text-blue-800 mt-2">
                    Selected file: <span className="font-semibold">{selectedCsvFile.name}</span>
                  </p>
                )}
                <button
                  onClick={handleCsvUpload}
                  disabled={!selectedCsvFile || csvUploading}
                  className="mt-3 inline-flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
                >
                  {csvUploading ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Uploading...
                    </>
                  ) : (
                    <>
                      <Upload className="w-4 h-4" />
                      Upload CSV
                    </>
                  )}
                </button>
              </div>
              
              {/* Manual Entry Option */}
              <div className="mb-4">
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Option 2: Manual Entry</h3>
                {!showEncryption ? (
                  <button
                    onClick={() => setShowEncryption(true)}
                    className="w-full inline-flex items-center justify-center gap-2 bg-gray-600 text-white px-6 py-3 rounded-lg hover:bg-gray-700 transition-colors"
                  >
                    <Play className="w-5 h-5" />
                    Enter Data Manually
                  </button>
                ) : (
                  <div>
                    <SecureEncryption
                      computationId={computationId}
                      onEncryptionComplete={handleEncryptionComplete}
                    />
                    {encryptedData && (
                      <div className="mt-4">
                        <button
                          onClick={handleSubmitEncryptedData}
                          disabled={submitting}
                          className="w-full flex items-center justify-center gap-2 bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
                        >
                          {submitting ? (
                            <>
                              <RefreshCw className="w-5 h-5 animate-spin" />
                              Submitting...
                            </>
                          ) : (
                            <>
                              <CheckCircle className="w-5 h-5" />
                              Submit Encrypted Data
                            </>
                          )}
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Compute Button - Show when ready to compute */}
          {isReadyToCompute && (
            <div className="bg-gradient-to-r from-green-50 to-emerald-50 border-2 border-green-200 rounded-lg shadow-lg p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                <Calculator className="w-6 h-6 text-green-600" />
                Execute Computation
              </h2>
              <p className="text-sm text-gray-700 mb-4">
                All {participantsCount} participants have submitted their data ({submissionsCount} submissions). 
                Click the button below to execute the secure computation and generate results.
              </p>
              <button
                onClick={handleCompute}
                disabled={computing}
                className="w-full inline-flex items-center justify-center gap-2 bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 shadow-md hover:shadow-lg transform hover:scale-105 transition-all"
              >
                {computing ? (
                  <>
                    <RefreshCw className="w-5 h-5 animate-spin" />
                    Computing...
                  </>
                ) : (
                  <>
                    <Calculator className="w-5 h-5" />
                    Execute Computation
                  </>
                )}
              </button>
            </div>
          )}

          {/* Processing Status */}
          {(computation.status === 'processing' || computation.status === 'computing') && (
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                <Activity className="w-6 h-6 animate-pulse text-blue-500" />
                Computation in Progress
              </h2>
              <p className="text-sm text-gray-600 mb-4">
                The secure computation is currently being processed. Please wait...
              </p>
              <div className="flex items-center gap-2 text-blue-600">
                <RefreshCw className="w-5 h-5 animate-spin" />
                <span>Processing...</span>
              </div>
            </div>
          )}

          {/* Error Status */}
          {computation.status === 'error' && (
            <div className="bg-red-50 border-2 border-red-200 rounded-lg shadow-md p-6">
              <h2 className="text-xl font-bold text-red-900 mb-4 flex items-center gap-2">
                <AlertCircle className="w-6 h-6 text-red-500" />
                Computation Failed
              </h2>
              {computation.error_message && (
                <div className="mb-4 p-3 bg-red-100 rounded-lg">
                  <p className="text-sm font-medium text-red-800 mb-1">Error Message:</p>
                  <p className="text-sm text-red-700">{computation.error_message}</p>
                </div>
              )}
              {computation.error_code && (
                <div className="mb-4">
                  <p className="text-sm text-red-600">
                    Error Code: <span className="font-mono">{computation.error_code}</span>
                  </p>
                </div>
              )}
              <div className="flex gap-3">
                <button
                  onClick={handleCompute}
                  disabled={computing}
                  className="inline-flex items-center gap-2 bg-red-600 text-white px-6 py-3 rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
                >
                  {computing ? (
                    <>
                      <RefreshCw className="w-5 h-5 animate-spin" />
                      Retrying...
                    </>
                  ) : (
                    <>
                      <RefreshCw className="w-5 h-5" />
                      Retry Computation
                    </>
                  )}
                </button>
                <button
                  onClick={() => {
                    fetchComputationDetails();
                    fetchParticipants();
                  }}
                  className="inline-flex items-center gap-2 bg-gray-600 text-white px-6 py-3 rounded-lg hover:bg-gray-700 transition-colors"
                >
                  <RefreshCw className="w-5 h-5" />
                  Refresh Status
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Results */}
        {computation.status === 'completed' && (
          <div className="bg-white rounded-lg shadow-md p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                <BarChart3 className="w-6 h-6" />
                Results
              </h2>
              <div className="flex items-center gap-2">
                <Link
                  href={`/secure-computations/${computationId}/results`}
                  className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-700"
                >
                  <Eye className="w-4 h-4" />
                  View Full Results
                </Link>
              </div>
            </div>
            <ComputationResults computationId={computationId} />
          </div>
        )}
      </div>
    </div>
  );
}
