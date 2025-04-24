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
    <div className="min-h-screen bg-slate-900 flex items-center justify-center text-white">
      {/* Sol Panel */}
      <div className="lg:w-[35%] w-full h-1/2 p-2 lg:p-10 flex flex-col rounded-2xl bg-slate-800 border-r border-slate-700">
        <div className="flex flex-col bg-slate-700 rounded-2xl shadow-xl p-8 lg:p-10 h-full">
          <header className="mb-8">
            <h1 className="text-3xl lg:text-4xl font-bold text-indigo-400 text-center">
              Robot Kontrol Paneli
            </h1>
            {loading ? (
              <div className="mt-4 flex justify-center">
                <LoadingSpinner text="Bağlantı kuruluyor..." />
              </div>
            ) : (
              <p className="mt-4 text-slate-300 italic text-sm text-center">{message}</p>
            )}
          </header>

          {/* Butonlar yukarı alındı ve hizalandı */}
          <div className="flex flex-col gap-4 mt-4">
            <Button
              text="Taramayı Başlat"
              type="success"
              onClick={handleStartScan}
              disabled={status.scan_active}
              className="w-full px-6 py-3 rounded-lg bg-green-500 hover:bg-green-600 text-white font-semibold shadow-md"
            />
            <Button
              text="Taramayı Durdur"
              type="danger"
              onClick={handleStopScan}
              disabled={!status.scan_active}
              className="w-full px-6 py-3 rounded-lg bg-red-500 hover:bg-red-600 text-white font-semibold shadow-md"
            />
          </div>
        </div>
      </div>

      {/* Sağ Panel */}
      <div className="lg:w-[65%] w-full h-1/2 p-1 bg-slate-900 flex items-center justify-center">
        <div className="w-full h-full bg-slate-800 rounded-2xl shadow-2xl p-6 flex flex-col">
          <h3 className="text-2xl font-bold text-indigo-300 mb-4">Tarama İzleme</h3>
          <div className="overflow-auto">
            <ScanTrace />
          </div>
        </div>
      </div>
    </div>


  );
};

export default ControlPanel;
