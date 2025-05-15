import React, { useState, useEffect, useCallback } from 'react';
import { apiService } from '../services/api.service';
import { API_BASE_URL } from '../constants/api';
import StatusCard from '../components/StatusCard';
import LoadingSpinner from '../components/LoadingSpinner';
import Button from '../components/Button';
import io from 'socket.io-client';
import { toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { ToastContainer } from 'react-toastify';
import Config from '../components/Config';
/**
 * DebugPanel - Component for monitoring and controlling robot systems
 * Displays real-time robot status and logs through WebSocket connection
 */
const DebugPanel = () => {
  // State management
  const [scanLog, setScanLog] = useState([]);
  const [status, setStatus] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [airSignalSent, setAirSignalSent] = useState(false);

  // Connect to WebSocket and fetch logs
  useEffect(() => {
    // Initialize socket connection with better error handling
    const socketConnection = io(API_BASE_URL, {
      timeout: 5000,       // Connection timeout
      reconnectionAttempts: 5,
      reconnectionDelay: 1000
    });

    // Set timeout to exit loading state if no connection
    const loadingTimeout = setTimeout(() => {
      if (loading) {
        setLoading(false);
        setError("Connection timeout - server may be unavailable");
      }
    }, 7000);

    // Socket event handlers
    socketConnection.on('connect', () => {
      setError(null);
      setLoading(false);
    });

    socketConnection.on('robot_status', (data) => {
      clearTimeout(loadingTimeout);
      setStatus(data);
      setLoading(false);
      setError(null);
    });

    // Fetch scan logs with error handling and timeout
    const fetchScanLog = async () => {
      try {
        const response = await Promise.race([
          apiService.getScanLog(),
          new Promise((_, reject) =>
            setTimeout(() => reject(new Error("Fetch timeout")), 5000)
          )
        ]);

        // Handle different response formats
        const logs = response?.logs || response?.data?.logs || [];
        setScanLog(logs);
      } catch (err) {
        console.error("Error fetching logs:", err);
        // Don't set error state here to avoid UI changes if socket is working
      }
    };

    fetchScanLog();

    // Cleanup function
    return () => {
      clearTimeout(loadingTimeout);
      if (socketConnection) {
        socketConnection.disconnect();
      }
    };
  }, [loading]);

  // Refresh logs periodically with exponential backoff on failure
  // useEffect(() => {
  //   let retryDelay = 5000; // Start with 5 seconds
  //   let maxDelay = 30000;  // Max delay of 30 seconds
  //   let consecutiveErrors = 0;

  //   const fetchLogsWithBackoff = async () => {
  //     try {
  //       const response = await Promise.race([
  //         apiService.getScanLog(),
  //         new Promise((_, reject) =>
  //           setTimeout(() => reject(new Error("Fetch timeout")), 5000)
  //         )
  //       ]);

  //       const logs = response?.logs || response?.data?.logs || [];
  //       setScanLog(logs);

  //       // Reset on success
  //       consecutiveErrors = 0;
  //       retryDelay = 5000;
  //     } catch (err) {
  //       console.error("Error refreshing logs:", err);
  //       consecutiveErrors++;

  //       // Implement exponential backoff
  //       if (consecutiveErrors > 1) {
  //         retryDelay = Math.min(retryDelay * 1.5, maxDelay);
  //       }
  //     }
  //   };

  //   // Set up interval with current delay
  //   const logInterval = setInterval(fetchLogsWithBackoff, retryDelay);

  //   return () => clearInterval(logInterval);
  // }, []);

  // Auto-scroll log container when new logs arrive
  useEffect(() => {
    const container = document.getElementById('log-container');
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }, [scanLog]);

  // Handle air signal button press with debounce
  const handleAirSignal = useCallback(async () => {
    if (airSignalSent) return; // Prevent multiple clicks

    try {
      setAirSignalSent(true);

      // Add timeout to prevent hanging on API call
      const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => reject(new Error("Air signal timeout")), 3000);
      });

      await Promise.race([
        apiService.sendAirSignal(),
        timeoutPromise
      ]);

      // Reset button after delay
      toast.success("Air signal sent successfully");
      setTimeout(() => setAirSignalSent(false), 1500);
    } catch (error) {
      console.error("Air signal error:", error);
      toast.error(`Error sending air signal: ${error.message || "Unknown error"}`);
      setAirSignalSent(false);
    }
  }, [airSignalSent]);

  // Determine log entry styling based on log level
  const getLogStyle = (logEntry) => {
    if (logEntry.includes(' - ERROR - ')) return 'text-red-600';
    if (logEntry.includes(' - WARNING - ')) return 'text-yellow-600';
    return 'text-green-600';
  };

  // Health check function for server connectivity
  const checkServerHealth = async () => {
    try {
      await apiService.getHelloMessage();
      return true;
    } catch (err) {
      toast.error("Server communication error. Please check your connection.");
      return false;
    }
  };

  // Handle manual refresh button
  const handleRefresh = async () => {
    const isHealthy = await checkServerHealth();

    if (isHealthy) {
      try {
        const response = await apiService.getScanLog();
        setScanLog(response?.logs || response?.data?.logs || []);
        toast.success("Logs refreshed successfully");
      } catch (err) {
        toast.error("Error refreshing logs: " + err.message);
      }
    }
  };

  // Loading state
  if (loading) {
    return <LoadingSpinner text="Robot durumu yükleniyor..." />;
  }

  // Error state with retry button
  if (error) {
    return (
      <div className="bg-red-50 p-6 rounded-lg text-center">
        <h2 className="text-xl font-bold text-red-600 mb-4">Hata</h2>
        <p className="text-red-500">{error}</p>
        <Button
          text="Yeniden Dene"
          onClick={() => window.location.reload()}
          type="primary"
          className="mt-4"
        />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6 bg-white shadow-md rounded-lg">
      <ToastContainer
        position="top-right"
        autoClose={3000}
      />
      <div className="mb-6 flex justify-between items-center">
        <h1 className="text-2xl font-bold text-jaguar-blue">Robot Debug Panel</h1>
        <div className="text-sm text-gray-500">
          <span className="flex items-center">
            <span className="w-2 h-2 bg-green-500 rounded-full mr-2"></span>
            Connected
          </span>
        </div>
      </div>
      {/* Status Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
        <StatusCard title="Stop(DI8)" value={status.DI8} />
        <StatusCard title="Start(DI9)" value={status.DI9} />
        <StatusCard title="Vacuum(DI0)" value={status.DI0 !== undefined ? 1 - status.DI0 : undefined} />
        <StatusCard title="Scan Active" value={status.scan_active} isBoolean={true} />
        <StatusCard title="Monitor Active" value={status.monitor_active} isBoolean={true} />
      </div>

      {/* Air Signal Button */}
      <div className="mb-6">
        <Button
          text={airSignalSent ? "Signal Sent" : "Send Air Signal"}
          onClick={handleAirSignal}
          type={airSignalSent ? 'success' : 'primary'}
          disabled={airSignalSent}
        />
      </div>

      {/* Log Display */}
      <div className="bg-gray-50 p-4 rounded-md">
        <div className="flex justify-between items-center mb-2">
          <h3 className="text-lg font-semibold text-gray-700">Scan Logs</h3>
          <Button
            text="Refresh Logs"
            onClick={handleRefresh}
            type="secondary"
            className="text-xs px-2 py-1"
          />
        </div>
        <div className="max-h-64 overflow-y-auto">
          {scanLog.length > 0 ? (
            <pre
              id="log-container"
              className="text-xs text-gray-800 max-h-64 overflow-y-auto"
            >
              {scanLog.map((log, index) => (
                <div
                  key={index}
                  className={`mb-1 whitespace-pre-wrap break-words ${getLogStyle(log)}`}
                >
                  {log.trim()}
                </div>
              ))}
            </pre>
          ) : (
            <p className="text-gray-500">No logs available</p>
          )}
        </div>
      </div>
      <div className="mt-6">
        <Config />
      </div>
    </div>
  );
};

export default DebugPanel;
