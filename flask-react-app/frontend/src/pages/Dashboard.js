import React from 'react';
import DebugDashboard from '../components/DebugDashboard';
import BasicDashboard from '../components/BasicDashboard';

function DashboardPage() {
  const [advanced, setAdvanced] = React.useState(false);
  return (
    <div className="w-full h-full overflow-auto">
        <button onClick={() => {setAdvanced(!advanced)}} className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm">
            {advanced ? "Basic Dashboard" : "Debug Dashboard"}</button>

      {!advanced && <BasicDashboard />}
      {advanced && <DebugDashboard />}
    </div>
  );
}

export default DashboardPage;