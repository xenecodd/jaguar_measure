// API configuration constants
export const API_BASE_URL = 'http://192.168.43.80:5000';

// API endpoints
export const ENDPOINTS = {
  HELLO: '/api/hello',
  SCAN: '/api/scan',
  ROBOT_STATUS: '/api/robot/status',
  AIR: '/api/robot/air',
  SCAN_LOG: '/api/scan/log',
  LATEST_SCAN: '/api/scan/latest'
};

// Polling intervals (in milliseconds)
export const INTERVALS = {
  HELLO_MESSAGE: 5000,
  ROBOT_STATUS: 100,
  SCAN_LOG: 100
};
