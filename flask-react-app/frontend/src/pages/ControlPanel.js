import React, { useState, useEffect, useRef, useCallback } from 'react';
import { apiService } from '../services/api.service';
import { INTERVALS, API_BASE_URL } from '../constants/api';
import Button from '../components/Button';
import LoadingSpinner from '../components/LoadingSpinner';
import io from 'socket.io-client';
import ScanTrace from '../components/ScanTrace';
import { toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import ThreeDTrace from '../components/3DTrace';

// Status indicator component
const StatusIndicator = ({ active, label, size = 'sm' }) => {
  const sizeClasses = {
    sm: 'h-2 w-2',
    md: 'h-3 w-3',
    lg: 'h-4 w-4'
  };

  return (
    <div className="flex items-center gap-2">
      <div 
        className={`${sizeClasses[size]} rounded-full transition-all duration-300 ${
          active 
            ? 'bg-emerald-400 shadow-emerald-400/50 shadow-md animate-pulse' 
            : 'bg-slate-500'
        }`}
        role="status"
        aria-label={`${label}: ${active ? 'active' : 'inactive'}`}
      />
      <span className="text-sm font-medium text-slate-300">{label}</span>
    </div>
  );
};

// Coordinate display component
const CoordinateCard = ({ label, value, color = 'indigo' }) => {
  const formatCoordinate = useCallback((val) => {
    if (val === undefined || val === null) return '---';
    const formatted = Math.round(val * 100) / 100;
    return formatted.toString().length > 8 ? formatted.toFixed(1) : formatted.toString();
  }, []);

  const colorClasses = {
    indigo: 'text-indigo-300 border-indigo-500/30',
    emerald: 'text-emerald-300 border-emerald-500/30',
    amber: 'text-amber-300 border-amber-500/30'
  };

  return (
    <div className="bg-slate-800/60 backdrop-blur-sm border border-slate-600/50 rounded-lg p-2 sm:p-3 text-center transition-all duration-200 hover:border-slate-500/50">
      <div className={`text-xs font-semibold uppercase tracking-wide mb-1 ${colorClasses[color]}`}>
        {label}
      </div>
      <div 
        className="text-slate-200 font-mono text-xs sm:text-sm font-medium truncate" 
        title={value}
        role="text"
        aria-label={`${label} coordinate: ${formatCoordinate(value)}`}
      >
        {formatCoordinate(value)}
      </div>
    </div>
  );
};

const ControlPanel = () => {
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState({});
  const [traceValue, setTraceValue] = useState(null);
  const [connectionError, setConnectionError] = useState(false);
  const containerRef = useRef();
  const socketRef = useRef();

  // Memoized API call to prevent unnecessary re-renders
  const fetchMessage = useCallback(async () => {
    try {
      setConnectionError(false);
      const data = await apiService.getHelloMessage();
      setMessage(data.message);
      setLoading(false);
    } catch (error) {
      setMessage('API ile iletişim kurulamadı.');
      setConnectionError(true);
      setLoading(false);
    }
  }, []);

  // Initialize API connection
  useEffect(() => {
    fetchMessage();
    const intervalId = setInterval(fetchMessage, INTERVALS.HELLO_MESSAGE);
    return () => clearInterval(intervalId);
  }, [fetchMessage]);

  // WebSocket connection with improved error handling
  useEffect(() => {
    const socketConnection = io(API_BASE_URL, {
      timeout: 5000,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
      transports: ['websocket', 'polling']
    });

    socketRef.current = socketConnection;

    socketConnection.on('robot_status', (data) => {
      setStatus(data);
      setLoading(false);
      setConnectionError(false);
    });

    socketConnection.on('connect', () => {
      setConnectionError(false);
    });

    socketConnection.on('connect_error', (err) => {
      console.error('WebSocket connection error:', err);
      toast.error(`Bağlantı hatası: ${err.message}`);
      setConnectionError(true);
      setLoading(false);
    });

    socketConnection.on('disconnect', () => {
      setConnectionError(true);
    });

    return () => {
      if (socketConnection) {
        socketConnection.disconnect();
      }
    };
  }, []);

  const handleStartScan = useCallback(async (altButton = false) => {
    try {
      const response = await apiService.controlScan({ 
        message: 'START', 
        alt_button: altButton 
      });
      
      if (response.status === 200) {
        toast.success(response.data.message);
        setStatus((prev) => ({ ...prev, scan_active: true }));
      }
    } catch (error) {
      toast.error(error.message || 'Tarama başlatılırken hata oluştu');
    }
  }, []);

  const handleStopScan = useCallback(async () => {
    try {
      await apiService.controlScan({ message: 'STOP' });
      setStatus((prev) => ({ ...prev, scan_active: false }));
      toast.success('Tarama durduruldu.');
    } catch (error) {
      toast.error('Tarama durdurulurken hata oluştu.');
    }
  }, []);

  const handleTraceChange = useCallback((newValue) => {
    setTraceValue(newValue);
  }, []);

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
        <div className="text-center space-y-4">
          <LoadingSpinner text="Sistem başlatılıyor..." />
          <div className="w-64 h-2 bg-slate-700 rounded-full overflow-hidden">
            <div className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 animate-pulse rounded-full w-1/2"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen w-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white overflow-hidden">
      <div className="h-full w-full p-2 sm:p-3 lg:p-4">
        <div className="grid grid-cols-1 lg:grid-cols-4 grid-rows-[2fr_1fr] lg:grid-rows-[1fr_auto] gap-2 sm:gap-3 lg:gap-4 h-full">
          
          {/* Scan Monitoring */}
          <section 
            className="lg:col-span-3 bg-slate-800/40 backdrop-blur-md rounded-xl border border-slate-700/50 shadow-2xl overflow-hidden"
            role="region"
            aria-label="Tarama İzleme"
          >
            <header className="flex items-center justify-between p-2 sm:p-3 border-b border-slate-700/50 bg-slate-800/60">
              <div className="flex items-center gap-2 sm:gap-3">
                <div className="p-1.5 sm:p-2 bg-indigo-500/20 rounded-lg">
                  <span className="text-base sm:text-xl" role="img" aria-label="Arama ikonu">🔍</span>
                </div>
                <h2 className="text-base sm:text-xl font-bold text-indigo-300">Tarama İzleme</h2>
              </div>
              <StatusIndicator 
                active={status?.scan_active} 
                label={status?.scan_active ? "Aktif" : "Bekliyor"}
                size="md"
              />
            </header>
            
            <div className="h-[calc(100%-3rem)] sm:h-[calc(100%-4rem)] p-2 sm:p-3">
              <div className="w-full h-full rounded-lg overflow-hidden border border-slate-700/30">
                <ScanTrace onScan={handleTraceChange} />
              </div>
            </div>
          </section>

          {/* Control Panel - Fixed width to prevent hiding */}
          <aside 
            className="lg:col-span-1 bg-slate-800/40 backdrop-blur-md rounded-xl border border-slate-700/50 shadow-2xl overflow-hidden min-w-0"
            role="complementary"
            aria-label="Robot Kontrol Paneli"
          >
            <div className="h-full flex flex-col min-h-0">
              <header className="flex-shrink-0 p-2 sm:p-3 border-b border-slate-700/50 bg-slate-800/60">
                <h1 className="text-center text-sm sm:text-lg font-bold bg-gradient-to-r from-indigo-400 via-purple-400 to-indigo-400 bg-clip-text text-transparent mb-2 sm:mb-3">
                  Robot Kontrol Paneli
                </h1>
                
                <div className="flex items-center justify-center gap-2 p-2 sm:p-3 bg-slate-900/30 rounded-lg border border-slate-700/30">
                  <StatusIndicator 
                    active={!connectionError && !loading} 
                    label="Bağlantı"
                    size="sm"
                  />
                  <div className="text-xs sm:text-sm text-slate-300 truncate" title={message}>
                    {message}
                  </div>
                </div>
              </header>

              {/* System Status */}
              <div className="flex-shrink-0 p-2 sm:p-3 border-b border-slate-700/30">
                <h3 className="text-xs sm:text-sm font-semibold text-indigo-300 mb-2 flex items-center gap-2">
                  <span className="w-1 h-3 sm:h-4 bg-indigo-400 rounded-full"></span>
                  Sistem Durumu
                </h3>
                <div className="space-y-1.5 sm:space-y-2">
                  <StatusIndicator active={status?.scan_active} label="Tarama Durumu" />
                  <StatusIndicator active={status?.TCP} label="TCP Bağlantısı" />
                  <div className="flex items-center gap-2">
                    <StatusIndicator active={status?.MODE === 2} label="" />
                    <span className="text-xs sm:text-sm font-medium text-slate-300">
                      Mod: {status?.MODE === 0 ? "Otomatik" : "Manuel"}
                    </span>
                  </div>
                </div>
              </div>

              {/* Control Buttons - Scrollable if needed */}
              <div className="flex-1 p-2 sm:p-3 space-y-2 sm:space-y-3 overflow-y-auto min-h-0">
                {!traceValue && (
                  <Button
                    text="Arayüzden Taramayı Başlat"
                    type="success"
                    onClick={() => handleStartScan(true)}
                    className="w-full py-2 sm:py-3 px-2 sm:px-4 rounded-lg text-xs sm:text-sm bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-600 hover:to-emerald-700 text-white font-semibold shadow-lg hover:shadow-emerald-500/25 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
                    aria-label="Arayüzden taramayı başlat"
                  />
                )}
                
                <div className="grid grid-cols-1 gap-2 sm:gap-3">
                  <Button
                    text="Taramayı Başlat"
                    type="success"
                    onClick={() => handleStartScan(false)}
                    disabled={status?.scan_active}
                    className="w-full py-2 sm:py-3 px-2 sm:px-4 rounded-lg text-xs sm:text-sm bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-600 hover:to-emerald-700 text-white font-semibold shadow-lg hover:shadow-emerald-500/25 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
                    aria-label="Normal taramayı başlat"
                  />
                  <Button
                    text="Taramayı Durdur"
                    type="danger"
                    onClick={handleStopScan}
                    disabled={!status?.scan_active}
                    className="w-full py-2 sm:py-3 px-2 sm:px-4 rounded-lg text-xs sm:text-sm bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white font-semibold shadow-lg hover:shadow-red-500/25 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-red-500/50"
                    aria-label="Taramayı durdur"
                  />
                </div>
              </div>
            </div>
          </aside>

          {/* 3D Positioning - Full width on mobile, spans full width on desktop */}
          <section 
            className="lg:col-span-4 bg-slate-800/40 backdrop-blur-md rounded-xl border border-slate-700/50 shadow-2xl overflow-hidden"
            role="region"
            aria-label="3D Konumlandırma"
          >
            {status?.TCP ? (
              <div className="h-full flex flex-col">
                <header className="flex items-center justify-between p-2 sm:p-3 border-b border-slate-700/50 bg-slate-800/60">
                  <div className="flex items-center gap-2 sm:gap-3">
                    <div className="p-1.5 sm:p-2 bg-emerald-500/20 rounded-lg">
                      <span className="text-base sm:text-xl" role="img" aria-label="3D ikonu">📐</span>
                    </div>
                    <h2 className="text-base sm:text-lg font-bold text-emerald-300">3D Konumlandırma</h2>
                  </div>
                  <div className="flex items-center gap-2 px-2 sm:px-3 py-1 sm:py-1.5 bg-emerald-500/20 rounded-full border border-emerald-500/30">
                    <StatusIndicator active={true} label="" size="sm" />
                    <span className="text-emerald-300 text-xs sm:text-sm font-medium">Aktif</span>
                  </div>
                </header>

                <div className="flex-1 p-2 sm:p-3 min-h-0">
                  <div className="grid grid-cols-1 xl:grid-cols-5 gap-2 sm:gap-3 h-full">
                    {/* 3D Visualization */}
                    <div className="xl:col-span-4 h-full min-h-[200px] sm:min-h-[300px]">
                      <div 
                        ref={containerRef} 
                        className="w-full h-full rounded-lg overflow-hidden border border-slate-700/30 bg-slate-900/20"
                      >
                        <ThreeDTrace
                          containerRef={containerRef}
                          tcpData={
                            status.TCP[1]
                              ? { 
                                  x: status.TCP[1][0] / 7, 
                                  z: status.TCP[1][1] / 7, 
                                  y: status.TCP[1][2] / 7 
                                }
                              : null
                          }
                        />
                      </div>
                    </div>

                    {/* Coordinates Display */}
                    <div className="xl:col-span-1 space-y-2 sm:space-y-3">
                      <h3 className="text-xs sm:text-sm font-semibold text-slate-300 mb-2 sm:mb-3 flex items-center gap-2">
                        <span className="w-1 h-3 sm:h-4 bg-emerald-400 rounded-full"></span>
                        Koordinatlar
                      </h3>
                      {status.TCP[1] && (
                        <div className="space-y-2 sm:space-y-3">
                          <CoordinateCard 
                            label="X Ekseni" 
                            value={status.TCP[1][0]} 
                            color="indigo" 
                          />
                          <CoordinateCard 
                            label="Y Ekseni" 
                            value={status.TCP[1][1]} 
                            color="emerald" 
                          />
                          <CoordinateCard 
                            label="Z Ekseni" 
                            value={status.TCP[1][2]} 
                            color="amber" 
                          />
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="h-full flex items-center justify-center p-4 sm:p-8">
                <div className="text-center space-y-3 sm:space-y-4">
                  <div className="text-4xl sm:text-6xl text-slate-600" role="img" aria-label="Bekleme ikonu">📡</div>
                  <div className="space-y-1 sm:space-y-2">
                    <p className="text-slate-400 text-sm sm:text-lg font-medium">TCP verisi bekleniyor...</p>
                    <p className="text-slate-500 text-xs sm:text-sm">Lütfen robot bağlantısını kontrol edin</p>
                  </div>
                  <div className="flex justify-center">
                    <div className="animate-spin rounded-full h-4 w-4 sm:h-6 sm:w-6 border-b-2 border-indigo-500"></div>
                  </div>
                </div>
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
};

export default ControlPanel;