import React, { useEffect, useState } from 'react';
import { apiService } from '../services/api.service';
import { toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

const ScanTrace = () => {
  const [rectangles, setRectangles] = useState([]);
  const [ignoredPointsInput, setIgnoredPointsInput] = useState([]);

  // 64 adet gri renkli (8x8) başlangıç kutusunu oluştur
  useEffect(() => {
    const initialRectangles = Array.from({ length: 64 }, (_, i) => ({
      id: String(i),
      x: (i % 8) * 50,
      y: Math.floor(i / 8) * 50,
      fill: 'gray',
    }));
    setRectangles(initialRectangles);
  }, []);

  // API'den renk bilgisini periyodik olarak al ve güncelle
  useEffect(() => {
    const fetchColors = async () => {
      try {
        const data = await apiService.getColors();
        setRectangles((prevRects) =>
          prevRects.map((rect, idx) => ({
            ...rect,
            fill: data.colors[idx] || 'gray',
          }))
        );
      } catch (error) {
        console.error('Renkler alınırken hata oluştu:', error);
      }
    };

    fetchColors();
    const interval = setInterval(fetchColors, 200);
    return () => clearInterval(interval);
  }, []);

  // Tıklanan kutu rengini değiştir
  const handleRectClick = (id) => {
    setRectangles((prevRects) =>
      prevRects.map((rect) =>
        rect.id === id
          ? { ...rect, fill: rect.fill === 'gray' ? 'black' : 'gray' }
          : rect
      )
    );
  };

  // Ignored points listesini güncelle ve API'ye gönder
  const handleSendIgnoredPoints = async (action) => {
    try {
      const newPoints = ignoredPointsInput.includes(action)
        ? ignoredPointsInput.filter((index) => index !== action)
        : [...ignoredPointsInput, action];

      setIgnoredPointsInput(newPoints);
      handleRectClick(action);

      const response = await apiService.controlScan({ ignored_index_list: newPoints });
      toast(response);
    } catch (error) {
      toast(error);
    }
  };

  return (
    <div className="bg-white shadow rounded-lg p-6">
      <h3 className="text-2xl font-bold text-gray-800 mb-6">Tarama İzleme</h3>
      {/* Responsive grid yapısı */}
      <div className="grid grid-cols-8 gap-2 w-full h-80">
        {rectangles.map((rect) => (
          <div
            key={rect.id}
            onClick={() => handleSendIgnoredPoints(rect.id)}
            className="flex items-center justify-center cursor-pointer transition-colors duration-200 text-white font-semibold text-sm hover:scale-105 rounded"
            style={{ backgroundColor: rect.fill }}
          >
            {rect.id}
          </div>
        ))}
      </div>
    </div>
  );
};

export default ScanTrace;
