import React, { useEffect, useState } from 'react';
import { apiService } from '../services/api.service';

const ScanTrace = () => {
  const [rectangles, setRectangles] = useState([]);

  // Initialize the grid with 64 gray rectangles (8x8)
  useEffect(() => {
    const initialRectangles = Array.from({ length: 64 }, (_, i) => ({
      id: String(i),
      x: (i % 8) * 50,
      y: Math.floor(i / 8) * 50,
      fill: 'gray',
    }));

    setRectangles(initialRectangles);
  }, []);

  // Fetch colors from API and update rectangles
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

  const handleRectClick = (id) => {
    setRectangles((prevRects) =>
      prevRects.map((rect) =>
        rect.id === id
          ? { ...rect, fill: rect.fill === 'blue' ? 'red' : 'blue' }
          : rect
      )
    );
  };

  return (
    <div className="w-full p-4 bg-white rounded-lg shadow">
      <h3 className="text-lg font-semibold mb-4">Tarama İzleme</h3>
      {/* Sabit piksel boyutları yerine responsive sınıflar kullanıldı */}
      <div className="grid grid-cols-8 gap-1 w-full h-80">
        {rectangles.map((rect) => (
          <div
            key={rect.id}
            onClick={() => handleRectClick(rect.id)}
            className="flex items-center justify-center cursor-pointer transition-colors duration-200 text-white font-bold text-sm hover:text-red-600 rounded"
            style={{
              backgroundColor: rect.fill,
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