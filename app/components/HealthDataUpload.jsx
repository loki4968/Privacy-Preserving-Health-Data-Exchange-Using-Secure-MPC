import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { toast } from 'react-hot-toast';

const HealthDataUpload = () => {
  const [formData, setFormData] = useState({
    patient_id: '',
    data_type: '',
    data: {},
    timestamp: new Date().toISOString()
  });
  const [isLoading, setIsLoading] = useState(false);
  const { user } = useAuth();
  const token = user?.token;

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleDataChange = (e) => {
    try {
      const data = JSON.parse(e.target.value);
      setFormData(prev => ({
        ...prev,
        data
      }));
    } catch (error) {
      toast.error('Invalid JSON format');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/secure-health-data', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(formData)
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to upload health data');
      }

      toast.success('Health data uploaded successfully');
      setFormData({
        patient_id: '',
        data_type: '',
        data: {},
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      toast.error(error.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md mx-auto">
        <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">
            Upload Health Data
          </h2>
          
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="patient_id" className="block text-sm font-medium text-gray-700">
                Patient ID
              </label>
              <input
                type="text"
                name="patient_id"
                id="patient_id"
                required
                value={formData.patient_id}
                onChange={handleChange}
                className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              />
            </div>

            <div>
              <label htmlFor="data_type" className="block text-sm font-medium text-gray-700">
                Data Type
              </label>
              <select
                name="data_type"
                id="data_type"
                required
                value={formData.data_type}
                onChange={handleChange}
                className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              >
                <option value="">Select a type</option>
                <option value="blood_pressure">Blood Pressure</option>
                <option value="heart_rate">Heart Rate</option>
                <option value="temperature">Temperature</option>
                <option value="lab_result">Lab Result</option>
                <option value="medication">Medication</option>
              </select>
            </div>

            <div>
              <label htmlFor="data" className="block text-sm font-medium text-gray-700">
                Health Data (JSON)
              </label>
              <textarea
                name="data"
                id="data"
                required
                value={JSON.stringify(formData.data, null, 2)}
                onChange={handleDataChange}
                rows={6}
                className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm font-mono"
                placeholder='{"value": 120, "unit": "mmHg", "notes": "Morning reading"}'
              />
            </div>

            <div>
              <button
                type="submit"
                disabled={isLoading}
                className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
              >
                {isLoading ? 'Uploading...' : 'Upload Health Data'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default HealthDataUpload; 