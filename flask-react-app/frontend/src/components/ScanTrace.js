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
    <div className="bg-slate-800 shadow-xl rounded-2xl ">

      {/* Responsive grid yapısı */}
      <div className="grid grid-cols-8 gap-2 w-full h-80">
        {rectangles.map((rect) => (
          <div
            key={rect.id}
            onClick={() => handleSendIgnoredPoints(rect.id)}
            className="flex items-center justify-center cursor-pointer transition-transform duration-200 transform hover:scale-105 text-white font-semibold text-sm rounded-xl shadow-md"
            style={{
              backgroundColor: rect.fill,
              boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
            }}
          >
            {rect.id}
          </div>
        ))}
      </div>
    </div>

  );
};

export default ScanTrace;
