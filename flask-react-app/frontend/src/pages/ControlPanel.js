import React, { useState, useEffect } from 'react';
import { apiService } from '../services/api.service';
import { INTERVALS, API_BASE_URL } from '../constants/api';
import Button from '../components/Button';
import LoadingSpinner from '../components/LoadingSpinner';
import io from 'socket.io-client';
import ScanTrace from '../components/ScanTrace';
import { toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import ThreeDTrace from '../components/3DTrace';
const ControlPanel = () => {
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState({});
  const [traceValue, setTraceValue] = useState(null);
  const containerRef = React.useRef();
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
    const socketConnection = io(API_BASE_URL, {
      timeout: 5000,       // Connection timeout
      reconnectionAttempts: 5,
      reconnectionDelay: 1000
    });

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
  const handleStartScan = async (alt_button) => {
    try {
      alt_button = alt_button || false;
      const response = await apiService.controlScan({ message: 'START', alt_button });
      if (response.status === 200) {
        toast.success(response.data.message);
      }
      setStatus((prev) => ({ ...prev, scan_active: true }));
    } catch (error) {
      toast.error(error.message);
    }
  };

  const handleTraceChange = (newValue) => {
    setTraceValue(newValue);
  };

  // Taramayı durdur
  const handleStopScan = async () => {
    try {
      await apiService.controlScan({ message: 'STOP' });
      setStatus((prev) => ({ ...prev, scan_active: false }));
      toast.success('Scan durdurıldı.');
    } catch (error) {
      toast.error('Scan durdurulurken bir hata oluştu.');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 flex flex-col lg:flex-row text-white">
      {/* Sol Panel */}
      <div className="lg:w-[35%] w-full p-3 lg:p-6 lg:sticky lg:top-0 lg:h-screen overflow-auto z-20">
        <div className="flex flex-col bg-slate-800 bg-opacity-80 backdrop-blur-sm rounded-xl shadow-2xl border border-slate-700 p-6 lg:p-8 h-full">
          {/* Header */}
          <header className="mb-6">
            <div className="flex items-center justify-center space-x-2 mb-3">
              <div className="text-3xl lg:text-4xl font-bold bg-gradient-to-r from-indigo-400 to-purple-500 bg-clip-text text-transparent">
                Robot Kontrol Paneli
              </div>
            </div>
            {loading ? (
              <div className="mt-4 flex flex-col items-center justify-center">
                <LoadingSpinner text="Bağlantı kuruluyor..." />
                <div className="w-full mt-2 h-1 bg-slate-700 rounded-full overflow-hidden">
                  <div className="h-full bg-indigo-500 animate-pulse rounded-full w-1/2"></div>
                </div>
              </div>
            ) : (
              <div className="mt-3 flex items-center justify-center">
                <div className={`h-2 w-2 rounded-full animate-pulse ${!status?.scan_active ? "bg-green-500" : "bg-amber-500"} mr-2`}></div>
                <div className="text-slate-300 text-sm">{message}</div>
              </div>
            )}
          </header>
  
          {/* Status Panel */}
          <div className="flex-grow space-y-6">
            <div className="bg-slate-900 bg-opacity-50 rounded-lg p-4 border border-slate-700">
              <h3 className="text-sm font-semibold text-indigo-300 mb-2">Sistem Durumu</h3>
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="flex items-center">
                  <div className={`h-2 w-2 rounded-full animate-pulse ${status?.scan_active ? "bg-green-500" : "bg-slate-500"} mr-2`}></div>
                  <span>Tarama: {status?.scan_active ? "Aktif" : "Bekliyor"}</span>
                </div>
                <div className="flex items-center">
                  <div className={`h-2 w-2 rounded-full animate-pulse ${status?.TCP ? "bg-green-500" : "bg-slate-500"} mr-2`}></div>
                  <span>TCP Bağlantı</span>
                </div>
              </div>
            </div>
  
            {/* Butonlar */}
            <div className="space-y-4">
              {traceValue && (
                <Button
                  text="Arayüzden Taramayı Başlat"
                  type="success"
                  onClick={() => handleStartScan(true)}
                  className="w-full px-6 py-3 rounded-lg bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white font-semibold shadow-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                />
              )}
  
              <div className="grid grid-cols-2 gap-3">
                <Button
                  text="Taramayı Başlat"
                  type="success"
                  onClick={() => handleStartScan(false)}
                  disabled={status?.scan_active}
                  className="w-full px-6 py-3 rounded-lg bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white font-semibold shadow-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                />
                <Button
                  text="Taramayı Durdur"
                  type="danger"
                  onClick={handleStopScan}
                  disabled={!status?.scan_active}
                  className="w-full px-6 py-3 rounded-lg bg-gradient-to-r from-red-500 to-rose-600 hover:from-red-600 hover:to-rose-700 text-white font-semibold shadow-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Sağ Panel */}
      <div className="lg:w-[65%] w-full h-screen lg:h-auto p-3 overflow-auto">
        <div className="w-full h-full bg-slate-800 bg-opacity-80 backdrop-blur-sm rounded-xl border border-slate-700 shadow-2xl p-4 lg:p-6 flex flex-col">
          {/* Header */}
          <div className="mb-4 pb-2 border-b border-slate-700 flex items-center justify-between">
            <h3 className="text-xl lg:text-2xl font-bold text-indigo-300 flex items-center">
              <span className="mr-2">🔍</span> Tarama İzleme
              {status?.scan_active && <span className="ml-2 h-2 w-2 rounded-full bg-green-500 animate-pulse"></span>}
            </h3>
            <div className="flex space-x-2">
              <div className="px-3 py-1 bg-indigo-600 rounded-full text-xs font-medium">Tarama Verisi</div>
              <div className="px-3 py-1 bg-slate-700 rounded-full text-xs font-medium">3D Görünüm</div>
            </div>
          </div>
  
          {/* İçerikler (üstten alta: Trace küçük, 3D büyük) */}
          <div className="flex flex-col flex-grow space-y-4">
            {/* ScanTrace - %30 yükseklik */}
            <div className="h-[30%] min-h-[150px] bg-slate-900 bg-opacity-50 rounded-lg p-4 overflow-auto">
              <div className="text-xs text-slate-400 mb-2 flex justify-between">
                <span>Tarama İlerlemesi</span>
                <span className="bg-slate-800 px-2 py-1 rounded text-indigo-300">
                  {traceValue ? 'Veri alınıyor' : 'Bekleniyor'}
                </span>
              </div>
              <ScanTrace onScan={handleTraceChange} />
            </div>
  
            {/* 3D Visualization - %70 yükseklik */}
            {status?.TCP ? (
              <div className="h-[70%] bg-slate-900 bg-opacity-50 rounded-lg p-4 flex flex-col">
                <div className="text-xs text-slate-400 mb-2 flex justify-between">
                  <span>3D Konumlandırma</span>
                  <div className="flex items-center">
                    <span className="h-2 w-2 rounded-full bg-green-500 animate-pulse mr-1"></span>
                    <span className="bg-slate-800 px-2 py-1 rounded text-green-300">Aktif</span>
                  </div>
                </div>
                <div ref={containerRef} className="w-full flex-grow rounded-lg overflow-hidden border border-slate-700">
                  <ThreeDTrace
                    containerRef={containerRef}
                    tcpData={
                      status.TCP[1]
                        ? { x: status.TCP[1][0] / 7, z: status.TCP[1][1] / 7, y: status.TCP[1][2] / 7 }
                        : null
                    }
                  />
                </div>
  
                {/* Koordinatlar */}
                {status.TCP[1] && (
                  <div className="mt-2 grid grid-cols-3 gap-2 text-xs">
                    <div className="bg-slate-800 p-2 rounded text-center">
                      <span className="text-indigo-300">X:</span> {Math.round(status.TCP[1][0] * 100) / 100}
                    </div>
                    <div className="bg-slate-800 p-2 rounded text-center">
                      <span className="text-indigo-300">Y:</span> {Math.round(status.TCP[1][1] * 100) / 100}
                    </div>
                    <div className="bg-slate-800 p-2 rounded text-center">
                      <span className="text-indigo-300">Z:</span> {Math.round(status.TCP[1][2] * 100) / 100}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="h-[70%] bg-slate-900 bg-opacity-50 rounded-lg flex items-center justify-center">
                <div className="text-center p-6">
                  <div className="text-slate-500 text-4xl mb-2">📡</div>
                  <p className="text-slate-400">TCP verisi bekleniyor...</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
  
};

      export default ControlPanel;
