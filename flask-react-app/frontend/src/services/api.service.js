import axios from 'axios';
import { API_BASE_URL, ENDPOINTS } from '../constants/api';

// Create axios instance with base configuration
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Error handling interceptor
apiClient.interceptors.response.use(
  response => response,
  error => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

// API service functions
export const apiService = {
  // Get hello message
  getHelloMessage: async () => {
    try {
      const response = await apiClient.get(ENDPOINTS.HELLO);
      return response.data;
    } catch (error) {
      throw error;
    }
  },
  
  // Start or stop scan
  controlScan: async (action) => {
    try {
      const message = action.toUpperCase() === 'START' ? 'START' : 'STOP';
      const response = await apiClient.post(ENDPOINTS.SCAN, { message });
      return response.data;
    } catch (error) {
      throw error;
    }
  },
  
  getLatestScan: async () => {
    try {
      const response = await apiClient.get(ENDPOINTS.LATEST_SCAN);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Get robot status
  getRobotStatus: async () => {
    try {
      const response = await apiClient.get(ENDPOINTS.ROBOT_STATUS);
      return response.data;
    } catch (error) {
      throw error;
    }
  },
  
  // Get scan log
  getScanLog: async () => {
    try {
      const response = await apiClient.get(ENDPOINTS.SCAN_LOG);
      return response.data;
    } catch (error) {
      throw error;
    }
  },
  
  // Send air signal
  sendAirSignal: async () => {
    try {
      const response = await apiClient.post(ENDPOINTS.AIR);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  getColors: async () => {
    try {
      const response = await apiClient.get(ENDPOINTS.COLORS);
      return response.data;
    } catch (error) {
      throw error;
    }
  }
};
