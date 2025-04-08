import React, { useRef } from 'react';
import Dashboard from './Dashboard';
import ThreeDTrace from '../components/3DTrace';

function Home() {
  const threeTraceRef = useRef(null);
  
  return (
    <div className="w-full h-full overflow-auto">
      <Dashboard />
    </div>
  );
}

export default Home;