import React, { useState, useEffect } from 'react';
import { Container, Row, Col, Card, Button, Form, Alert, Spinner } from 'react-bootstrap';
import { Line, Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import MLService from '../services/MLService';
import { useAuth } from '../context/AuthContext';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend
);

const MLDashboard = () => {
  const { currentUser } = useAuth();
  const [activeTab, setActiveTab] = useState('timeseries');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  // Time Series state
  const [timeSeriesData, setTimeSeriesData] = useState([]);
  const [forecastHorizon, setForecastHorizon] = useState(7);
  const [forecastMethod, setForecastMethod] = useState('linear');
  const [forecastResults, setForecastResults] = useState(null);
  const [anomalyResults, setAnomalyResults] = useState(null);
  const [seasonalityResults, setSeasonalityResults] = useState(null);
  const [privacyBudget, setPrivacyBudget] = useState(1.0);
  
  // Risk Assessment state
  const [healthMetrics, setHealthMetrics] = useState({
    blood_pressure: [],
    heart_rate: [],
    glucose_levels: [],
    cholesterol: []
  });
  const [patientInfo, setPatientInfo] = useState({
    age: 45,
    gender: 'male',
    smoking_status: 'former',
    family_history: true
  });
  const [riskResults, setRiskResults] = useState(null);
  const [riskFactors, setRiskFactors] = useState(null);
  
  // Sample data for demonstration
  useEffect(() => {
    // Generate sample time series data
    const generateSampleTimeSeries = () => {
      const now = new Date();
      const data = [];
      
      // Generate 30 days of data
      for (let i = 30; i >= 0; i--) {
        const date = new Date(now);
        date.setDate(date.getDate() - i);
        
        // Add some randomness and trend
        const value = 70 + Math.sin(i / 3) * 10 + Math.random() * 5;
        
        data.push({
          timestamp: date.toISOString().split('T')[0],
          value: parseFloat(value.toFixed(1))
        });
      }
      
      setTimeSeriesData(data);
    };
    
    // Generate sample health metrics
    const generateSampleHealthMetrics = () => {
      const metrics = {
        blood_pressure: [],
        heart_rate: [],
        glucose_levels: [],
        cholesterol: []
      };
      
      // Generate 10 readings for each metric
      for (let i = 0; i < 10; i++) {
        metrics.blood_pressure.push(120 + Math.random() * 20);
        metrics.heart_rate.push(70 + Math.random() * 15);
        metrics.glucose_levels.push(90 + Math.random() * 30);
        metrics.cholesterol.push(180 + Math.random() * 40);
      }
      
      setHealthMetrics(metrics);
    };
    
    generateSampleTimeSeries();
    generateSampleHealthMetrics();
  }, []);
  
  // Time Series Forecasting
  const handleForecast = async () => {
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const result = await MLService.forecastTimeSeries(
        timeSeriesData,
        forecastHorizon,
        forecastMethod,
        privacyBudget
      );

      setForecastResults(result);
      setSuccess('Forecast generated successfully!');
    } catch (err) {
      setError(`Error generating forecast: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };
  
  // Anomaly Detection
  const handleAnomalyDetection = async () => {
    setLoading(true);
    setError('');
    setSuccess('');
    
    try {
      const result = await MLService.detectTimeSeriesAnomalies(
        timeSeriesData,
        privacyBudget
      );
      
      setAnomalyResults(result);
      setSuccess('Anomalies detected successfully!');
    } catch (err) {
      setError(`Error detecting anomalies: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };
  
  // Seasonality Analysis
  const handleSeasonalityAnalysis = async () => {
    setLoading(true);
    setError('');
    setSuccess('');
    
    try {
      const result = await MLService.analyzeTimeSeriesSeasonality(
        timeSeriesData,
        privacyBudget
      );
      
      setSeasonalityResults(result);
      setSuccess('Seasonality analysis completed successfully!');
    } catch (err) {
      setError(`Error analyzing seasonality: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };
  
  // Risk Assessment
  const handleRiskAssessment = async () => {
    setLoading(true);
    setError('');
    setSuccess('');
    
    try {
      const result = await MLService.calculateRiskScore(
        healthMetrics,
        patientInfo,
        privacyBudget
      );
      
      setRiskResults(result);
      setSuccess('Risk assessment completed successfully!');
    } catch (err) {
      setError(`Error calculating risk: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };
  
  // Risk Factors Identification
  const handleRiskFactorsIdentification = async () => {
    setLoading(true);
    setError('');
    setSuccess('');
    
    try {
      const result = await MLService.identifyRiskFactors(
        healthMetrics,
        null, // No timestamps for this example
        privacyBudget
      );
      
      setRiskFactors(result);
      setSuccess('Risk factors identified successfully!');
    } catch (err) {
      setError(`Error identifying risk factors: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };
  
  // Prepare chart data for time series forecast
  const prepareTimeSeriesChartData = () => {
    if (!forecastResults) return null;
    
    const labels = [
      ...timeSeriesData.map(point => point.timestamp),
      ...forecastResults.forecast.map(point => point.timestamp)
    ];
    
    const historicalData = timeSeriesData.map(point => point.value);
    const forecastData = Array(timeSeriesData.length).fill(null).concat(
      forecastResults.forecast.map(point => point.value)
    );
    
    const lowerBound = Array(timeSeriesData.length).fill(null).concat(
      forecastResults.forecast.map(point => point.lower_bound)
    );
    
    const upperBound = Array(timeSeriesData.length).fill(null).concat(
      forecastResults.forecast.map(point => point.upper_bound)
    );
    
    return {
      labels,
      datasets: [
        {
          label: 'Historical Data',
          data: historicalData,
          borderColor: 'rgba(75, 192, 192, 1)',
          backgroundColor: 'rgba(75, 192, 192, 0.2)',
          pointRadius: 3,
          tension: 0.1
        },
        {
          label: 'Forecast',
          data: forecastData,
          borderColor: 'rgba(153, 102, 255, 1)',
          backgroundColor: 'rgba(153, 102, 255, 0.2)',
          pointRadius: 3,
          tension: 0.1
        },
        {
          label: 'Lower Bound',
          data: lowerBound,
          borderColor: 'rgba(255, 99, 132, 1)',
          backgroundColor: 'transparent',
          borderDash: [5, 5],
          pointRadius: 0,
          tension: 0.1
        },
        {
          label: 'Upper Bound',
          data: upperBound,
          borderColor: 'rgba(255, 99, 132, 1)',
          backgroundColor: 'transparent',
          borderDash: [5, 5],
          pointRadius: 0,
          tension: 0.1,
          fill: {
            target: '-1',
            above: 'rgba(255, 99, 132, 0.1)'
          }
        }
      ]
    };
  };
  
  // Prepare chart data for anomaly detection
  const prepareAnomalyChartData = () => {
    if (!anomalyResults) return null;
    
    const labels = timeSeriesData.map(point => point.timestamp);
    const values = timeSeriesData.map(point => point.value);
    
    // Create a dataset for anomalies
    const anomalyIndices = anomalyResults.anomalies.map(a => a.index);
    const anomalyData = values.map((val, idx) => 
      anomalyIndices.includes(idx) ? val : null
    );
    
    return {
      labels,
      datasets: [
        {
          label: 'Time Series',
          data: values,
          borderColor: 'rgba(75, 192, 192, 1)',
          backgroundColor: 'rgba(75, 192, 192, 0.2)',
          pointRadius: 3,
          tension: 0.1
        },
        {
          label: 'Anomalies',
          data: anomalyData,
          borderColor: 'rgba(255, 99, 132, 1)',
          backgroundColor: 'rgba(255, 99, 132, 1)',
          pointRadius: 6,
          pointStyle: 'circle',
          showLine: false
        }
      ]
    };
  };
  
  // Prepare chart data for seasonality
  const prepareSeasonalityChartData = () => {
    if (!seasonalityResults) return null;
    
    const labels = seasonalityResults.autocorrelation.map((_, idx) => `Lag ${idx}`);
    const values = seasonalityResults.autocorrelation;
    
    return {
      labels,
      datasets: [
        {
          label: 'Autocorrelation',
          data: values,
          backgroundColor: 'rgba(54, 162, 235, 0.5)',
          borderColor: 'rgba(54, 162, 235, 1)',
          borderWidth: 1
        }
      ]
    };
  };
  
  // Prepare chart data for risk factors
  const prepareRiskFactorsChartData = () => {
    if (!riskFactors) return null;
    
    const labels = Object.keys(riskFactors.factor_contributions);
    const values = Object.values(riskFactors.factor_contributions);
    
    return {
      labels,
      datasets: [
        {
          label: 'Risk Factor Contribution',
          data: values,
          backgroundColor: [
            'rgba(255, 99, 132, 0.5)',
            'rgba(54, 162, 235, 0.5)',
            'rgba(255, 206, 86, 0.5)',
            'rgba(75, 192, 192, 0.5)',
            'rgba(153, 102, 255, 0.5)'
          ],
          borderColor: [
            'rgba(255, 99, 132, 1)',
            'rgba(54, 162, 235, 1)',
            'rgba(255, 206, 86, 1)',
            'rgba(75, 192, 192, 1)',
            'rgba(153, 102, 255, 1)'
          ],
          borderWidth: 1
        }
      ]
    };
  };
  
  return (
    <Container className="mt-4">
      <h2 className="mb-4">Machine Learning Insights</h2>
      
      {error && <Alert variant="danger">{error}</Alert>}
      {success && <Alert variant="success">{success}</Alert>}
      
      <div className="mb-4">
        <Button 
          variant={activeTab === 'timeseries' ? 'primary' : 'outline-primary'}
          className="me-2"
          onClick={() => setActiveTab('timeseries')}
        >
          Time Series Analysis
        </Button>
        <Button 
          variant={activeTab === 'risk' ? 'primary' : 'outline-primary'}
          onClick={() => setActiveTab('risk')}
        >
          Risk Assessment
        </Button>
      </div>
      
      {activeTab === 'timeseries' && (
        <>
          <Row className="mb-4">
            <Col md={4}>
              <Card>
                <Card.Header>Time Series Configuration</Card.Header>
                <Card.Body>
                  <Form>
                    <Form.Group className="mb-3">
                      <Form.Label>Forecast Horizon</Form.Label>
                      <Form.Control 
                        type="number" 
                        value={forecastHorizon}
                        onChange={(e) => setForecastHorizon(parseInt(e.target.value))}
                        min={1}
                        max={30}
                      />
                    </Form.Group>
                    
                    <Form.Group className="mb-3">
                      <Form.Label>Forecast Method</Form.Label>
                      <Form.Select 
                        value={forecastMethod}
                        onChange={(e) => setForecastMethod(e.target.value)}
                      >
                        <option value="linear">Linear Regression</option>
                        <option value="exponential_smoothing">Exponential Smoothing</option>
                        <option value="holt_winters">Holt-Winters</option>
                        <option value="comprehensive">Comprehensive</option>
                      </Form.Select>
                    </Form.Group>
                    
                    <Form.Group className="mb-3">
                      <Form.Label>Privacy Budget (ε)</Form.Label>
                      <Form.Control 
                        type="number" 
                        value={privacyBudget}
                        onChange={(e) => setPrivacyBudget(parseFloat(e.target.value))}
                        min={0.1}
                        max={10}
                        step={0.1}
                      />
                      <Form.Text className="text-muted">
                        Lower values provide stronger privacy but may reduce accuracy
                      </Form.Text>
                    </Form.Group>
                    
                    <div className="d-grid gap-2">
                      <Button 
                        variant="primary" 
                        onClick={handleForecast}
                        disabled={loading}
                      >
                        {loading ? <Spinner animation="border" size="sm" /> : 'Generate Forecast'}
                      </Button>
                      <Button 
                        variant="secondary" 
                        onClick={handleAnomalyDetection}
                        disabled={loading}
                      >
                        {loading ? <Spinner animation="border" size="sm" /> : 'Detect Anomalies'}
                      </Button>
                      <Button 
                        variant="info" 
                        onClick={handleSeasonalityAnalysis}
                        disabled={loading}
                      >
                        {loading ? <Spinner animation="border" size="sm" /> : 'Analyze Seasonality'}
                      </Button>
                    </div>
                  </Form>
                </Card.Body>
              </Card>
            </Col>
            
            <Col md={8}>
              <Card>
                <Card.Header>Time Series Visualization</Card.Header>
                <Card.Body>
                  {forecastResults && (
                    <>
                      <h5>Forecast Results</h5>
                      <div style={{ height: '300px' }}>
                        <Line 
                          data={prepareTimeSeriesChartData()} 
                          options={{
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                              title: {
                                display: true,
                                text: 'Time Series Forecast'
                              },
                              tooltip: {
                                mode: 'index',
                                intersect: false
                              }
                            },
                            scales: {
                              x: {
                                title: {
                                  display: true,
                                  text: 'Date'
                                }
                              },
                              y: {
                                title: {
                                  display: true,
                                  text: 'Value'
                                }
                              }
                            }
                          }}
                        />
                      </div>
                      
                      <div className="mt-3">
                        <h6>Forecast Statistics</h6>
                        <p><strong>Model:</strong> {forecastResults.model_type}</p>
                        <p><strong>RMSE:</strong> {forecastResults.metrics?.rmse?.toFixed(2) || 'N/A'}</p>
                        <p><strong>MAE:</strong> {forecastResults.metrics?.mae?.toFixed(2) || 'N/A'}</p>
                      </div>
                    </>
                  )}
                  
                  {anomalyResults && (
                    <>
                      <h5 className="mt-4">Anomaly Detection</h5>
                      <div style={{ height: '300px' }}>
                        <Line 
                          data={prepareAnomalyChartData()} 
                          options={{
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                              title: {
                                display: true,
                                text: 'Anomaly Detection'
                              },
                              tooltip: {
                                mode: 'index',
                                intersect: false
                              }
                            }
                          }}
                        />
                      </div>
                      
                      <div className="mt-3">
                        <h6>Anomaly Statistics</h6>
                        <p><strong>Method:</strong> {anomalyResults.method}</p>
                        <p><strong>Anomalies Found:</strong> {anomalyResults.anomalies.length}</p>
                        <p><strong>Threshold:</strong> {anomalyResults.threshold}</p>
                      </div>
                    </>
                  )}
                  
                  {seasonalityResults && (
                    <>
                      <h5 className="mt-4">Seasonality Analysis</h5>
                      <div style={{ height: '300px' }}>
                        <Bar 
                          data={prepareSeasonalityChartData()} 
                          options={{
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                              title: {
                                display: true,
                                text: 'Autocorrelation Function'
                              }
                            },
                            scales: {
                              x: {
                                title: {
                                  display: true,
                                  text: 'Lag'
                                }
                              },
                              y: {
                                title: {
                                  display: true,
                                  text: 'Correlation'
                                }
                              }
                            }
                          }}
                        />
                      </div>
                      
                      <div className="mt-3">
                        <h6>Seasonality Statistics</h6>
                        <p><strong>Detected Period:</strong> {seasonalityResults.detected_period || 'None'}</p>
                        <p><strong>Seasonality Strength:</strong> {seasonalityResults.seasonality_strength?.toFixed(2) || 'N/A'}</p>
                      </div>
                    </>
                  )}
                  
                  {!forecastResults && !anomalyResults && !seasonalityResults && (
                    <div className="text-center p-5">
                      <p>Select an analysis method and click the corresponding button to generate insights.</p>
                    </div>
                  )}
                </Card.Body>
              </Card>
            </Col>
          </Row>
        </>
      )}
      
      {activeTab === 'risk' && (
        <>
          <Row className="mb-4">
            <Col md={4}>
              <Card>
                <Card.Header>Risk Assessment Configuration</Card.Header>
                <Card.Body>
                  <Form>
                    <Form.Group className="mb-3">
                      <Form.Label>Patient Age</Form.Label>
                      <Form.Control 
                        type="number" 
                        value={patientInfo.age}
                        onChange={(e) => setPatientInfo({...patientInfo, age: parseInt(e.target.value)})}
                        min={18}
                        max={100}
                      />
                    </Form.Group>
                    
                    <Form.Group className="mb-3">
                      <Form.Label>Gender</Form.Label>
                      <Form.Select 
                        value={patientInfo.gender}
                        onChange={(e) => setPatientInfo({...patientInfo, gender: e.target.value})}
                      >
                        <option value="male">Male</option>
                        <option value="female">Female</option>
                        <option value="other">Other</option>
                      </Form.Select>
                    </Form.Group>
                    
                    <Form.Group className="mb-3">
                      <Form.Label>Smoking Status</Form.Label>
                      <Form.Select 
                        value={patientInfo.smoking_status}
                        onChange={(e) => setPatientInfo({...patientInfo, smoking_status: e.target.value})}
                      >
                        <option value="never">Never</option>
                        <option value="former">Former</option>
                        <option value="current">Current</option>
                      </Form.Select>
                    </Form.Group>
                    
                    <Form.Group className="mb-3">
                      <Form.Check 
                        type="checkbox" 
                        label="Family History of Cardiovascular Disease" 
                        checked={patientInfo.family_history}
                        onChange={(e) => setPatientInfo({...patientInfo, family_history: e.target.checked})}
                      />
                    </Form.Group>
                    
                    <Form.Group className="mb-3">
                      <Form.Label>Privacy Budget (ε)</Form.Label>
                      <Form.Control 
                        type="number" 
                        value={privacyBudget}
                        onChange={(e) => setPrivacyBudget(parseFloat(e.target.value))}
                        min={0.1}
                        max={10}
                        step={0.1}
                      />
                    </Form.Group>
                    
                    <div className="d-grid gap-2">
                      <Button 
                        variant="primary" 
                        onClick={handleRiskAssessment}
                        disabled={loading}
                      >
                        {loading ? <Spinner animation="border" size="sm" /> : 'Calculate Risk Score'}
                      </Button>
                      <Button 
                        variant="secondary" 
                        onClick={handleRiskFactorsIdentification}
                        disabled={loading}
                      >
                        {loading ? <Spinner animation="border" size="sm" /> : 'Identify Risk Factors'}
                      </Button>
                    </div>
                  </Form>
                </Card.Body>
              </Card>
            </Col>
            
            <Col md={8}>
              <Card>
                <Card.Header>Risk Assessment Results</Card.Header>
                <Card.Body>
                  {riskResults && (
                    <>
                      <div className="text-center mb-4">
                        <h3>Overall Risk Score</h3>
                        <div 
                          className="d-inline-block p-4 rounded-circle" 
                          style={{
                            backgroundColor: riskResults.risk_category === 'high' ? '#dc3545' : 
                                          riskResults.risk_category === 'medium' ? '#ffc107' : '#28a745',
                            width: '150px',
                            height: '150px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: 'white',
                            fontSize: '2rem',
                            fontWeight: 'bold'
                          }}
                        >
                          {riskResults.risk_score.toFixed(1)}
                        </div>
                        <h4 className="mt-3" style={{
                          color: riskResults.risk_category === 'high' ? '#dc3545' : 
                                riskResults.risk_category === 'medium' ? '#ffc107' : '#28a745',
                        }}>
                          {riskResults.risk_category.toUpperCase()} RISK
                        </h4>
                      </div>
                      
                      <div className="mt-4">
                        <h5>Recommendations</h5>
                        <ul>
                          {riskResults.recommendations.map((rec, idx) => (
                            <li key={idx}>{rec}</li>
                          ))}
                        </ul>
                      </div>
                    </>
                  )}
                  
                  {riskFactors && (
                    <>
                      <h5 className="mt-4">Risk Factor Analysis</h5>
                      <div style={{ height: '300px' }}>
                        <Bar 
                          data={prepareRiskFactorsChartData()} 
                          options={{
                            responsive: true,
                            maintainAspectRatio: false,
                            indexAxis: 'y',
                            plugins: {
                              title: {
                                display: true,
                                text: 'Risk Factor Contributions'
                              }
                            },
                            scales: {
                              x: {
                                title: {
                                  display: true,
                                  text: 'Contribution to Risk (%)'
                                },
                                min: 0,
                                max: 100
                              }
                            }
                          }}
                        />
                      </div>
                      
                      <div className="mt-3">
                        <h6>Key Insights</h6>
                        <ul>
                          {riskFactors.insights.map((insight, idx) => (
                            <li key={idx}>{insight}</li>
                          ))}
                        </ul>
                      </div>
                    </>
                  )}
                  
                  {!riskResults && !riskFactors && (
                    <div className="text-center p-5">
                      <p>Configure patient information and click 'Calculate Risk Score' to generate risk assessment.</p>
                    </div>
                  )}
                </Card.Body>
              </Card>
            </Col>
          </Row>
        </>
      )}
    </Container>
  );
};

export default MLDashboard;