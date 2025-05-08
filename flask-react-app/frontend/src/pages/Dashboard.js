import React from 'react';
import DebugDashboard from '../components/DebugDashboard';

function DashboardPage() {
  return (
    <div className="w-full h-full  overflow-auto">
      <div className="relative">
        <DebugDashboard />
      </div>
    </div>
  );
}

export default DashboardPage;