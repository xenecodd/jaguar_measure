import React, { useState, useEffect } from 'react';
import { apiService } from '../services/api.service';
import { INTERVALS } from '../constants/api';
import StatusCard from '../components/StatusCard';
import LoadingSpinner from '../components/LoadingSpinner';
import Button from '../components/Button';

const DebugPanel = () => {
  const [robotStatus, setRobotStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [airSignalSent, setAirSignalSent] = useState(false);
  const [scanLog, setScanLog] = useState([]);

  useEffect(() => {
    const fetchRobotStatus = async () => {
      try {
        const data = await apiService.getRobotStatus();
        setRobotStatus(data);
        setLoading(false);
        setError(null);
      } catch (error) {
        console.error('Error fetching robot status:', error);
        setError('Robot durumu alırken bir hata oldu.');
        setLoading(false);
      }
    };

    // Fetch scan logs only once when the page loads
    const fetchScanLog = async () => {
      try {
        const response = await apiService.getScanLog();
        // Fix: Check if logs are directly in the response object
        if (response && response.logs) {
          setScanLog(response.logs);
        } else if (response && response.data && response.data.logs) {
          setScanLog(response.data.logs);
        }
      } catch (error) {
        console.error('Error fetching scan log:', error);
      }
    };
    
    fetchRobotStatus();
    fetchScanLog(); // Fetch logs only once on initial load
    
    const intervalId = setInterval(fetchRobotStatus, INTERVALS.ROBOT_STATUS);
    
    return () => clearInterval(intervalId);
  }, []);

  const handleAirSignal = async () => {
    try {
      await apiService.sendAirSignal();
      setAirSignalSent(true);
      // Reset the button color after 2 seconds
      setTimeout(() => setAirSignalSent(false), 1500);
    } catch (error) {
      alert('Error sending air signal');
      setAirSignalSent(false);
    }
  };

  if (loading) {
    return <LoadingSpinner text="Robot durumu yükleniyor..." />;
  }

  if (error) {
    return (
      <div className="bg-red-50 p-6 rounded-lg text-center">
        <h2 className="text-xl font-bold text-red-600 mb-4">Hata</h2>
        <p className="text-red-500">{error}</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6 bg-white shadow-md rounded-lg">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-jaguar-blue">Robot Debug Panel</h1>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
        <StatusCard title="Stop(DI8)" value={robotStatus.DI8} />
        <StatusCard title="Start(DI9)" value={robotStatus.DI9} />
        <StatusCard title="Vacuum(DI0)" value={1-robotStatus.DI0} />
        <StatusCard title="Scan Active" value={robotStatus.scan_active} isBoolean={true} />
        <StatusCard title="Monitor Active" value={robotStatus.monitor_active} isBoolean={true} />
      </div>

      <div className="mb-6">
        <Button 
          text="Send Air Signal" 
          onClick={handleAirSignal}
          type={airSignalSent ? "success" : "primary"}
          disabled={airSignalSent}
        />
      </div>

      <div className="bg-gray-50 p-4 rounded-md">
        <h3 className="text-lg font-semibold mb-2 text-gray-700">Scan Logs</h3>
        <div className="max-h-64 overflow-y-auto">
          {scanLog.length > 0 ? (
            <pre className="text-xs text-gray-800">
              {scanLog.map((log, index) => {
                // Determine log level and corresponding color
                const logLevel = log.includes(' - ERROR - ') 
                  ? 'text-red-600' 
                  : log.includes(' - WARNING - ') 
                  ? 'text-yellow-600' 
                  : 'text-green-600';

                return (
                  <div 
                    key={index} 
                    className={`mb-1 whitespace-pre-wrap break-words ${logLevel}`}
                  >
                    {log.trim()}
                  </div>
                );
              })}
            </pre>
          ) : (
            <p className="text-gray-500">No logs available</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default DebugPanel;