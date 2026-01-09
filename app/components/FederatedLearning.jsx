import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Container, Row, Col, Card, Button, Form, Alert, Spinner, Table, Badge } from 'react-bootstrap';
import MLService from '../services/MLService';
import { useAuth } from '../context/AuthContext';

const FederatedLearning = () => {
  const { currentUser } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  // Federated Learning state
  const [modelType, setModelType] = useState('linear');
  const [modelParameters, setModelParameters] = useState({});
  const [modelId, setModelId] = useState('');
  const [organizationId, setOrganizationId] = useState(1); // Default org ID
  const [federatedModels, setFederatedModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState(null);
  const [modelUpdates, setModelUpdates] = useState([]);
  const [aggregationResult, setAggregationResult] = useState(null);
  
  // WebSocket state
  const [websocket, setWebsocket] = useState(null);
  const [reconnectAttempt, setReconnectAttempt] = useState(0);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [lastActivity, setLastActivity] = useState(null);
  const [pingStatus, setPingStatus] = useState({ lastPong: null, latency: null });
  const [connectionHealth, setConnectionHealth] = useState(null);
  const pingIntervalRef = useRef(null);
  const MAX_RECONNECT_ATTEMPTS = 5;
  const RECONNECT_DELAY = 3000;
  const PING_INTERVAL = 30000; // 30 seconds
  
  // WebSocket connection handler
  const connectWebSocket = useCallback(() => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        console.error('No auth token found');
        return;
      }

      // Get user info for connection metadata
      const userEmail = localStorage.getItem('userEmail') || currentUser?.email || 'unknown';
      const userRole = localStorage.getItem('userRole') || currentUser?.role || 'unknown';
      const userAgent = navigator.userAgent;

      setConnectionStatus('connecting');
      const ws = new WebSocket(`ws://localhost:8000/ws/federated?token=${token}&email=${encodeURIComponent(userEmail)}&role=${encodeURIComponent(userRole)}&user_agent=${encodeURIComponent(userAgent)}`);
      
      ws.onopen = () => {
        console.log('WebSocket connected for Federated Learning');
        setReconnectAttempt(0);
        setConnectionStatus('connected');
        setLastActivity(new Date());
        setSuccess('Connected to real-time updates');
        
        // Request active federated models
        ws.send(JSON.stringify({
          type: 'get_federated_models'
        }));
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          handleWebSocketMessage(message);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionStatus('error');
        setError('Connection error. Attempting to reconnect...');
      };

      ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        setConnectionStatus('disconnected');
        
        if (reconnectAttempt < MAX_RECONNECT_ATTEMPTS) {
          console.log(`Attempting to reconnect (${reconnectAttempt + 1}/${MAX_RECONNECT_ATTEMPTS})...`);
          setConnectionStatus('reconnecting');
          setTimeout(() => {
            setReconnectAttempt(prev => prev + 1);
            connectWebSocket();
          }, RECONNECT_DELAY);
        } else {
          setError('Failed to connect after multiple attempts. Please refresh the page.');
        }
      };

      setWebsocket(ws);
      return ws;
    } catch (error) {
      console.error('Error connecting to WebSocket:', error);
      setConnectionStatus('error');
      setError('Failed to establish connection. Please try again later.');
    }
  }, [reconnectAttempt, currentUser]);

  // Handle WebSocket messages
  const handleWebSocketMessage = useCallback((message) => {
    setLastActivity(new Date());
    
    switch (message.type) {
      case 'federated_models':
        setFederatedModels(message.data.models);
        break;
        
      case 'model_update':
        // Handle real-time model update
        const update = message.data;
        setModelUpdates(prev => [update, ...prev]);
        
        // If this update is for the currently selected model, update the UI
        if (selectedModel && update.model_id === selectedModel.id) {
          // Update participant count if needed
          if (update.participants_count) {
            setSelectedModel(prev => ({
              ...prev,
              participants: update.participants_count
            }));
          }
        }
        break;
        
      case 'aggregation_result':
        // Handle aggregation result update
        if (selectedModel && message.data.model_id === selectedModel.id) {
          setAggregationResult(message.data.result);
          setSuccess(`Model updates aggregated successfully for model: ${selectedModel.id}`);
          
          // Update the model status
          setFederatedModels(prev => prev.map(model => {
            if (model.id === selectedModel.id) {
              return { ...model, status: 'updated' };
            }
            return model;
          }));
          
          setSelectedModel(prev => ({ ...prev, status: 'updated' }));
        }
        break;
        
      case 'connection_health':
        setConnectionHealth(message.data);
        break;
        
      case 'pong':
        const serverTime = new Date(message.timestamp);
        const clientTime = new Date();
        const latency = clientTime - serverTime;
        setPingStatus({
          lastPong: serverTime,
          latency: latency
        });
        break;
        
      case 'reconnect':
        // Server requested reconnection
        if (websocket) {
          websocket.close();
          setTimeout(connectWebSocket, 1000);
        }
        break;
        
      case 'system_notification':
        setSuccess(message.data.message);
        break;
        
      default:
        console.log('Unhandled message type:', message.type);
    }
  }, [selectedModel, websocket, connectWebSocket]);

  // Setup ping interval for connection health monitoring
  const setupPingInterval = useCallback(() => {
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
    }
    
    pingIntervalRef.current = setInterval(() => {
      if (websocket && websocket.readyState === WebSocket.OPEN) {
        websocket.send(JSON.stringify({
          type: 'ping',
          timestamp: new Date().toISOString()
        }));
      }
    }, PING_INTERVAL);
    
    return () => {
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
      }
    };
  }, [websocket]);

  // Initialize WebSocket connection and fetch data
  useEffect(() => {
    const ws = connectWebSocket();
    const cleanupPing = setupPingInterval();
    
    // Fetch initial data if WebSocket fails
    const fetchInitialData = async () => {
      try {
        const response = await MLService.getFederatedModels();
        if (response.success) {
          setFederatedModels(response.models);
        }
      } catch (err) {
        console.error('Error fetching initial data:', err);
      }
    };
    
    // If WebSocket connection fails, fall back to REST API
    if (!ws) {
      fetchInitialData();
    }
    
    return () => {
      if (websocket) {
        websocket.close();
      }
      cleanupPing();
    };
  }, [connectWebSocket, setupPingInterval]);
  
  // For backward compatibility, also include mock data if no real data is available
  useEffect(() => {
    if (federatedModels.length === 0) {
      // Mock federated models
      const mockModels = [
        { id: 'model-123', model_type: 'linear', created_at: '2023-05-15', participants: 3, status: 'active' },
        { id: 'model-456', model_type: 'logistic', created_at: '2023-05-10', participants: 5, status: 'completed' },
      ];
      
      setFederatedModels(mockModels);
    }
    
    if (modelUpdates.length === 0) {
      // Mock model updates
      const mockUpdates = [
        { organization_id: 1, timestamp: '2023-05-15T10:30:00', metrics: { accuracy: 0.85, loss: 0.23 } },
        { organization_id: 2, timestamp: '2023-05-15T11:15:00', metrics: { accuracy: 0.82, loss: 0.25 } },
        { organization_id: 3, timestamp: '2023-05-15T12:00:00', metrics: { accuracy: 0.87, loss: 0.21 } },
      ];
      
      setModelUpdates(mockUpdates);
    }
  }, [federatedModels.length, modelUpdates.length]);
  
  // Initialize a new federated learning model
  const handleInitializeModel = async () => {
    setLoading(true);
    setError('');
    setSuccess('');
    
    try {
      const result = await MLService.initializeFederatedModel(modelType, modelParameters);
      setModelId(result.model_id);
      setSuccess(`Model initialized successfully with ID: ${result.model_id}`);
      
      // Add the new model to the list
      setFederatedModels([...federatedModels, {
        id: result.model_id,
        model_type: modelType,
        created_at: new Date().toISOString().split('T')[0],
        participants: 0,
        status: 'active'
      }]);
    } catch (err) {
      setError(`Error initializing model: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };
  
  // Join a federated learning training session
  const handleJoinTraining = async () => {
    if (!selectedModel) {
      setError('Please select a model first');
      return;
    }
    
    setLoading(true);
    setError('');
    setSuccess('');
    
    try {
      const result = await MLService.joinFederatedTraining(selectedModel.id, organizationId);
      setSuccess(`Successfully joined training for model: ${selectedModel.id}`);
      
      // Update the selected model's participant count
      const updatedModels = federatedModels.map(model => {
        if (model.id === selectedModel.id) {
          return { ...model, participants: model.participants + 1 };
        }
        return model;
      });
      
      setFederatedModels(updatedModels);
      setSelectedModel({ ...selectedModel, participants: selectedModel.participants + 1 });
    } catch (err) {
      setError(`Error joining training: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };
  
  // Submit a model update for federated learning
  const handleSubmitUpdate = async () => {
    if (!selectedModel) {
      setError('Please select a model first');
      return;
    }
    
    setLoading(true);
    setError('');
    setSuccess('');
    
    try {
      // Mock gradients and metrics
      const mockGradients = {
        weights: Array(10).fill(0).map(() => Math.random() * 0.1 - 0.05),
        bias: Math.random() * 0.1 - 0.05
      };
      
      const mockMetrics = {
        accuracy: 0.85 + Math.random() * 0.1 - 0.05,
        loss: 0.2 + Math.random() * 0.1 - 0.05,
        f1_score: 0.83 + Math.random() * 0.1 - 0.05
      };
      
      const result = await MLService.submitModelUpdate(
        selectedModel.id, 
        organizationId, 
        mockGradients, 
        mockMetrics
      );
      
      setSuccess(`Model update submitted successfully for model: ${selectedModel.id}`);
      
      // Add the update to the list
      const newUpdate = {
        organization_id: organizationId,
        timestamp: new Date().toISOString(),
        metrics: mockMetrics
      };
      
      setModelUpdates([...modelUpdates, newUpdate]);
    } catch (err) {
      setError(`Error submitting update: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };
  
  // Aggregate model updates for federated learning
  const handleAggregateUpdates = async () => {
    if (!selectedModel) {
      setError('Please select a model first');
      return;
    }
    
    setLoading(true);
    setError('');
    setSuccess('');
    
    try {
      const result = await MLService.aggregateModelUpdates(selectedModel.id);
      setAggregationResult(result);
      setSuccess(`Model updates aggregated successfully for model: ${selectedModel.id}`);
      
      // Update the model status
      const updatedModels = federatedModels.map(model => {
        if (model.id === selectedModel.id) {
          return { ...model, status: 'updated' };
        }
        return model;
      });
      
      setFederatedModels(updatedModels);
      setSelectedModel({ ...selectedModel, status: 'updated' });
    } catch (err) {
      setError(`Error aggregating updates: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <Container className="mt-4">
      <h2 className="mb-4">Federated Learning</h2>
      
      <div className="d-flex justify-content-between align-items-center mb-3">
        <div>
          <Badge 
            bg={connectionStatus === 'connected' ? 'success' : 
               connectionStatus === 'connecting' ? 'warning' : 
               connectionStatus === 'reconnecting' ? 'info' : 'danger'}
            className="me-2"
          >
            {connectionStatus === 'connected' ? 'Connected' : 
             connectionStatus === 'connecting' ? 'Connecting...' : 
             connectionStatus === 'reconnecting' ? 'Reconnecting...' : 'Disconnected'}
          </Badge>
          
          {lastActivity && (
            <small className="text-muted me-3">
              Last activity: {new Date(lastActivity).toLocaleTimeString()}
            </small>
          )}
          
          {pingStatus.latency !== null && (
            <small className="text-muted">
              Latency: {pingStatus.latency}ms
            </small>
          )}
        </div>
        
        {connectionStatus !== 'connected' && (
          <Button 
            variant="outline-primary" 
            size="sm" 
            onClick={connectWebSocket}
            disabled={connectionStatus === 'connecting' || connectionStatus === 'reconnecting'}
          >
            Reconnect
          </Button>
        )}
      </div>
      
      {error && <Alert variant="danger">{error}</Alert>}
      {success && <Alert variant="success">{success}</Alert>}
      
      <Row className="mb-4">
        <Col md={6}>
          <Card>
            <Card.Header>Initialize New Federated Model</Card.Header>
            <Card.Body>
              <Form>
                <Form.Group className="mb-3">
                  <Form.Label>Model Type</Form.Label>
                  <Form.Select 
                    value={modelType}
                    onChange={(e) => setModelType(e.target.value)}
                  >
                    <option value="linear">Linear Regression</option>
                    <option value="logistic">Logistic Regression</option>
                    <option value="forest">Random Forest</option>
                    <option value="isolation_forest">Isolation Forest</option>
                    <option value="kmeans">K-Means Clustering</option>
                  </Form.Select>
                </Form.Group>
                
                <Form.Group className="mb-3">
                  <Form.Label>Organization ID</Form.Label>
                  <Form.Control 
                    type="number" 
                    value={organizationId}
                    onChange={(e) => setOrganizationId(parseInt(e.target.value))}
                    min={1}
                  />
                </Form.Group>
                
                <div className="d-grid">
                  <Button 
                    variant="primary" 
                    onClick={handleInitializeModel}
                    disabled={loading}
                  >
                    {loading ? <Spinner animation="border" size="sm" /> : 'Initialize Model'}
                  </Button>
                </div>
              </Form>
            </Card.Body>
          </Card>
        </Col>
        
        <Col md={6}>
          <Card>
            <Card.Header>Available Federated Models</Card.Header>
            <Card.Body>
              <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                <Table striped bordered hover>
                  <thead>
                    <tr>
                      <th>Model ID</th>
                      <th>Type</th>
                      <th>Created</th>
                      <th>Participants</th>
                      <th>Status</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {federatedModels.map((model) => (
                      <tr 
                        key={model.id} 
                        className={selectedModel?.id === model.id ? 'table-primary' : ''}
                      >
                        <td>{model.id}</td>
                        <td>{model.model_type}</td>
                        <td>{model.created_at}</td>
                        <td>{model.participants}</td>
                        <td>
                          <span className={`badge bg-${model.status === 'active' ? 'success' : 
                                            model.status === 'completed' ? 'secondary' : 'info'}`}>
                            {model.status}
                          </span>
                        </td>
                        <td>
                          <Button 
                            variant="outline-primary" 
                            size="sm"
                            onClick={() => setSelectedModel(model)}
                          >
                            Select
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>
      
      {selectedModel && (
        <Row className="mb-4">
          <Col md={12}>
            <Card>
              <Card.Header>Selected Model: {selectedModel.id}</Card.Header>
              <Card.Body>
                <Row>
                  <Col md={4}>
                    <Card>
                      <Card.Header>Model Actions</Card.Header>
                      <Card.Body>
                        <div className="d-grid gap-2">
                          <Button 
                            variant="success" 
                            onClick={handleJoinTraining}
                            disabled={loading}
                          >
                            {loading ? <Spinner animation="border" size="sm" /> : 'Join Training'}
                          </Button>
                          <Button 
                            variant="info" 
                            onClick={handleSubmitUpdate}
                            disabled={loading}
                          >
                            {loading ? <Spinner animation="border" size="sm" /> : 'Submit Update'}
                          </Button>
                          <Button 
                            variant="warning" 
                            onClick={handleAggregateUpdates}
                            disabled={loading}
                          >
                            {loading ? <Spinner animation="border" size="sm" /> : 'Aggregate Updates'}
                          </Button>
                        </div>
                      </Card.Body>
                    </Card>
                  </Col>
                  
                  <Col md={8}>
                    <Card>
                      <Card.Header>Model Updates</Card.Header>
                      <Card.Body>
                        <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                          <Table striped bordered hover>
                            <thead>
                              <tr>
                                <th>Organization</th>
                                <th>Timestamp</th>
                                <th>Accuracy</th>
                                <th>Loss</th>
                              </tr>
                            </thead>
                            <tbody>
                              {modelUpdates.map((update, idx) => (
                                <tr key={idx}>
                                  <td>Org {update.organization_id}</td>
                                  <td>{new Date(update.timestamp).toLocaleString()}</td>
                                  <td>{update.metrics.accuracy.toFixed(4)}</td>
                                  <td>{update.metrics.loss.toFixed(4)}</td>
                                </tr>
                              ))}
                            </tbody>
                          </Table>
                        </div>
                      </Card.Body>
                    </Card>
                  </Col>
                </Row>
                
                {aggregationResult && (
                  <Row className="mt-3">
                    <Col md={12}>
                      <Card>
                        <Card.Header>Aggregation Results</Card.Header>
                        <Card.Body>
                          <Row>
                            <Col md={6}>
                              <h5>Model Performance</h5>
                              <Table striped bordered>
                                <tbody>
                                  <tr>
                                    <th>Global Accuracy</th>
                                    <td>{(aggregationResult.global_metrics?.accuracy || 0.88).toFixed(4)}</td>
                                  </tr>
                                  <tr>
                                    <th>Global Loss</th>
                                    <td>{(aggregationResult.global_metrics?.loss || 0.18).toFixed(4)}</td>
                                  </tr>
                                  <tr>
                                    <th>Improvement</th>
                                    <td>{(aggregationResult.improvement || 0.05).toFixed(4)}</td>
                                  </tr>
                                  <tr>
                                    <th>Convergence</th>
                                    <td>{aggregationResult.converged ? 'Yes' : 'No'}</td>
                                  </tr>
                                </tbody>
                              </Table>
                            </Col>
                            
                            <Col md={6}>
                              <h5>Participant Contributions</h5>
                              <ul className="list-group">
                                {(aggregationResult.contributions || [1, 2, 3].map(id => ({ 
                                  organization_id: id, 
                                  contribution: (0.3 + Math.random() * 0.1).toFixed(2) 
                                }))).map((contrib, idx) => (
                                  <li key={idx} className="list-group-item d-flex justify-content-between align-items-center">
                                    Organization {contrib.organization_id}
                                    <span className="badge bg-primary rounded-pill">
                                      {contrib.contribution}
                                    </span>
                                  </li>
                                ))}
                              </ul>
                            </Col>
                          </Row>
                        </Card.Body>
                      </Card>
                    </Col>
                  </Row>
                )}
              </Card.Body>
            </Card>
          </Col>
        </Row>
      )}
    </Container>
  );
};

export default FederatedLearning;