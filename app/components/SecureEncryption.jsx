import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { toast } from 'react-hot-toast';

const SecureEncryption = ({ computationId, onEncryptionComplete }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [encryptionParams, setEncryptionParams] = useState(null);
  const [dataToEncrypt, setDataToEncrypt] = useState('');
  const [encryptedData, setEncryptedData] = useState(null);
  const [csvFile, setCsvFile] = useState(null);
  const [inputMethod, setInputMethod] = useState('manual'); // 'manual' or 'csv'
  const { user } = useAuth();
  const token = user?.token;

  const fetchEncryptionParams = async () => {
    setIsLoading(true);
    try {
      console.log('Fetching encryption parameters for computation:', computationId);
      console.log('Token present:', !!token);
      
      const response = await fetch(`http://localhost:8000/secure-computations/computations/${computationId}/client-encrypt`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      console.log('Response status:', response.status);
      console.log('Response ok:', response.ok);
      console.log('Response headers:', Object.fromEntries(response.headers.entries()));

      if (!response.ok) {
        let errorMessage = `Failed to fetch encryption parameters (Status: ${response.status})`;
        try {
          const text = await response.text();
          console.error('Raw response text:', text);
          console.error('Response status:', response.status);
          console.error('Response statusText:', response.statusText);
          
          if (text) {
            try {
              const errorData = JSON.parse(text);
              console.error('Parsed error response data:', errorData);
              
              // Try multiple possible error message fields
              errorMessage = errorData.detail || 
                            errorData.message || 
                            (errorData.error && (typeof errorData.error === 'string' ? errorData.error : errorData.error.message)) ||
                            errorData.msg ||
                            text ||
                            `Server error (${response.status}): ${response.statusText}`;
            } catch (parseError) {
              // Not JSON, use text directly
              errorMessage = text || `Server error (${response.status}): ${response.statusText}`;
            }
          } else {
            errorMessage = `Server returned empty response (Status: ${response.status})`;
          }
        } catch (readError) {
          console.error('Error reading response:', readError);
          errorMessage = `Server error (${response.status}): ${response.statusText || 'Unknown error'}`;
        }
        throw new Error(errorMessage);
      }

      const data = await response.json();
      console.log('Encryption parameters received:', data);
      setEncryptionParams(data);
      toast.success('Encryption parameters fetched successfully');
    } catch (error) {
      console.error('Error fetching encryption parameters:', error);
      toast.error(error.message || 'Failed to fetch encryption parameters');
    } finally {
      setIsLoading(false);
    }
  };

  const parseCsvFile = (file) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      
      reader.onload = (e) => {
        try {
          const text = e.target.result;
          const lines = text.split('\n').filter(line => line.trim());
          
          // Parse CSV - handle both comma and other delimiters
          const dataPoints = [];
          let delimiter = ',';
          
          // Try to detect delimiter
          if (text.includes(';')) delimiter = ';';
          else if (text.includes('\t')) delimiter = '\t';
          
          lines.forEach((line, index) => {
            const trimmedLine = line.trim();
            if (!trimmedLine) return;
            
            // Split by delimiter and extract numeric values
            const values = trimmedLine.split(delimiter);
            values.forEach(value => {
              const trimmed = value.trim();
              if (trimmed) {
                const num = parseFloat(trimmed);
                if (!isNaN(num)) {
                  dataPoints.push(num);
                }
              }
            });
          });
          
          if (dataPoints.length === 0) {
            reject(new Error('No numeric values found in CSV file. Please ensure the file contains numeric data.'));
            return;
          }
          
          resolve(dataPoints);
        } catch (error) {
          reject(new Error(`Failed to parse CSV file: ${error.message}`));
        }
      };
      
      reader.onerror = () => {
        reject(new Error('Failed to read CSV file'));
      };
      
      reader.readAsText(file);
    });
  };

  const handleCsvFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    if (!file.name.endsWith('.csv')) {
      toast.error('Please select a CSV file');
      return;
    }
    
    setCsvFile(file);
    setIsLoading(true);
    
    try {
      const dataPoints = await parseCsvFile(file);
      // Convert to comma-separated string for display
      setDataToEncrypt(dataPoints.join(', '));
      toast.success(`Loaded ${dataPoints.length} values from CSV file`);
    } catch (error) {
      toast.error(error.message);
      setCsvFile(null);
    } finally {
      setIsLoading(false);
    }
  };

  const encryptData = async () => {
    if (!encryptionParams) {
      toast.error('Please fetch encryption parameters first');
      return;
    }

    let dataPoints = [];
    
    // Get data from CSV file or manual input
    if (inputMethod === 'csv' && csvFile) {
      try {
        setIsLoading(true);
        dataPoints = await parseCsvFile(csvFile);
      } catch (error) {
        toast.error(error.message);
        setIsLoading(false);
        return;
      }
    } else {
      if (!dataToEncrypt.trim()) {
        toast.error('Please enter data to encrypt or upload a CSV file');
      return;
    }

      // Parse the input data
      dataPoints = dataToEncrypt.split(',').map(item => parseFloat(item.trim()));
      
      // Check for invalid data
      if (dataPoints.some(isNaN)) {
        toast.error('Invalid data format. Please enter comma-separated numbers.');
        return;
      }
    }

    setIsLoading(true);
    try {

      let result;
      
      // Encrypt based on encryption type
      if (encryptionParams.encryption_type === 'homomorphic') {
        result = encryptHomomorphic(dataPoints, encryptionParams);
      } else if (encryptionParams.encryption_type === 'hybrid') {
        result = encryptHybrid(dataPoints, encryptionParams);
      } else {
        // Standard encryption (placeholder - in real app would use proper encryption)
        result = {
          encryption_type: 'standard',
          data: dataPoints
        };
      }

      setEncryptedData(result);
      toast.success('Data encrypted successfully');
      
      // Notify parent component with both encrypted result and raw data points
      if (onEncryptionComplete) {
        onEncryptionComplete(result, dataPoints);
      }
    } catch (error) {
      toast.error(error.message);
    } finally {
      setIsLoading(false);
    }
  };

  // Placeholder for homomorphic encryption
  // In a real application, this would use a proper homomorphic encryption library
  const encryptHomomorphic = (dataPoints, params) => {
    // Simulate homomorphic encryption
    const publicKey = params.public_key;
    
    return {
      encryption_type: 'homomorphic',
      algorithm: 'paillier',
      encrypted_values: dataPoints.map(value => ({
        // This is a placeholder. In a real app, we would use actual homomorphic encryption
        value: value * 1000, // Simulated encryption
        n: publicKey.n,
        g: publicKey.g
      }))
    };
  };

  // Placeholder for hybrid encryption (homomorphic + SMPC)
  const encryptHybrid = (dataPoints, params) => {
    // Simulate homomorphic encryption
    const homomorphicKey = params.homomorphic.public_key;
    
    // Simulate SMPC shares generation
    const smpcParams = params.smpc;
    
    return {
      encryption_type: 'hybrid',
      homomorphic: {
        encrypted_values: dataPoints.map(value => ({
          // This is a placeholder. In a real app, we would use actual homomorphic encryption
          value: value * 1000, // Simulated encryption
          n: homomorphicKey.n,
          g: homomorphicKey.g
        }))
      },
      smpc_shares: {
        // This is a placeholder. In a real app, we would generate actual SMPC shares
        shares: generateSimulatedShares(dataPoints, smpcParams),
        threshold: smpcParams.threshold,
        total_shares: smpcParams.total_shares,
        prime: smpcParams.prime
      }
    };
  };

  // Placeholder for SMPC shares generation
  const generateSimulatedShares = (dataPoints, params) => {
    const shares = {};
    
    // For each participant, generate a "share" (this is just a simulation)
    params.participant_ids.forEach((participantId, index) => {
      shares[participantId] = dataPoints.map(value => {
        return {
          x: index + 1,
          y: (value * (index + 1)) % parseInt(params.prime)
        };
      });
    });
    
    return shares;
  };

  return (
    <div className="bg-white shadow sm:rounded-lg p-6 mt-4">
      <h3 className="text-lg font-medium text-gray-900 mb-4">Secure Client-Side Encryption</h3>
      
      {!encryptionParams ? (
        <div>
          <p className="text-sm text-gray-500 mb-4">
            Fetch encryption parameters to securely encrypt your data before submission.
          </p>
          <button
            onClick={fetchEncryptionParams}
            disabled={isLoading}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
          >
            {isLoading ? 'Fetching...' : 'Fetch Encryption Parameters'}
          </button>
        </div>
      ) : (
        <div>
          <div className="mb-4">
            <p className="text-sm text-gray-500 mb-2">
              Encryption Type: <span className="font-semibold">{encryptionParams.encryption_type}</span>
            </p>
            {encryptionParams.encryption_type === 'homomorphic' && (
              <p className="text-sm text-gray-500">
                Algorithm: <span className="font-semibold">{encryptionParams.algorithm}</span>
              </p>
            )}
            {encryptionParams.encryption_type === 'hybrid' && (
              <div>
                <p className="text-sm text-gray-500">
                  Homomorphic Algorithm: <span className="font-semibold">{encryptionParams.homomorphic.algorithm}</span>
                </p>
                <p className="text-sm text-gray-500">
                  SMPC Algorithm: <span className="font-semibold">{encryptionParams.smpc.algorithm}</span>
                </p>
                <p className="text-sm text-gray-500">
                  Threshold: <span className="font-semibold">{encryptionParams.smpc.threshold}</span>
                </p>
              </div>
            )}
          </div>
          
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Data Input Method
            </label>
            <div className="flex gap-4 mb-4">
              <label className="flex items-center">
                <input
                  type="radio"
                  name="inputMethod"
                  value="manual"
                  checked={inputMethod === 'manual'}
                  onChange={(e) => setInputMethod(e.target.value)}
                  className="mr-2"
                />
                <span className="text-sm text-gray-700">Manual Entry</span>
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  name="inputMethod"
                  value="csv"
                  checked={inputMethod === 'csv'}
                  onChange={(e) => setInputMethod(e.target.value)}
                  className="mr-2"
                />
                <span className="text-sm text-gray-700">CSV File Upload</span>
              </label>
            </div>

            {inputMethod === 'manual' ? (
              <div>
            <label htmlFor="dataToEncrypt" className="block text-sm font-medium text-gray-700 mb-1">
              Enter Data (comma-separated numbers)
            </label>
            <textarea
              id="dataToEncrypt"
              value={dataToEncrypt}
              onChange={(e) => setDataToEncrypt(e.target.value)}
              className="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
              rows="3"
              placeholder="e.g., 45.2, 67.8, 32.1"
            />
              </div>
            ) : (
              <div>
                <label htmlFor="csvFile" className="block text-sm font-medium text-gray-700 mb-1">
                  Upload CSV File
                </label>
                <input
                  type="file"
                  id="csvFile"
                  accept=".csv"
                  onChange={handleCsvFileChange}
                  className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                />
                {csvFile && (
                  <p className="mt-2 text-sm text-gray-600">
                    Selected: <span className="font-medium">{csvFile.name}</span>
                    {dataToEncrypt && (
                      <span className="ml-2 text-gray-500">
                        ({dataToEncrypt.split(',').length} values loaded)
                      </span>
                    )}
                  </p>
                )}
                <p className="mt-1 text-xs text-gray-500">
                  CSV file should contain numeric values. All numeric values from all columns will be extracted.
                </p>
              </div>
            )}
          </div>
          
          <button
            onClick={encryptData}
            disabled={isLoading || (inputMethod === 'manual' && !dataToEncrypt) || (inputMethod === 'csv' && !csvFile)}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50"
          >
            {isLoading ? 'Encrypting...' : 'Encrypt Data'}
          </button>
          
          {encryptedData && (
            <div className="mt-4">
              <h4 className="text-md font-medium text-gray-900 mb-2">Encrypted Data</h4>
              <div className="bg-gray-50 p-3 rounded-md">
                <pre className="text-xs overflow-auto max-h-40">
                  {JSON.stringify(encryptedData, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SecureEncryption;