import React, { useState, useEffect } from 'react';
import { apiService } from '../services/api.service';
import { INTERVALS } from '../constants/api';
import Button from '../components/Button';
import LoadingSpinner from '../components/LoadingSpinner';

const Dashboard = () => {
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [response, setResponse] = useState(null);
  const [robotStatus, setRobotStatus] = useState({
    scan_active: false,
  });

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
    const fetchRobotStatus = async () => {
      try {
        const data = await apiService.getRobotStatus();
        setRobotStatus(data);
      } catch (error) {
        console.error('Error fetching robot status:', error);
      }
    };

    fetchRobotStatus();
    const intervalId = setInterval(fetchRobotStatus, INTERVALS.ROBOT_STATUS);
    
    return () => clearInterval(intervalId);
  }, []);

  // Start scan function
  const handleStartScan = async () => {
    try {
      const data = await apiService.controlScan('START');
      setResponse(data);
    } catch (error) {
      setResponse({ error: 'Scan başlatılırken bir hata oluştu.' });
    }
  };

  // Stop scan function
  const handleStopScan = async () => {
    try {
      const data = await apiService.controlScan('STOP');
      setResponse(data);
    } catch (error) {
      setResponse({ error: 'Scan durdurulurken bir hata oluştu.' });
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
            disabled={robotStatus.scan_active}
            className="w-full md:w-auto"
          />
          <Button 
            text="Taramayı Durdur" 
            type="danger" 
            onClick={handleStopScan} 
            disabled={!robotStatus.scan_active}
            className="w-full md:w-auto"
          />
        </div>

        {response && (
          <div className="bg-gray-50 p-4 rounded-md border border-gray-200">
            <h3 className="text-lg font-semibold mb-3 text-gray-700">Sistem Yanıtı</h3>
            {response.stdout && (
              <div className="mb-2 bg-white p-3 rounded shadow-sm">
                <span className="font-medium text-gray-600 mr-2">Çıktı:</span>
                <span className="text-gray-700">{response.stdout}</span>
              </div>
            )}
            {response.stderr && (
              <div className="mb-2 bg-red-50 p-3 rounded border border-red-200">
                <span className="font-medium text-red-600 mr-2">Hata:</span>
                <span className="text-red-700">{response.stderr}</span>
              </div>
            )}
            {response.message && (
              <div className="bg-white p-3 rounded shadow-sm">
                <span className="font-medium text-gray-600 mr-2">Mesaj:</span>
                <span className="text-gray-700">{response.message}</span>
              </div>
            )}
            {response.error && (
              <div className="mb-2 bg-red-50 p-3 rounded border border-red-200">
                <span className="font-medium text-red-600 mr-2">Hata:</span>
                <span className="text-red-700">{response.error}</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
