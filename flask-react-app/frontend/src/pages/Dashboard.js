import React from 'react';
import DebugDashboard from '../components/DebugDashboard';
import BasicDashboard from '../components/BasicDashboard';

function DashboardPage() {
  const [advanced, setAdvanced] = React.useState(false);
  return (
    <div className="w-full h-full overflow-auto">
      <div className="fixed top-12 left-4 z-50">
        <button
          onClick={() => { setAdvanced(!advanced); }}
          className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded text-sm"
        >
          {advanced ? "Basic Dashboard" : "Debug Dashboard"}
        </button>
      </div>
      {!advanced && <BasicDashboard />}
      {advanced && <DebugDashboard />}
    </div>

  );
}

export default DashboardPage;