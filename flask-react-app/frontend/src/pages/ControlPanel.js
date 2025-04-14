import React, { useState, useEffect } from 'react';
import { apiService } from '../services/api.service';
import { INTERVALS } from '../constants/api';
import Button from '../components/Button';
import LoadingSpinner from '../components/LoadingSpinner';
import io from 'socket.io-client';
import { API_BASE_URL } from '../constants/api';
import ScanTrace from '../components/ScanTrace';

const ControlPanel = () => {
  const [error, setError] = useState(null);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState({});

  // Fetch hello message on component mount
  useEffect(() => {
    const fetchMessage = async () => {
      try {
        const data = await apiService.getHelloMessage();
        setMessage(data.message);
        setLoading(false);
      } catch (error) {
        setMessage('API ile iletişim kurulamadı.');
        setLoading(false);
      }
    };

    fetchMessage();
    const intervalId = setInterval(fetchMessage, INTERVALS.HELLO_MESSAGE);

    return () => clearInterval(intervalId);
  }, []);

  useEffect(() => {
    // Initialize socket connection
    const socketConnection = io(API_BASE_URL);

    // Socket event handlers
    socketConnection.on('robot_status', (data) => {
      setStatus(data);
      setLoading(false);
    });

    socketConnection.on('connect_error', (err) => {
      setError(`WebSocket bağlantı hatası: ${err.message}`);
      setLoading(false);
    });

    // Cleanup function
    return () => {
      if (socketConnection) {
        socketConnection.disconnect();
      }
    };
  }, []);

  // Start scan function
  const handleStartScan = async () => {
    try {
      await apiService.controlScan('START');
      setStatus({ ...status, scan_active: true });
    } catch (error) {
      setError('Scan başlatılırken bir hata oluştu.');
    }
  };

  // Stop scan function
  const handleStopScan = async () => {
    try {
      await apiService.controlScan('STOP');
      setStatus({ ...status, scan_active: false });
    } catch (error) {
      setError('Scan durdurulurken bir hata oluştu.');
    }
  };

  return (
    <div className="w-full min-h-screen p-4 sm:p-6 md:p-8 lg:p-12 bg-gray-100 flex flex-col">
      <div className="max-w-7xl mx-auto w-full flex-grow bg-white shadow-sm rounded-lg p-6 sm:p-8">
        <div className="mb-6 md:mb-8 text-center">
          <h1 className="text-3xl font-bold leading-tight mt-0 mb-2">
            Robot Kontrol Paneli
          </h1>
          {loading ? (
            <LoadingSpinner text="Bağlantı kuruluyor..." />
          ) : (
            <div className="text-gray-600 text-sm md:text-base italic">{message}</div>
          )}
        </div>
        <div className="flex flex-col justify-center items-center md:flex-row gap-4 mb-6">
          <Button
            text="Taramayı Başlat"
            type="success"
            onClick={handleStartScan}
            disabled={status.scan_active}
            className="w-full md:w-auto"
          />
          <Button
            text="Taramayı Durdur"
            type="danger"
            onClick={handleStopScan}
            disabled={!status.scan_active}
            className="w-full md:w-auto"
          />
        </div>
        <div>
          <ScanTrace/>
        </div>
        {error && (
          <div className="bg-red-50 p-4 rounded-md border border-red-200">
            <h3 className="text-lg font-semibold mb-3 text-red-700">Hata</h3>
            <p className="text-red-700">{error}</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default ControlPanel;
