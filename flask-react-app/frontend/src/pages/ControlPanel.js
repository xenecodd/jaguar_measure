import React, { useState, useEffect } from 'react';
import { apiService } from '../services/api.service';
import { INTERVALS, API_BASE_URL } from '../constants/api';
import Button from '../components/Button';
import LoadingSpinner from '../components/LoadingSpinner';
import io from 'socket.io-client';
import ScanTrace from '../components/ScanTrace';
import { toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

const ControlPanel = () => {
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState({});

  // API'den 'hello' mesajını ve socket üzerinden durumu al
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

  // Socket bağlantısını başlat ve dinle
  useEffect(() => {
    const socketConnection = io(API_BASE_URL);

    socketConnection.on('robot_status', (data) => {
      setStatus(data);
      setLoading(false);
    });

    socketConnection.on('connect_error', (err) => {
      toast(`WebSocket bağlantı hatası: ${err.message}`);
      setLoading(false);
    });

    return () => {
      if (socketConnection) socketConnection.disconnect();
    };
  }, []);

  // Taramayı başlat
  const handleStartScan = async () => {
    try {
      await apiService.controlScan({ message: 'START' });
      setStatus((prev) => ({ ...prev, scan_active: true }));
    } catch (error) {
      toast('Scan başlatılırken bir hata oluştu.');
    }
  };

  // Taramayı durdur
  const handleStopScan = async () => {
    try {
      await apiService.controlScan({ message: 'STOP' });
      setStatus((prev) => ({ ...prev, scan_active: false }));
    } catch (error) {
      toast('Scan durdurulurken bir hata oluştu.');
    }
  };

  return (
    <div className="min-h-screen bg-gray-200 flex flex-col lg:flex-row">
      {/* Sol Panel: Kontrol ve Bilgilendirme */}
      <div className="lg:w-2/5 w-full h-full p-20 flex flex-col bg-gray-100">
        <div className="max-w-xl mx-auto bg-white rounded-lg shadow-lg p-8 flex flex-col flex-grow">
          <header className="mb-8 text-center">
            <h1 className="text-3xl font-extrabold text-blue-800">
              Robot Kontrol Paneli
            </h1>
            {loading ? (
              <LoadingSpinner text="Bağlantı kuruluyor..." />
            ) : (
              <p className="mt-4 text-gray-600 italic text-base">
                {message}
              </p>
            )}
          </header>

          <div className="flex flex-col md:flex-row justify-around items-center gap-4 mt-auto">
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
        </div>
      </div>

      {/* Sağ Panel: Tarama İzleme */}
      <div className="lg:w-3/5 w-full h-full p-6 flex items-center justify-center bg-gray-100">
        <div className="max-w-4xl w-full">
          <ScanTrace />
        </div>
      </div>
    </div>
  );
};

export default ControlPanel;
