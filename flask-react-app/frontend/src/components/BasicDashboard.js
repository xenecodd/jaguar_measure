import React, { useEffect, useState } from "react";
import { apiService } from "../services/api.service";

/**
 * SimpleDebugDashboard - A straightforward dashboard showing scan iterations as passed or failed
 * @returns {JSX.Element} Simplified dashboard component
 */
const SimpleDebugDashboard = () => {
  const [scans, setScans] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch latest scan data on component mount
  useEffect(() => {
    const getScans = async () => {
      try {
        setIsLoading(true);
        const data = await apiService.getLatestScan();
        // Convert status.ok to boolean explicitly
        const correctedScans = data?.scan_results?.map(scan => ({
          ...scan,
          status: {
            ...scan.status,
            ok: scan.status?.ok === true || scan.status?.ok === "true"
          }
        })) || [];
        setScans(correctedScans);
        // Log processed values for debugging
        console.log(
          "Processed scans:",
          correctedScans.map(scan => ({
            iteration: scan.iteration,
            ok: scan.status.ok
          }))
        );
      } catch (err) {
        setError("Oops! Couldn't load the scan results.");
        console.error("Failed to fetch scans:", err);
      } finally {
        setIsLoading(false);
      }
    };
    getScans();
  }, []);

  // Render loading state
  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  // Render error state
  if (error) {
    return <div className="text-center text-red-500 p-4">{error}</div>;
  }

  // Render no data state
  if (!scans.length) {
    return <div className="text-center text-gray-500 p-4">No scan results yet.</div>;
  }

  return (
    <div className="max-w-2xl mx-auto p-4">
      <h1 className="text-2xl font-bold text-blue-600 mb-4">Scan Check Results</h1>

      {/* Summary Counts */}
      <div className="flex justify-between mb-6 bg-gray-100 p-3 rounded">
        <div className="text-center">
          <p className="text-lg font-semibold text-green-600">
            {scans.filter(scan => scan.status.ok).length}
          </p>
          <p className="text-sm text-gray-600">Passed</p>
        </div>
        <div className="text-center">
          <p className="text-lg font-semibold text-red-600">
            {scans.filter(scan => !scan.status.ok).length}
          </p>
          <p className="text-sm text-gray-600">Failed</p>
        </div>
      </div>

      {/* Scan List */}
      <div className="grid grid-cols-4 gap-4">
        {scans.map((scan, index) => (
          <div
            key={index}
            className={`p-3 rounded shadow ${
              scan.status.ok ? "bg-green-100" : "bg-red-100"
            }`}
          >
            <div className="flex justify-between items-center">
              <span className="font-medium">Check #{scan.iteration}</span>
              <span
                className={`px-2 py-1 rounded text-white text-sm ${
                  scan.status.ok ? "bg-green-500" : "bg-red-500"
                }`}
              >
                {scan.status.ok ? "PASSED" : "FAILED"}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SimpleDebugDashboard;