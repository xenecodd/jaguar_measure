import React, { useEffect, useState } from 'react';
import { apiService } from '../services/api.service';
import { toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { ToastContainer } from 'react-toastify';

const ScanTrace = ({ onScan }) => {
  const [rectangles, setRectangles] = useState([]);
  const [ignoredPointsInput, setIgnoredPointsInput] = useState([]);
  const [internalData, setInternalData] = useState("blank");
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
      console.log(data)
      } catch (error) {
        console.log('Renkler alınırken hata oluştu:', error);
        setTimeout(fetchColors, 5000);
      }
    };

    fetchColors();
    const interval = setInterval(fetchColors, 200);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (internalData !== "blank") {
      onScan(internalData);
    }
  }, [internalData, onScan]);
  // Tıklanan kutu rengini değiştir
  const handleRectClick = (id) => {
    if (JSON.stringify(ignoredPointsInput) === JSON.stringify([19, 23, 20, 0, 2])) {
      toast.success("Easter egg :)");
      setInternalData("Easter egg :)"); // Bu yeterli, onScan otomatik çalışacak
    } else {
      setInternalData("");
    }    
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
      const numericAction = parseInt(action, 10);
      const newPoints = ignoredPointsInput.includes(numericAction)
        ? ignoredPointsInput.filter((index) => index !== numericAction)
        : [...ignoredPointsInput, numericAction];
      setIgnoredPointsInput(newPoints);
      handleRectClick(action);
  
      await apiService.controlScan({ ignored_index_list: newPoints });
    } catch (error) {
      toast.error(error);
    }
  };
  return (
    <div className="bg-slate-800 shadow-xl rounded-2xl ">
      <ToastContainer
        position="top-right"
        autoClose={2000}
        newestOnTop={true}
        closeOnClick={true}
        pauseOnHover={true}
        theme="dark"
        style={{
          zIndex: 9999,
        }}
        closeButton={false}
      />
      {/* Responsive grid yapısı */}
      <div className="grid grid-cols-10 gap-2 w-full h-80">
        {rectangles.map((rect) => (
          <div
            key={rect.id}
            onClick={() => handleSendIgnoredPoints(rect.id)}
            className={`flex ${rect.fill === "yellow" ? "animate-pulse " : ""} items-center text-xl justify-center cursor-pointer transition-transform duration-200 transform hover:scale-105 text-white font-semibold text-sm rounded-xl shadow-md`}
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
