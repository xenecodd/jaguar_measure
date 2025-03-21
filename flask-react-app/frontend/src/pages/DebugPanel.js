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

    fetchRobotStatus();
    const intervalId = setInterval(fetchRobotStatus, INTERVALS.ROBOT_STATUS);
    
    return () => clearInterval(intervalId);
  }, []);

  const handleAirSignal = async () => {
    try {
      await apiService.sendAirSignal();
      alert('Air signal sent successfully');
    } catch (error) {
      alert('Error sending air signal');
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
        <h1 className="text-2xl font-bold text-jaguar-blue">Robot Durum Paneli</h1>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
        <StatusCard title="DI8" value={robotStatus.DI8} />
        <StatusCard title="DI9" value={robotStatus.DI9} />
        <StatusCard title="DI0" value={robotStatus.DI0} />
        <StatusCard title="Scan Aktif" value={robotStatus.scan_active} isBoolean={true} />
        <StatusCard title="Monitor Aktif" value={robotStatus.monitor_active} isBoolean={true} />
      </div>

      <div className="mb-6">
        <Button 
          text="Hava Sinyali Gönder" 
          onClick={handleAirSignal}
          type="primary"
        />
      </div>

      <div className="bg-gray-50 p-4 rounded-md">
        <h3 className="text-lg font-semibold mb-2 text-gray-700">Dijital Giriş Bilgileri</h3>
        <p className="text-gray-600">
          Bu panel, robotun dijital girişlerinin geri dönüşlerini gösterir.
        </p>
      </div>
    </div>
  );
};

export default DebugPanel;
