"use client";

import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import RoleProtectedRoute from "../components/RoleProtectedRoute";
import { PERMISSIONS } from "../config/roles";
import { useRouter, useSearchParams } from 'next/navigation';
import { motion, AnimatePresence } from "framer-motion";
import { API_ENDPOINTS, fetchApi } from "../config/api";
import PatientDashboard from "../components/PatientDashboard";
import {
  Upload,
  LogOut,
  FileText,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Folder,
  RefreshCw,
  Plus,
  User,
  Filter,
  Settings,
  HelpCircle,
  ChevronDown,
  Building2,
  Shield,
  Activity,
  UploadCloud,
  Trash2,
  BarChart2,
  Users,
  Bell,
  Download,
  LineChart,
  UserCog,
  FileUp,
  Eye
} from "lucide-react";
import Layout from '../components/Layout';
import { Card, CardTitle, CardContent } from '../components/ui/card';
import { CustomButton } from "../components/ui/custom-button";
import { toast } from "react-hot-toast";
import HealthMetricsDashboard from "../components/HealthMetricsDashboard";
import DataExport from "../components/DataExport";
import AnalyticsDashboard from "../components/AnalyticsDashboard";
import UserProfile from "../components/UserProfile";
import UploadForm from "../components/UploadForm";
import SettingsPanel from "../components/SettingsPanel";

export default function DashboardPage() {
  const [uploads, setUploads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showAccountMenu, setShowAccountMenu] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [secureComputations, setSecureComputations] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const { user, logout } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [records, setRecords] = useState([]);
  const [selectedResult, setSelectedResult] = useState(null);

  const fetchRecords = async () => {
    try {
      setLoading(true);
      const token = user?.token || localStorage.getItem('token');
      
      if (!token) {
        console.error("No authentication token found");
        toast.error("Please log in again");
        router.replace('/login');
        return;
      }
      
      // Check if user is a patient and redirect to reports page if requested in URL params
      if (user?.role === 'patient' && searchParams.get('view') === 'reports') {
        router.push('/reports');
        return;
      }

      const response = await fetch(API_ENDPOINTS.uploads, {
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        }
      });

      let data = {};
      try {
        const text = await response.text();
        data = text ? JSON.parse(text) : {};
      } catch (e) {
        console.warn("Failed to parse response as JSON:", e);
        data = {};
      }

      if (response.ok) {
        console.log("Fetched records:", data);
        setRecords(Array.isArray(data) ? data : []);
      } else {
        console.error("Failed to fetch records:", response.status, data);
        if (response.status === 401) {
          toast.error("Session expired. Please log in again");
          router.replace('/login');
        } else if (response.status === 429) {
          toast.error("Too many requests. Please wait a moment and try again.");
        } else {
          toast.error(data.detail || data.message || "Failed to load records");
        }
      }
    } catch (error) {
      console.error("Error fetching records:", error);
      toast.error("Failed to load records");
    } finally {
      setLoading(false);
    }
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (showAccountMenu && !event.target.closest('.account-menu')) {
        setShowAccountMenu(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showAccountMenu]);

  const fetchSecureComputations = async () => {
    // Skip secure computation API calls for patient users
    if (user?.role === 'patient') {
      console.log("Skipping secure computations fetch for patient user");
      return;
    }

    try {
      const token = user?.token || localStorage.getItem('token');
      
      if (!token) {
        console.error("No authentication token found");
        return;
      }

      // Use fetchApi utility instead of direct fetch to handle errors properly
      const data = await fetchApi(API_ENDPOINTS.secureComputations, {
        method: 'GET',
        token
      });
      
      console.log("Fetched secure computations:", data);
      setSecureComputations(data);
      setError(null); // Clear any previous errors
    } catch (error) {
      console.error("Error fetching secure computations:", error);
      // Display error message to user
      setError(`Error fetching secure computations: ${error.message}`);
      toast.error(`Error fetching secure computations: ${error.message}`);
    }
  };

  useEffect(() => {
    if (user?.token) {
      fetchRecords();
      // Only fetch secure computations for non-patient users
      if (user?.role !== 'patient') {
        fetchSecureComputations();
      }
    }
  }, [user?.token, user?.role]); // Depend on token and role

  // Remove fetchRecords from dependencies of other useEffects
  useEffect(() => {
    if (!user) {
      router.replace('/login');
      return;
    }

    // Check for upload success
    const uploadSuccess = searchParams.get("upload_success");
    const recordId = searchParams.get("record_id");
    if (uploadSuccess === "true" && recordId) {
      toast.success(`Record ${recordId} uploaded successfully!`);
    }
  }, [user, searchParams, router]);

  useEffect(() => {
    if (searchParams.get('view') === 'results' && searchParams.get('id')) {
      fetchResult(searchParams.get('id'));
    }
  }, [searchParams]);

  const fetchUploads = async () => {
    try {
      const res = await fetch(API_ENDPOINTS.uploads, {
        headers: {
          Authorization: `Bearer ${user.token}`,
        },
      });
      
      if (res.ok) {
        const data = await res.json();
        setUploads(data);
      } else if (res.status === 401) {
        logout();
      } else {
        setError("Failed to fetch uploads");
      }
    } catch (e) {
      setError("Network error");
    } finally {
      setLoading(false);
    }
  };

  const fetchResult = async (id) => {
    try {
      const response = await fetch(API_ENDPOINTS.results(id), {
        headers: {
          'Authorization': `Bearer ${user.token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setSelectedResult(data);
        toast.success('Result loaded successfully');
      } else {
        console.error('Failed to fetch result:', await response.text());
        toast.error('Failed to load result');
      }
    } catch (error) {
      console.error('Error fetching result:', error);
      toast.error('Error loading result');
    }
  };

  const handleDelete = async (uploadId) => {
    if (!confirm("Are you sure you want to delete this upload? This action cannot be undone.")) {
      return;
    }

    setDeletingId(uploadId);
    try {
      const res = await fetch(API_ENDPOINTS.uploadById(uploadId), {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${user.token}`,
        },
      });

      if (res.ok) {
        toast.success("Upload deleted successfully");
        // Remove the deleted upload from the state
        setUploads(uploads.filter(upload => upload.id !== uploadId));
      } else {
        const error = await res.json();
        throw new Error(error.detail || "Failed to delete upload");
      }
    } catch (err) {
      toast.error(err.message);
    } finally {
      setDeletingId(null);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="w-5 h-5" />;
      case "processing":
        return <RefreshCw className="w-5 h-5 animate-spin" />;
      case "error":
        return <XCircle className="w-5 h-5" />;
      default:
        return <Clock className="w-5 h-5" />;
    }
  };

  const getStatusStyle = (status) => {
    switch (status) {
      case "completed":
        return "bg-green-100 text-green-800 border-green-200";
      case "processing":
        return "bg-yellow-100 text-yellow-800 border-yellow-200";
      case "error":
        return "bg-red-100 text-red-800 border-red-200";
      default:
        return "bg-gray-100 text-gray-800 border-gray-200";
    }
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.5
      }
    }
  };

  const stats = [
    { label: 'Total Records', value: records.length, icon: <FileText className="w-6 h-6 text-blue-500" /> },
    { label: 'Processing', value: records.filter(r => r.status === 'processing').length, icon: <RefreshCw className="w-6 h-6 text-yellow-500" /> },
    { label: 'Completed', value: records.filter(r => r.status === 'completed').length, icon: <CheckCircle className="w-6 h-6 text-green-500" /> },
    { label: 'Failed', value: records.filter(r => r.status === 'error').length, icon: <XCircle className="w-6 h-6 text-red-500" /> }
  ];

  // Define available tabs based on user permissions
  const getAvailableTabs = () => [
    { 
      id: 'overview', 
      label: 'Overview', 
      icon: <BarChart2 className="w-5 h-5" />,
      requiredPermissions: [] // Available to all authenticated users
    },
    { 
      id: 'records', 
      label: 'Records', 
      icon: <FileText className="w-5 h-5" />,
      requiredPermissions: [PERMISSIONS.READ_PATIENT_DATA]
    },
    { 
      id: 'uploads', 
      label: 'Uploads', 
      icon: <UploadCloud className="w-5 h-5" />,
      requiredPermissions: [PERMISSIONS.WRITE_PATIENT_DATA]
    },
    { 
      id: 'secure-computations', 
      label: 'Secure Computations', 
      icon: <Shield className="w-5 h-5" />,
      requiredPermissions: [PERMISSIONS.READ_PATIENT_DATA]
    },
    { 
      id: 'metrics', 
      label: 'Health Metrics', 
      icon: <Activity className="w-5 h-5" />,
      requiredPermissions: [PERMISSIONS.READ_PATIENT_DATA]
    },
    { 
      id: 'analytics', 
      label: 'Analytics', 
      icon: <LineChart className="w-5 h-5" />,
      requiredPermissions: [PERMISSIONS.VIEW_ANALYTICS]
    },
    { 
      id: 'sharing', 
      label: 'Data Sharing', 
      icon: <Users className="w-5 h-5" />,
      requiredPermissions: [PERMISSIONS.SHARE_RECORDS]
    },
    { 
      id: 'export', 
      label: 'Export', 
      icon: <Download className="w-5 h-5" />,
      requiredPermissions: [PERMISSIONS.EXPORT_DATA]
    }
  ].filter(tab => 
    tab.requiredPermissions.every(permission => 
      user?.permissions?.includes(permission)
    )
  );

  const renderOverviewTab = () => (
    <div className="space-y-6">
      {/* User Overview Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Organization Info */}
        <motion.div
          variants={itemVariants}
          className="bg-white rounded-xl shadow-sm p-6 border border-gray-200"
        >
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg">
              <Building2 className="h-6 w-6 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Organization</h3>
              <p className="text-sm text-gray-500">Your healthcare institution</p>
            </div>
          </div>
          <div className="mt-6 space-y-4">
            <div>
              <p className="text-sm text-gray-500">Name</p>
              <p className="text-base font-medium text-gray-900">{user?.name || 'N/A'}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Email</p>
              <p className="text-base font-medium text-gray-900">{user?.email || 'N/A'}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Type</p>
              <p className="text-base font-medium text-gray-900 capitalize">{user?.type || 'N/A'}</p>
            </div>
          </div>
        </motion.div>

        {/* Role & Permissions */}
        <motion.div
          variants={itemVariants}
          className="bg-white rounded-xl shadow-sm p-6 border border-gray-200"
        >
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-gradient-to-br from-purple-500 to-purple-600 rounded-lg">
              <Shield className="h-6 w-6 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Role & Access</h3>
              <p className="text-sm text-gray-500">Your permissions and access level</p>
            </div>
          </div>
          <div className="mt-6 space-y-4">
            <div>
              <p className="text-sm text-gray-500">Role</p>
              <p className="text-base font-medium text-gray-900 capitalize">{user?.role || 'N/A'}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Permissions</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {user?.permissions?.map((permission, index) => (
                  <span
                    key={index}
                    className="px-3 py-1 bg-purple-50 text-purple-700 rounded-full text-sm font-medium"
                  >
                    {permission}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </motion.div>

        {/* Analytics Summary */}
        <motion.div
          variants={itemVariants}
          className="bg-white rounded-xl shadow-sm p-6 border border-gray-200"
        >
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-gradient-to-br from-green-500 to-green-600 rounded-lg">
              <BarChart2 className="h-6 w-6 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Analytics</h3>
              <p className="text-sm text-gray-500">Data exchange metrics</p>
            </div>
          </div>
          <div className="mt-6 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-green-50 rounded-lg p-4">
                <p className="text-sm text-green-600 font-medium">Success Rate</p>
                <p className="text-2xl font-bold text-green-700">
                  {records.length ? 
                    Math.round((records.filter(r => r.status === 'completed').length / records.length) * 100) : 0}%
                </p>
              </div>
              <div className="bg-blue-50 rounded-lg p-4">
                <p className="text-sm text-blue-600 font-medium">Total Data</p>
                <p className="text-2xl font-bold text-blue-700">{records.length}</p>
              </div>
            </div>
            <div className="pt-4">
              <div className="flex items-center justify-between text-sm mb-2">
                <span className="text-gray-500">Processing Status</span>
                <span className="text-gray-900 font-medium">
                  {records.filter(r => r.status === 'processing').length} active
                </span>
              </div>
              <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-green-500 rounded-full transition-all duration-500"
                  style={{
                    width: `${records.length ? 
                      (records.filter(r => r.status === 'completed').length / records.length) * 100 : 0}%`
                  }}
                />
              </div>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Recent Activity Timeline */}
      <motion.div
        variants={itemVariants}
        className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden"
      >
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-4">
              <h2 className="text-xl font-semibold text-gray-900">Recent Activity</h2>
              <span className="px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-sm font-medium">
                Last 7 days
              </span>
            </div>
            <button
              onClick={fetchRecords}
              className="p-2 text-gray-400 hover:text-gray-500"
            >
              <RefreshCw className="w-5 h-5" />
            </button>
          </div>

          <div className="space-y-6">
            {records.slice(0, 5).map((record, index) => (
              <div key={record.id} className="flex items-start space-x-4">
                <div className={`p-2 rounded-lg ${
                  record.status === 'completed' ? 'bg-green-100' :
                  record.status === 'processing' ? 'bg-yellow-100' :
                  'bg-red-100'
                }`}>
                  {getStatusIcon(record.status)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {record.filename}
                  </p>
                  <p className="text-sm text-gray-500">
                    {new Date(record.created_at).toLocaleDateString()} at {new Date(record.created_at).toLocaleTimeString()}
                  </p>
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => router.push(`/result/${record.id}`)}
                    className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                  >
                    View Details
                  </button>
                </div>
              </div>
            ))}
          </div>

          {records.length > 5 && (
            <div className="mt-6 text-center">
              <button
                onClick={() => setActiveTab('records')}
                className="text-sm text-blue-600 hover:text-blue-700 font-medium"
              >
                View All Activity
              </button>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  // If user is a patient, show the patient dashboard instead
  if (user?.role?.toUpperCase() === 'PATIENT') {
    return (
      <Layout>
        <div className="container mx-auto px-4 py-8">
          <PatientDashboard />
        </div>
      </Layout>
    );
  }

  return (
    <RoleProtectedRoute>
      <div className="min-h-screen bg-gray-50">
        {/* Top Navigation Bar */}
        <nav className="bg-white shadow-sm border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              <div className="flex items-center">
                <Activity className="w-8 h-8 text-blue-600" />
                <h1 className="ml-2 text-2xl font-bold text-gray-900">Health Data Exchange</h1>
              </div>
              
              <div className="flex items-center space-x-4">
                {/* Show admin settings link if user is admin */}
                {user?.isAdmin && (
                  <button
                    onClick={() => router.push('/admin')}
                    className="p-2 text-gray-400 hover:text-gray-500"
                  >
                    <Settings className="w-6 h-6" />
                  </button>
                )}
                
                {/* Notifications - visible to all users */}
                <button className="p-2 text-gray-400 hover:text-gray-500">
                  <Bell className="w-6 h-6" />
                </button>

                {/* User Menu */}
                <div className="relative account-menu">
                  <button
                    onClick={() => setShowAccountMenu(!showAccountMenu)}
                    className="flex items-center space-x-3 p-2 rounded-lg hover:bg-gray-100"
                  >
                    <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
                      <User className="w-5 h-5 text-blue-600" />
                    </div>
                    <span className="text-sm font-medium text-gray-700">{user?.email}</span>
                    <ChevronDown className="w-4 h-4 text-gray-500" />
                  </button>
                  
                  {showAccountMenu && (
                    <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg py-1 z-10 border border-gray-200">
                      <button
                        onClick={() => router.push('/profile')}
                        className="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 w-full"
                      >
                        <User className="w-4 h-4 mr-2" />
                        Profile
                      </button>
                      <button
                        onClick={() => router.push('/settings')}
                        className="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 w-full"
                      >
                        <Settings className="w-4 h-4 mr-2" />
                        Settings
                      </button>
                      <button
                        onClick={() => router.push('/help')}
                        className="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 w-full"
                      >
                        <HelpCircle className="w-4 h-4 mr-2" />
                        Help
                      </button>
                      <hr className="my-1 border-gray-200" />
                      <button
                        onClick={logout}
                        className="flex items-center px-4 py-2 text-sm text-red-600 hover:bg-red-50 w-full"
                      >
                        <LogOut className="w-4 h-4 mr-2" />
                        Logout
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </nav>

        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Quick Stats */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            {stats.map((stat, index) => (
              <motion.div
                key={stat.label}
                variants={itemVariants}
                initial="hidden"
                animate="visible"
                className="bg-white rounded-xl shadow-sm p-6 border border-gray-200"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-500">{stat.label}</p>
                    <p className="mt-2 text-3xl font-bold text-gray-900">{stat.value}</p>
                  </div>
                  {stat.icon}
                </div>
              </motion.div>
            ))}
          </div>

          {/* Main Content Tabs */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="border-b border-gray-200">
              <nav className="flex space-x-8 px-6" aria-label="Tabs">
                {getAvailableTabs().map(tab => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center space-x-2 py-4 px-1 border-b-2 font-medium text-sm ${
                      activeTab === tab.id
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }`}
                  >
                    {tab.icon}
                    <span>{tab.label}</span>
                  </button>
                ))}
              </nav>
            </div>

            <div className="p-6">
              {activeTab === 'overview' ? (
                renderOverviewTab()
              ) : activeTab === 'records' ? (
                <RoleProtectedRoute requiredPermissions={[PERMISSIONS.READ_PATIENT_DATA]}>
                  <div>
                    <div className="flex justify-between items-center mb-6">
                      <div className="flex items-center space-x-4">
                        <h2 className="text-xl font-semibold text-gray-900">Recent Records</h2>
                        <button
                          onClick={fetchRecords}
                          className="p-2 text-gray-400 hover:text-gray-500"
                        >
                          <RefreshCw className="w-5 h-5" />
                        </button>
                      </div>
                      
                      <CustomButton
                        onClick={() => setActiveTab('uploads')}
                        className="flex items-center space-x-2 bg-blue-600 hover:bg-blue-700"
                      >
                        <Plus className="w-5 h-5" />
                        <span>Upload Records</span>
                      </CustomButton>
                    </div>

                    {/* Records List */}
                    {loading ? (
                      <div className="flex justify-center items-center h-64">
                        <RefreshCw className="w-8 h-8 text-blue-500 animate-spin" />
                      </div>
                    ) : error ? (
                      <div className="flex justify-center items-center h-64 text-red-500">
                        <AlertCircle className="w-6 h-6 mr-2" />
                        <span>{error}</span>
                      </div>
                    ) : (
                      <motion.div
                        variants={containerVariants}
                        initial="hidden"
                        animate="visible"
                        className="grid gap-4"
                      >
                        {records.map((record) => (
                          <motion.div
                            key={record.id}
                            variants={itemVariants}
                            className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-shadow"
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center space-x-3">
                                <div className="p-2 bg-blue-50 rounded-lg">
                                  <FileText className="w-5 h-5 text-blue-600" />
                                </div>
                                <div>
                                  <h3 className="text-sm font-medium text-gray-900">{record.filename}</h3>
                                  <p className="text-sm text-gray-500">{new Date(record.created_at).toLocaleDateString()}</p>
                                </div>
                              </div>
                              
                              <div className="flex items-center space-x-4">
                                <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium border ${getStatusStyle(record.status)}`}>
                                  {getStatusIcon(record.status)}
                                  <span className="ml-2">{record.status}</span>
                                </span>
                                
                                <button
                                  onClick={() => handleDelete(record.id)}
                                  disabled={deletingId === record.id}
                                  className="p-2 text-gray-400 hover:text-red-500 transition-colors"
                                >
                                  {deletingId === record.id ? (
                                    <RefreshCw className="w-5 h-5 animate-spin" />
                                  ) : (
                                    <Trash2 className="w-5 h-5" />
                                  )}
                                </button>
                              </div>
                            </div>
                          </motion.div>
                        ))}
                      </motion.div>
                    )}
                  </div>
                </RoleProtectedRoute>
              ) : activeTab === 'metrics' ? (
                <RoleProtectedRoute requiredPermissions={[PERMISSIONS.READ_PATIENT_DATA]}>
                  <div>
                    <div className="flex justify-between items-center mb-6">
                      <div className="flex items-center space-x-4">
                        <h2 className="text-xl font-semibold text-gray-900">Health Metrics Dashboard</h2>
                      </div>
                    </div>
                    <HealthMetricsDashboard patientData={records} />
                  </div>
                </RoleProtectedRoute>
              ) : activeTab === 'secure-computations' ? (
                // Hide secure computations tab for patient users
                user?.role === 'patient' ? (
                  <div className="bg-gray-50 rounded-lg p-8 text-center">
                    <Shield className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">Access Restricted</h3>
                    <p className="text-gray-500">Secure computations are not available for patient accounts.</p>
                  </div>
                ) : (
                  <RoleProtectedRoute requiredPermissions={[PERMISSIONS.READ_PATIENT_DATA]}>
                    <div>
                      <div className="flex justify-between items-center mb-6">
                        <div className="flex items-center space-x-4">
                          <h2 className="text-xl font-semibold text-gray-900">Secure Computations</h2>
                        </div>
                        <CustomButton
                          onClick={() => router.push('/secure-computations')}
                          className="flex items-center space-x-2 bg-blue-600 hover:bg-blue-700"
                        >
                          <Plus className="w-5 h-5" />
                          <span>New Secure Computation</span>
                        </CustomButton>
                      </div>
                      
                      {secureComputations && secureComputations.length > 0 ? (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                          {secureComputations.slice(0, 6).map(computation => (
                            <div 
                              key={computation.computation_id} 
                              className="bg-white border rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
                              onClick={() => router.push(`/secure-computations?id=${computation.computation_id}`)}
                            >
                              <div className="flex justify-between items-start mb-2">
                                <h3 className="font-medium text-gray-900 truncate">
                                  {computation.title || 'Untitled Computation'}
                                </h3>
                                <span className={`text-xs px-2 py-1 rounded-full ${computation.status === 'COMPLETED' ? 'bg-green-100 text-green-800' : computation.status === 'FAILED' ? 'bg-red-100 text-red-800' : computation.status === 'IN_PROGRESS' ? 'bg-blue-100 text-blue-800' : 'bg-yellow-100 text-yellow-800'}`}>
                                  {computation.status?.replace('_', ' ') || 'PENDING'}
                                </span>
                              </div>
                              <p className="text-sm text-gray-500 mb-3 truncate">
                                {computation.description || 'No description provided'}
                              </p>
                              <div className="flex justify-between items-center text-xs text-gray-500">
                                <span>Function: {computation.function_type || 'Average'}</span>
                                <span>{computation.created_at ? new Date(computation.created_at).toLocaleDateString() : 'N/A'}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="bg-gray-50 rounded-lg p-8 text-center">
                          <Shield className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                          <h3 className="text-lg font-medium text-gray-900 mb-2">No Secure Computations Yet</h3>
                          <p className="text-gray-500 mb-4">Start a new secure computation to analyze health data across institutions while preserving privacy.</p>
                          <CustomButton
                            onClick={() => router.push('/secure-computations')}
                            className="flex items-center space-x-2 bg-blue-600 hover:bg-blue-700"
                          >
                            <Plus className="w-5 h-5" />
                            <span>Start New Computation</span>
                          </CustomButton>
                        </div>
                      )}
                      
                      {secureComputations && secureComputations.length > 6 && (
                        <div className="mt-4 text-center">
                          <button
                            onClick={() => router.push('/secure-computations')}
                            className="text-blue-500 hover:text-blue-700 font-medium"
                          >
                            View All Secure Computations
                          </button>
                        </div>
                      )}
                    </div>
                  </RoleProtectedRoute>
                )
              ) : activeTab === 'analytics' ? (
                <RoleProtectedRoute requiredPermissions={[PERMISSIONS.VIEW_ANALYTICS]}>
                  <div>
                    <div className="flex justify-between items-center mb-6">
                      <div className="flex items-center space-x-4">
                        <h2 className="text-xl font-semibold text-gray-900">Analytics Dashboard</h2>
                      </div>
                    </div>
                    <AnalyticsDashboard data={records} />
                  </div>
                </RoleProtectedRoute>
              ) : activeTab === 'uploads' ? (
                <RoleProtectedRoute requiredPermissions={[PERMISSIONS.WRITE_PATIENT_DATA]}>
                  <div>
                    <div className="flex justify-between items-center mb-6">
                      <div className="flex items-center space-x-4">
                        <h2 className="text-xl font-semibold text-gray-900">Upload Health Records</h2>
                      </div>
                      <CustomButton
                        onClick={() => router.push('/upload')}
                        className="flex items-center space-x-2 bg-blue-600 hover:bg-blue-700"
                      >
                        <Plus className="w-5 h-5" />
                        <span>Advanced Upload</span>
                      </CustomButton>
                    </div>
                    <UploadForm onUploadSuccess={fetchRecords} />
                  </div>
                </RoleProtectedRoute>
              ) : activeTab === 'export' ? (
                <RoleProtectedRoute requiredPermissions={[PERMISSIONS.EXPORT_DATA]}>
                  <div>
                    <div className="flex justify-between items-center mb-6">
                      <div className="flex items-center space-x-4">
                        <h2 className="text-xl font-semibold text-gray-900">Data Export</h2>
                      </div>
                    </div>
                    <DataExport data={records} />
                  </div>
                </RoleProtectedRoute>
              ) : (
                <div className="flex justify-center items-center h-64 text-gray-500">
                  <p>Content for {activeTab} tab coming soon...</p>
                </div>
              )}
            </div>
          </div>
        </main>
      </div>
    </RoleProtectedRoute>
  );
}
