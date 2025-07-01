// API configuration constants
const DEVICE_IP = process.env.REACT_APP_DEVICE_IP
const PORT = process.env.REACT_APP_PORT
if (!DEVICE_IP || !PORT) {
  throw new Error('Environment variables REACT_APP_DEVICE_IP and REACT_APP_PORT must be set');
}

export const API_BASE_URL = `http://${DEVICE_IP}:${PORT}`;
console.log('API_BASE_URL:', API_BASE_URL);
// API endpoints
export const ENDPOINTS = {
  HELLO: '/api/hello',
  SCAN: '/api/scan',
  ROBOT_STATUS: '/api/robot/status',
  AIR: '/api/robot/air',
  SCAN_LOG: '/api/scan/log',
  LATEST_SCAN: '/api/scan/latest',
  COLORS: '/api/scan/colors',
  DOWNLOAD_EXCEL: '/api/scan/download-excel',
  CONFIG: '/api/scan/config',
  SET_INDEX: '/api/scan/index/set',
  HISTORY: '/api/scan/history'
};

// Polling intervals (in milliseconds)
export const INTERVALS = {
  HELLO_MESSAGE: 5000,
  ROBOT_STATUS: 100,
  SCAN_LOG: 5000
};