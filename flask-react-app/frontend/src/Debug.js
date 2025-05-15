import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = `http://${DEVICE_IP}:${PORT}`;
console.log('API_BASE_URL:', API_BASE_URL);
function Debug() {
  const [robotStatus, setRobotStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchRobotStatus = () => {
      axios.get(`${API_BASE_URL}/api/robot/status`)
        .then(response => {
          setRobotStatus(response.data);
          setLoading(false);
        })
        .catch(error => {
          console.error('Error fetching robot status:', error);
          setLoading(false);
        });
    };

    fetchRobotStatus();
    const intervalId = setInterval(fetchRobotStatus, 100);
    return () => clearInterval(intervalId);
  }, []);

  return (
    <div>
      <h1>Robot Status</h1>
      {loading ? (
        <p>Loading...</p>
      ) : (
        <div>
          <p><strong>DI8:</strong> {robotStatus.DI8}</p>
          <p><strong>DI9:</strong> {robotStatus.DI9}</p>
          <p><strong>DI0:</strong> {robotStatus.DI0}</p>
          <p><strong>Scan Active:</strong> {robotStatus.scan_active ? 'Yes' : 'No'}</p>
          <p><strong>Monitor Active:</strong> {robotStatus.monitor_active ? 'Yes' : 'No'}</p>
        </div>
      )}
    </div>
  );
}

export default Debug;