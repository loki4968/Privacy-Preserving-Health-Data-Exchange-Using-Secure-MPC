import React, { useState, useEffect } from 'react';
import { ChevronLeft, ChevronRight, Check, X, Info, Shield, Database, Users, Lock } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { secureComputationService } from '../services/secureComputationService';
import { API_ENDPOINTS, fetchApi } from '../config/api';

const SecureComputationWizard = ({ user, onClose, onComputationCreated }) => {
  const [currentStep, setCurrentStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Step titles for the wizard
  const steps = [
    { number: 1, title: "Setup", icon: <Info size={18} /> },
    { number: 2, title: "Data & Logic", icon: <Database size={18} /> },
    { number: 3, title: "Security", icon: <Lock size={18} /> },
    { number: 4, title: "Participants", icon: <Users size={18} /> },
    { number: 5, title: "Review", icon: <Shield size={18} /> }
  ];
  
  // Step 1: Setup
  const [computationTitle, setComputationTitle] = useState('');
  const [computationDescription, setComputationDescription] = useState('');
  const [interpretedSpec, setInterpretedSpec] = useState(null);
  
  // Step 2: Logic & Data
  const [selectedFunction, setSelectedFunction] = useState('');
  // Optional CSV column mapping (used later during CSV submission)
  const [hasHeader, setHasHeader] = useState(true);
  const [delimiter, setDelimiter] = useState(',');
  const [singleColumn, setSingleColumn] = useState('');
  const [multiColumns, setMultiColumns] = useState('');
  const [columnIndex, setColumnIndex] = useState('');
  const [secureAverageThreshold, setSecureAverageThreshold] = useState('');
  const [cohortAgeMin, setCohortAgeMin] = useState('');
  const [cohortCondition, setCohortCondition] = useState('');
  
  // Step 3: Security Method
  const [selectedSecurityMethod, setSelectedSecurityMethod] = useState('homomorphic');
  
  // Step 4: Participants
  const [selectedParticipants, setSelectedParticipants] = useState([]);
  const [availableParticipants, setAvailableParticipants] = useState([]);
  
  // Step 5: Review
  const [confirmationChecked, setConfirmationChecked] = useState(false);
  
  // Computation types supported by backend
  const functionOptions = [
    // Basic Statistics
    { id: 'average', label: 'Average', category: 'Basic Statistics' },
    { id: 'sum', label: 'Sum', category: 'Basic Statistics' },
    { id: 'count', label: 'Count', category: 'Basic Statistics' },
    { id: 'secure_average', label: 'Secure Average', category: 'Basic Statistics' },
    { id: 'secure_sum', label: 'Secure Sum', category: 'Basic Statistics' },
    { id: 'secure_variance', label: 'Secure Variance', category: 'Basic Statistics' },
    
    // Advanced Statistical Analysis
    { id: 'secure_correlation', label: 'Correlation Analysis', category: 'Advanced Statistics' },
    { id: 'secure_regression', label: 'Regression Analysis', category: 'Advanced Statistics' },
    { id: 'secure_survival', label: 'Survival Analysis', category: 'Clinical Analysis' },
    
    // Machine Learning
    { id: 'federated_logistic', label: 'Federated Logistic Regression', category: 'Machine Learning' },
    { id: 'federated_random_forest', label: 'Federated Random Forest', category: 'Machine Learning' },
    { id: 'anomaly_detection', label: 'Anomaly Detection', category: 'Machine Learning' },
    
    // Healthcare Analytics
    { id: 'cohort_analysis', label: 'Patient Cohort Analysis', category: 'Clinical Analysis' },
    { id: 'drug_safety', label: 'Drug Safety Analysis', category: 'Pharmacovigilance' },
    { id: 'epidemiological', label: 'Epidemiological Analysis', category: 'Public Health' },
    
    // Genomics & Precision Medicine
    { id: 'secure_gwas', label: 'Genome-Wide Association Study', category: 'Genomics' },
    { id: 'pharmacogenomics', label: 'Pharmacogenomic Analysis', category: 'Precision Medicine' }
  ];
  
  // Fetch available participants and datasets
  useEffect(() => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    if (!token) return;
    (async () => {
      try {
        const orgs = await secureComputationService.getAvailableOrganizations(token);
        const mapped = (orgs || []).map(o => ({ id: o.id, name: o.name || o.email, online: o.online }));
        setAvailableParticipants(mapped);
      } catch (error) {
        console.error('Error fetching organizations:', error);
        toast.error('Failed to fetch organizations');
        // fallback to only current user
        setAvailableParticipants([{ id: user?.id, name: user?.email || `Org ${user?.id}`, online: true }]);
      }

    })();
  }, []);
  
  
  const handleNext = () => {
    // Validate current step before proceeding
    if (currentStep === 1) {
      if (!computationTitle.trim()) {
        setError('Computation title is required');
        return;
      }
      // Try to interpret the description into a generic spec
      if (computationDescription && !interpretedSpec) {
        const token = user?.token || (typeof window !== 'undefined' ? localStorage.getItem('token') : null);
        if (token) {
          setLoading(true);
          secureComputationService
            .interpretPrompt(computationDescription, token)
            .then((spec) => {
              setInterpretedSpec(spec);
              console.log('Interpreted computation spec from prompt:', spec);
              // Auto-select function based on analysis_type if available
              if (spec.analysis_type && spec.operations && spec.operations.length > 0) {
                const opType = spec.operations[0].type;
                // Map analysis_type to function id
                const typeToFunction = {
                  'mean_difference': 'secure_average',
                  'regression': 'secure_regression',
                  'correlation': 'secure_correlation',
                  'survival': 'secure_survival',
                  'cohort_analysis': 'cohort_analysis',
                  'basic_statistics': 'secure_average'
                };
                const mappedFunction = typeToFunction[spec.analysis_type] || opType;
                if (mappedFunction && functionOptions.find(f => f.id === mappedFunction)) {
                  setSelectedFunction(mappedFunction);
                }
              }
              setLoading(false);
            })
            .catch((e) => {
              console.warn('Prompt interpretation failed, continuing without spec:', e);
              setLoading(false);
            });
        }
      }
    } else if (currentStep === 2) {
      // If we have an interpreted spec with operations, function selection is optional
      if (!selectedFunction && (!interpretedSpec || !interpretedSpec.operations || interpretedSpec.operations.length === 0)) {
        setError('Please select a computation function or provide a detailed description that can be interpreted');
        return;
      }
      // Dataset/column are optional for this MVP
    } else if (currentStep === 4) {
      if (selectedParticipants.length === 0) {
        setError('Please select at least one participant');
        return;
      }
    }
    
    setError(null);
    setCurrentStep(prev => Math.min(prev + 1, 5));
  };
  
  const handleBack = () => {
    setCurrentStep(prev => Math.max(prev - 1, 1));
    setError(null);
  };
  
  const handleParticipantToggle = (participantId) => {
    setSelectedParticipants(prev => {
      if (prev.includes(participantId)) {
        return prev.filter(id => id !== participantId);
      } else {
        return [...prev, participantId];
      }
    });
  };
  
  const handleSubmit = async () => {
    if (!confirmationChecked) {
      setError('Please confirm the details are correct');
      return;
    }
    
    let timeoutId;
    
    try {
      setLoading(true);
      setError(null);
      
      // Set a timeout to prevent infinite loading (30 seconds)
      timeoutId = setTimeout(() => {
        setLoading(false);
        setError('Request timed out. Please try again.');
      }, 30000);
      
      // Determine computation type: prefer spec-derived, then selected function, then default
      let finalComputationType = selectedFunction;
      
      // If we have a spec with operations, derive computation type from it
      if (interpretedSpec && interpretedSpec.operations && interpretedSpec.operations.length > 0) {
        const specOpType = interpretedSpec.operations[0].type;
        // Use spec operation type if no function was manually selected, or if it's more specific
        if (!selectedFunction || specOpType) {
          finalComputationType = specOpType || selectedFunction || 'health_statistics';
        }
      }
      
      // Fallback to default if still no type
      if (!finalComputationType) {
        finalComputationType = 'health_statistics';
      }
      
      // Prepare the request payload
      const computationData = {
        computation_type: finalComputationType,
        invited_org_ids: selectedParticipants.length > 0 ? selectedParticipants : null,
        security_method: selectedSecurityMethod
      };

      // Only add threshold if explicitly provided (not blood sugar specific)
      if (selectedFunction === 'secure_average' && secureAverageThreshold !== '') {
        const parsed = Number(secureAverageThreshold);
        if (!Number.isNaN(parsed) && parsed > 0) {
          computationData.threshold = parsed;
        }
      }

      // Build operations from spec or selected function
      const specOperations = [];
      
      // If we have interpreted spec operations, use those (they're more accurate)
      if (interpretedSpec && interpretedSpec.operations && interpretedSpec.operations.length > 0) {
        specOperations.push(...interpretedSpec.operations);
      } else if (selectedFunction) {
        // Fallback to manual selection
        const op = {
          id: 'main_operation',
          type: selectedFunction
        };
        if (selectedFunction === 'cohort_analysis') {
          const criteria = {};
          if (cohortAgeMin !== '') {
            const ageVal = Number(cohortAgeMin);
            if (!Number.isNaN(ageVal)) {
              criteria.age_min = ageVal;
            }
          }
          if (cohortCondition && cohortCondition.trim()) {
            criteria.condition = cohortCondition.trim();
          }
          if (Object.keys(criteria).length > 0) {
            op.options = criteria;
          }
        }
        specOperations.push(op);
      }

      // Build final spec
      const spec = interpretedSpec
        ? {
            // Merge interpreted spec with wizard selections
            ...interpretedSpec,
            prompt_text: interpretedSpec.prompt_text || computationDescription || computationTitle || '',
            operations: specOperations.length > 0 ? specOperations : (interpretedSpec.operations || []),
          }
        : {
            prompt_text: computationDescription || computationTitle || '',
            variables: [],
            operations: specOperations
          };

      // Always include spec if we have prompt text or operations
      if (spec.prompt_text || spec.operations.length > 0) {
        computationData.spec = spec;
      }
      
      console.log('Creating computation with data:', computationData);
      
      // Call the API to create a new computation
      const response = await secureComputationService.createComputation(computationData, user.token);
      
      // Clear timeout since request completed
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
      
      console.log('Computation creation response:', response);
      
      // Always close wizard and show success, regardless of response structure
      // The backend will return different formats, so we need to be flexible
      const computationId = response?.computation_id || response?.id || 'unknown';

      // Show success message
      toast.success(`Secure computation created successfully! ID: ${computationId}`);

      // Note: CSV upload removed - participants will submit their own data

      // Notify parent component about the new computation
      if (onComputationCreated) {
        onComputationCreated(response);
      }
      
      // Force close the wizard
      setLoading(false);
      onClose();
      
      // Redirect to computation details page
      if (computationId && computationId !== 'unknown') {
        setTimeout(() => {
          window.location.href = `/secure-computations/${computationId}`;
        }, 500);
      }
    } catch (err) {
      // Clear timeout on error
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
      
      console.error('Error creating computation:', err);
      
      // Handle specific error types
      let errorMessage = 'Unknown error occurred';
      if (err.message) {
        errorMessage = err.message;
      } else if (err.status === 401) {
        errorMessage = 'Authentication failed. Please log in again.';
      } else if (err.status === 403) {
        errorMessage = 'You do not have permission to create computations.';
      } else if (err.status === 500) {
        errorMessage = 'Server error. Please try again later.';
      } else if (err.message === 'Failed to fetch' || err.name === 'NetworkError') {
        errorMessage = 'Network error. Please check your connection and try again.';
      }
      
      setError('Failed to create computation: ' + errorMessage);
      // Don't close the wizard on error, let user see the error and try again
    } finally {
      setLoading(false);
    }
  };
  
  // Render step content based on current step
  const renderStepContent = () => {
    switch (currentStep) {
      case 1:
        return (
          <div className="space-y-6">
            <div className="flex items-center space-x-3 text-blue-700">
              <Info size={20} />
              <h2 className="text-xl font-semibold">Computation Setup</h2>
            </div>
            <p className="text-gray-600 text-sm">Define the basic information for your secure computation.</p>
            
            <div className="space-y-4 bg-gray-50 p-4 rounded-lg">
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">
                  Computation Title <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm"
                  placeholder="e.g., Regional Diabetes Age Analysis"
                  value={computationTitle}
                  onChange={(e) => setComputationTitle(e.target.value)}
                />
                <p className="text-xs text-gray-500 mt-1">Choose a clear, descriptive title that identifies the purpose of this computation.</p>
              </div>
              
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">
                  Description & Purpose <span className="text-blue-600 text-xs">(AI-Powered)</span>
                </label>
                <textarea
                  className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm"
                  placeholder="Describe your research question or survey purpose in natural language. Example: 'Compare average fasting blood glucose levels between diabetic and non-diabetic patients, adjusting for age and BMI over the last 6 months.'"
                  rows={5}
                  value={computationDescription}
                  onChange={(e) => {
                    setComputationDescription(e.target.value);
                    setInterpretedSpec(null); // Reset spec when description changes
                  }}
                />
                <p className="text-xs text-gray-500 mt-1">
                  Provide a detailed description of your research question or survey. The system will automatically extract variables, analysis type, and population criteria.
                </p>
                {interpretedSpec && (
                  <div className="mt-3 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <h4 className="text-sm font-semibold text-blue-900 mb-2">✨ Interpreted Specification</h4>
                    {interpretedSpec.research_question && (
                      <p className="text-sm text-blue-800 mb-2">
                        <strong>Research Question:</strong> {interpretedSpec.research_question}
                      </p>
                    )}
                    {interpretedSpec.analysis_type && (
                      <p className="text-sm text-blue-800 mb-2">
                        <strong>Analysis Type:</strong> <span className="capitalize">{interpretedSpec.analysis_type.replace('_', ' ')}</span>
                      </p>
                    )}
                    {interpretedSpec.variables && interpretedSpec.variables.length > 0 && (
                      <div className="mt-2">
                        <p className="text-sm font-medium text-blue-900 mb-1">Variables Detected:</p>
                        <ul className="list-disc list-inside text-xs text-blue-700 space-y-1">
                          {interpretedSpec.variables.map((v, idx) => (
                            <li key={idx}>
                              {v.name} {v.unit && `(${v.unit})`} {v.role && `[${v.role}]`}
                            </li>
                          ))}
                        </ul>
              </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        );
      
      case 2:
        return (
          <div className="space-y-6">
            <div className="flex items-center space-x-3 text-blue-700">
              <Database size={20} />
              <h2 className="text-xl font-semibold">Define Logic & Data</h2>
            </div>
            <p className="text-gray-600 text-sm">Select the computation function and data source for your secure analysis.</p>
            
            <div className="space-y-5 bg-gray-50 p-4 rounded-lg">
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">
                  Computation Function {interpretedSpec && interpretedSpec.operations && interpretedSpec.operations.length > 0 ? <span className="text-blue-600 text-xs">(Auto-selected from description)</span> : <span className="text-red-500">*</span>}
                </label>
                {interpretedSpec && interpretedSpec.operations && interpretedSpec.operations.length > 0 && (
                  <div className="mb-3 p-3 bg-green-50 border border-green-200 rounded-lg">
                    <p className="text-sm text-green-800">
                      <strong>Auto-selected:</strong> {interpretedSpec.operations[0].type || 'N/A'}
                    </p>
                    <p className="text-xs text-green-700 mt-1">
                      You can override this selection if needed
                    </p>
                  </div>
                )}
                <div className="space-y-4">
                  {/* Group computations by category */}
                  {Object.entries(
                    functionOptions.reduce((acc, option) => {
                      const category = option.category || 'Other';
                      if (!acc[category]) acc[category] = [];
                      acc[category].push(option);
                      return acc;
                    }, {})
                  ).map(([category, options]) => (
                    <div key={category} className="space-y-2">
                      <h4 className="font-semibold text-gray-800 text-sm border-b border-gray-200 pb-1">
                        {category}
                      </h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                        {options.map(option => (
                          <div 
                            key={option.id}
                            onClick={() => setSelectedFunction(option.id)}
                            className={`border rounded-lg p-3 cursor-pointer transition-all ${selectedFunction === option.id 
                              ? 'border-blue-500 bg-blue-50 shadow-sm' 
                              : 'border-gray-300 hover:border-blue-300 hover:bg-blue-50'}`}
                          >
                            <div className="font-medium text-sm">{option.label}</div>
                            <div className="text-xs text-gray-500 mt-1">
                              {option.id === 'average' && 'Calculate average value'}
                              {option.id === 'sum' && 'Calculate sum of values'}
                              {option.id === 'count' && 'Count matching records'}
                              {option.id === 'secure_average' && 'Privacy-preserving average'}
                              {option.id === 'secure_sum' && 'Privacy-preserving sum'}
                              {option.id === 'secure_variance' && 'Privacy-preserving variance'}
                              {option.id === 'secure_correlation' && 'Correlation between variables'}
                              {option.id === 'secure_regression' && 'Linear regression analysis'}
                              {option.id === 'secure_survival' && 'Kaplan-Meier survival curves'}
                              {option.id === 'federated_logistic' && 'Train logistic regression model'}
                              {option.id === 'federated_random_forest' && 'Train ensemble model'}
                              {option.id === 'anomaly_detection' && 'Detect outliers and anomalies'}
                              {option.id === 'cohort_analysis' && 'Analyze patient cohorts'}
                              {option.id === 'drug_safety' && 'Detect adverse drug reactions'}
                              {option.id === 'epidemiological' && 'Population health surveillance'}
                              {option.id === 'secure_gwas' && 'Genetic association analysis'}
                              {option.id === 'pharmacogenomics' && 'Drug-gene interactions'}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <Info className="w-5 h-5 text-blue-600 mt-0.5" />
                  <div>
                    <h3 className="font-medium text-blue-900">Data Submission Process</h3>
                    <p className="text-sm text-blue-700 mt-1">
                      Participants will manually enter their numeric data points during the submission phase. 
                      No pre-uploaded datasets are required for this computation.
                    </p>
                  </div>
                </div>

                {selectedFunction === 'secure_average' && (
                  <div className="space-y-2 mt-4">
                    <label className="block text-sm font-medium text-gray-700">
                      Threshold Value (Optional)
                    </label>
                    <input
                      type="number"
                      className="w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                      value={secureAverageThreshold}
                      onChange={(e) => setSecureAverageThreshold(e.target.value)}
                      placeholder="Enter threshold if needed for your analysis"
                      min="0"
                    />
                    <p className="text-xs text-gray-500">
                      Optional: Specify a threshold value for classification or filtering purposes
                    </p>
                  </div>
                )}
              </div>

              {selectedFunction === 'cohort_analysis' && (
                <div className="mt-4 space-y-3 bg-white border border-gray-200 rounded-lg p-4">
                  <div className="text-sm font-medium text-gray-800">
                    Cohort Criteria
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">
                        Minimum Age
                      </label>
                      <input
                        type="number"
                        className="w-full border border-gray-300 rounded p-2 text-sm"
                        value={cohortAgeMin}
                        onChange={(e) => setCohortAgeMin(e.target.value)}
                        placeholder="e.g., 18"
                        min="0"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-600 mb-1">
                        Condition / Diagnosis Keyword
                      </label>
                      <input
                        className="w-full border border-gray-300 rounded p-2 text-sm"
                        value={cohortCondition}
                        onChange={(e) => setCohortCondition(e.target.value)}
                        placeholder="e.g., diabetes"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Optional CSV Column Mapping */}
              <div className="bg-white border border-gray-200 rounded-lg p-4">
                <h4 className="font-medium text-gray-800 mb-2">Optional: CSV Column Mapping</h4>
                <p className="text-xs text-gray-500 mb-3">These settings will be used when submitting CSV data to this computation.</p>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div>
                    <label className="block text-xs text-gray-600 mb-1">Has Header</label>
                    <select
                      className="w-full border border-gray-300 rounded p-2 text-sm"
                      value={hasHeader ? 'true' : 'false'}
                      onChange={(e) => setHasHeader(e.target.value === 'true')}
                    >
                      <option value="true">True</option>
                      <option value="false">False</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-gray-600 mb-1">Delimiter</label>
                    <input
                      className="w-full border border-gray-300 rounded p-2 text-sm"
                      value={delimiter}
                      onChange={(e) => setDelimiter(e.target.value)}
                      placeholder=","/>
                  </div>
                  <div>
                    <label className="block text-xs text-gray-600 mb-1">Column Index (no header)</label>
                    <input
                      className="w-full border border-gray-300 rounded p-2 text-sm"
                      value={columnIndex}
                      onChange={(e) => setColumnIndex(e.target.value)}
                      placeholder="e.g., 0"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3">
                  <div>
                    <label className="block text-xs text-gray-600 mb-1">Single Column (header name)</label>
                    <input
                      className="w-full border border-gray-300 rounded p-2 text-sm"
                      value={singleColumn}
                      onChange={(e) => setSingleColumn(e.target.value)}
                      placeholder="e.g., systolic"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-600 mb-1">Multiple Columns (comma-separated)</label>
                    <input
                      className="w-full border border-gray-300 rounded p-2 text-sm"
                      value={multiColumns}
                      onChange={(e) => setMultiColumns(e.target.value)}
                      placeholder="e.g., systolic,diastolic"
                    />
                  </div>
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  Note: If both Single and Multiple Columns are provided, Multiple Columns take precedence. If none provided, the first column is used.
                </p>
              </div>
            </div>
          </div>
        );
      
      case 3:
        return (
          <div className="space-y-6">
            <div className="flex items-center space-x-3 text-blue-700">
              <Lock size={20} />
              <h2 className="text-xl font-semibold">Security Method</h2>
            </div>
            <p className="text-gray-600 text-sm">Select the security method to use for this computation. Different methods offer varying levels of privacy, performance, and complexity.</p>
            
            <div className="space-y-5 bg-gray-50 p-4 rounded-lg">
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">
                  Security Method <span className="text-red-500">*</span>
                </label>
                <div className="grid grid-cols-1 gap-4">
                  <div 
                    onClick={() => setSelectedSecurityMethod('standard')}
                    className={`border rounded-lg p-4 cursor-pointer transition-all ${selectedSecurityMethod === 'standard' 
                      ? 'border-blue-500 bg-blue-50 shadow-sm' 
                      : 'border-gray-300 hover:border-blue-300 hover:bg-blue-50'}`}
                  >
                    <div className="flex justify-between items-center">
                      <div>
                        <div className="font-medium text-lg">Standard</div>
                        <div className="text-sm text-gray-500 mt-1">Basic encryption for data in transit and at rest</div>
                      </div>
                      <div className="bg-green-100 text-green-800 text-xs font-medium px-2.5 py-0.5 rounded-full">Fast</div>
                    </div>
                    <div className="mt-3 text-sm">
                      <ul className="list-disc list-inside space-y-1 text-gray-600">
                        <li>Basic data privacy protection</li>
                        <li>Fast computation with minimal overhead</li>
                        <li>Suitable for non-sensitive data</li>
                      </ul>
                    </div>
                  </div>
                  
                  <div 
                    onClick={() => setSelectedSecurityMethod('homomorphic')}
                    className={`border rounded-lg p-4 cursor-pointer transition-all ${selectedSecurityMethod === 'homomorphic' 
                      ? 'border-blue-500 bg-blue-50 shadow-sm' 
                      : 'border-gray-300 hover:border-blue-300 hover:bg-blue-50'}`}
                  >
                    <div className="flex justify-between items-center">
                      <div>
                        <div className="font-medium text-lg">Homomorphic Encryption</div>
                        <div className="text-sm text-gray-500 mt-1">Perform computations on encrypted data</div>
                      </div>
                      <div className="bg-yellow-100 text-yellow-800 text-xs font-medium px-2.5 py-0.5 rounded-full">Medium</div>
                    </div>
                    <div className="mt-3 text-sm">
                      <ul className="list-disc list-inside space-y-1 text-gray-600">
                        <li>High data privacy protection</li>
                        <li>Moderate performance impact</li>
                        <li>Ideal for sensitive health data</li>
                      </ul>
                    </div>
                  </div>
                  
                  <div 
                    onClick={() => setSelectedSecurityMethod('hybrid')}
                    className={`border rounded-lg p-4 cursor-pointer transition-all ${selectedSecurityMethod === 'hybrid' 
                      ? 'border-blue-500 bg-blue-50 shadow-sm' 
                      : 'border-gray-300 hover:border-blue-300 hover:bg-blue-50'}`}
                  >
                    <div className="flex justify-between items-center">
                      <div>
                        <div className="font-medium text-lg">Hybrid (HE+SMPC)</div>
                        <div className="text-sm text-gray-500 mt-1">Combines homomorphic encryption with secure multi-party computation</div>
                      </div>
                      <div className="bg-red-100 text-red-800 text-xs font-medium px-2.5 py-0.5 rounded-full">Slow</div>
                    </div>
                    <div className="mt-3 text-sm">
                      <ul className="list-disc list-inside space-y-1 text-gray-600">
                        <li>Maximum data privacy protection</li>
                        <li>Significant performance impact</li>
                        <li>Best for highly sensitive data requiring maximum security</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        );
        
      case 4:
        return (
          <div className="space-y-6">
            <div className="flex items-center space-x-3 text-blue-700">
              <Users size={20} />
              <h2 className="text-xl font-semibold">Select Participants</h2>
            </div>
            <p className="text-gray-600 text-sm">Select the healthcare institutions that will participate in this secure computation. These organizations will receive a request to join your computation.</p>
            
            <div className="space-y-4 bg-gray-50 p-4 rounded-lg">
              <div className="flex justify-between items-center">
                <label className="block text-sm font-medium text-gray-700">
                  Invite Institutions <span className="text-red-500">*</span>
                </label>
                <div className="text-xs text-gray-500 flex items-center space-x-4">
                  <div className="flex items-center">
                    <span className="inline-block w-2 h-2 rounded-full mr-2 bg-green-500"></span>
                    <span>Online</span>
                  </div>
                  <div className="flex items-center">
                    <span className="inline-block w-2 h-2 rounded-full mr-2 bg-gray-400"></span>
                    <span>Offline</span>
                  </div>
                </div>
              </div>
              
              <div className="border border-gray-300 rounded-md overflow-hidden shadow-sm">
                <div className="bg-gray-100 p-3 border-b border-gray-300 flex justify-between text-xs font-medium text-gray-600">
                  <div>Institution</div>
                  <div>Status</div>
                </div>
                <div className="max-h-60 overflow-y-auto">
                  {availableParticipants.map(participant => (
                    <div 
                      key={participant.id} 
                      onClick={() => participant.online && handleParticipantToggle(participant.id)}
                      className={`p-3 flex items-center justify-between border-b border-gray-200 ${!participant.online ? 'bg-gray-50 opacity-60' : 'hover:bg-blue-50 cursor-pointer'} transition-colors`}
                    >
                      <div className="flex items-center">
                        <input
                          type="checkbox"
                          id={`participant-${participant.id}`}
                          checked={selectedParticipants.includes(participant.id)}
                          onChange={() => participant.online && handleParticipantToggle(participant.id)}
                          disabled={!participant.online}
                          className="mr-3 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                          onClick={(e) => e.stopPropagation()}
                        />
                        <label htmlFor={`participant-${participant.id}`} className="text-sm font-medium text-gray-700">
                          {participant.name}
                        </label>
                      </div>
                      <div className="flex items-center">
                        <span 
                          className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${participant.online ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}
                        >
                          {participant.online ? 'Available' : 'Unavailable'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              
              <div className="flex items-center justify-between pt-2">
                <p className="text-xs text-gray-500">Selected participants: {selectedParticipants.length}</p>
                {selectedParticipants.length > 0 && (
                  <button 
                    onClick={() => setSelectedParticipants([])} 
                    className="text-xs text-blue-600 hover:text-blue-800"
                  >
                    Clear all
                  </button>
                )}
              </div>
            </div>
          </div>
        );
      
      case 5:
        return (
          <div className="space-y-6">
            <div className="flex items-center space-x-3 text-blue-700">
              <Shield size={20} />
              <h2 className="text-xl font-semibold">Review & Launch</h2>
            </div>
            <p className="text-gray-600 text-sm">Review your secure computation details before launching.</p>
            
            <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
              <div className="bg-blue-50 p-4 border-b border-blue-100">
                <h3 className="font-medium text-blue-800">Computation Summary</h3>
              </div>
              
              <div className="p-4">
                <div className="space-y-4">
                  <div>
                    <h4 className="text-sm font-medium text-gray-500 mb-2">Basic Information</h4>
                    <div className="bg-gray-50 p-3 rounded-md">
                      <div className="grid grid-cols-3 gap-4 text-sm">
                        <div className="col-span-1 font-medium text-gray-700">Title:</div>
                        <div className="col-span-2">{computationTitle}</div>
                        
                        <div className="col-span-1 font-medium text-gray-700">Description:</div>
                        <div className="col-span-2">{computationDescription || 'None provided'}</div>
                      </div>
                    </div>
                  </div>
                  
                  <div>
                    <h4 className="text-sm font-medium text-gray-500 mb-2">Computation Logic</h4>
                    <div className="bg-gray-50 p-3 rounded-md">
                      <div className="grid grid-cols-3 gap-4 text-sm">
                        <div className="col-span-1 font-medium text-gray-700">Function:</div>
                        <div className="col-span-2">
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                            {functionOptions.find(f => f.id === selectedFunction)?.label || selectedFunction}
                          </span>
                        </div>
                        
                        <div className="col-span-1 font-medium text-gray-700">Data Source:</div>
                        <div className="col-span-2">Manual data entry by participants</div>
                        
                        <div className="col-span-1 font-medium text-gray-700">Security Method:</div>
                        <div className="col-span-2">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${selectedSecurityMethod === 'standard' 
                            ? 'bg-green-100 text-green-800' 
                            : selectedSecurityMethod === 'homomorphic' 
                              ? 'bg-yellow-100 text-yellow-800' 
                              : 'bg-red-100 text-red-800'}`}>
                            {selectedSecurityMethod === 'standard' 
                              ? 'Standard' 
                              : selectedSecurityMethod === 'homomorphic' 
                                ? 'Homomorphic Encryption' 
                                : 'Hybrid (HE+SMPC)'}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <div>
                    <h4 className="text-sm font-medium text-gray-500 mb-2">Participants ({selectedParticipants.length})</h4>
                    <div className="bg-gray-50 p-3 rounded-md">
                      {selectedParticipants.length > 0 ? (
                        <div className="grid grid-cols-2 gap-2 text-sm">
                          {selectedParticipants.map(id => {
                            const participant = availableParticipants.find(p => p.id === id);
                            return participant ? (
                              <div key={id} className="flex items-center">
                                <Check size={14} className="text-green-500 mr-2" />
                                {participant.name}
                              </div>
                            ) : null;
                          })}
                        </div>
                      ) : (
                        <div className="text-sm text-gray-500 italic">No participants selected</div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded-md">
              <div className="flex">
                <div className="flex-shrink-0">
                  <Info size={20} className="text-yellow-400" />
                </div>
                <div className="ml-3">
                  <p className="text-sm text-yellow-700">
                    By launching this computation, you'll initiate a secure multi-party computation process. All participants will need to approve before the computation begins.
                  </p>
                </div>
              </div>
            </div>
            
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <Info className="w-5 h-5 text-blue-600 mt-0.5" />
                <div>
                  <h4 className="font-medium text-blue-900 mb-1">Data Submission</h4>
                  <p className="text-sm text-blue-700">
                    After creating this computation, invited participants will receive a request to join and submit their data. 
                    As the computation creator, you do not need to upload data here. Each participant will submit their own data 
                    through the computation detail page.
                  </p>
              </div>
                </div>
            </div>

            <div className="flex items-start mt-4 bg-blue-50 p-4 rounded-md border border-blue-100">
              <input
                type="checkbox"
                id="confirmation"
                checked={confirmationChecked}
                onChange={(e) => setConfirmationChecked(e.target.checked)}
                className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <label htmlFor="confirmation" className="ml-2 block text-sm text-gray-700">
                I confirm the details are correct and consent to sending secure invitations to the selected participants.
              </label>
            </div>
          </div>
        );
      
      default:
        return null;
    }
  };
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        <div className="p-4 border-b border-gray-200 flex justify-between items-center">
          <h1 className="text-xl font-bold text-blue-700">Create New Secure Computation</h1>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 focus:outline-none transition-colors"
          >
            <X size={20} />
          </button>
        </div>
        
        {/* Step indicator */}
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex justify-between items-center">
            {steps.map((step, index) => (
              <div key={step.number} className="flex flex-col items-center relative z-10 w-1/4">
                <div 
                  className={`w-10 h-10 rounded-full flex items-center justify-center mb-1 transition-all duration-200 ${currentStep === step.number 
                    ? 'bg-blue-600 text-white ring-4 ring-blue-100' 
                    : currentStep > step.number 
                      ? 'bg-green-500 text-white' 
                      : 'bg-gray-200 text-gray-600'}`}
                >
                  {currentStep > step.number ? <Check size={18} /> : step.icon}
                </div>
                <span className={`text-xs font-medium ${currentStep === step.number ? 'text-blue-600' : 'text-gray-500'}`}>
                  {step.title}
                </span>
                {index < steps.length - 1 && (
                  <div className="absolute top-5 left-1/2 w-full h-1 bg-gray-200 -z-10">
                    <div 
                      className={`h-full ${currentStep > step.number ? 'bg-green-500' : 'bg-gray-200'}`}
                      style={{ width: '100%' }}
                    ></div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
        
        <div className="p-6 overflow-y-auto flex-grow" style={{ maxHeight: 'calc(90vh - 200px)' }}>
          {error && (
            <div className="mb-4 p-3 bg-red-50 border-l-4 border-red-500 text-red-700 rounded-md flex items-center shadow-sm">
              <X size={16} className="mr-2 flex-shrink-0" />
              {error}
            </div>
          )}
          
          {renderStepContent()}
        </div>
        
        <div className="p-4 border-t border-gray-200 flex justify-between items-center">
          <div>
            {currentStep > 1 && (
              <button
                onClick={handleBack}
                disabled={loading}
                className={`px-4 py-2 rounded-md flex items-center transition-all duration-200 ${loading ? 'opacity-50 cursor-not-allowed' : ''} text-gray-700 bg-gray-100 hover:bg-gray-200 border border-gray-300 shadow-sm`}
              >
                <ChevronLeft size={16} className="mr-1" />
                Back
              </button>
            )}
          </div>
          
          <div className="flex items-center">
            {currentStep < 5 ? (
              <button
                onClick={handleNext}
                disabled={loading}
                className="px-5 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50 flex items-center shadow-sm transition-all duration-200"
              >
                <span>Continue to {steps[currentStep].title}</span>
                <ChevronRight size={16} className="ml-2" />
              </button>
            ) : (
              <button
                onClick={handleSubmit}
                disabled={loading || !confirmationChecked}
                className={`px-5 py-2 rounded-md flex items-center shadow-sm transition-all duration-200 ${!confirmationChecked ? 'bg-blue-400 text-white cursor-not-allowed' : 'bg-green-600 text-white hover:bg-green-700 focus:ring-2 focus:ring-green-500 focus:ring-opacity-50'}`}
              >
                {loading ? (
                  <div className="flex items-center">
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span>Sending Invitations...</span>
                  </div>
                ) : (
                  <div className="flex items-center">
                    <span>Launch Secure Computation</span>
                    <Check size={16} className="ml-2" />
                  </div>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SecureComputationWizard;