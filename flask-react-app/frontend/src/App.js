import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import Navbar from './components/Navbar';
import DebugPanel from './pages/DebugPanel';
import './styles/index.css';
import Home from './pages/Home.js';
import ThreeDTrace from './components/3DTrace.js';
import { useRef } from 'react';


function App() {
  const threeTraceRef = useRef(null);
  return (
    <Router>
      <Navbar />
      <Routes>
        <Route path="/" element={<Home />} />
        {/* <Route path="/dashboard" element={<ThreeDTrace containerRef={threeTraceRef} />} /> */}
        <Route path="/debug" element={<DebugPanel />} />
      </Routes>
    </Router>
  );
}

export default App;
