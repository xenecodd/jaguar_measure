import React, { useEffect, useState, useMemo } from "react";
import { apiService } from "../services/api.service";
import StatusCard from "./StatusCard";
import FeatureChart from "./FeatureChart";

const DebugDashboard = () => {
    const [latestScan, setLatestScan] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [expandedIterations, setExpandedIterations] = useState({});
    const [selectedFeature, setSelectedFeature] = useState("");
    const [searchQuery, setSearchQuery] = useState("");
    const [filterStatus, setFilterStatus] = useState("all"); // 'all', 'pass', 'fail'
    
    // Extract feature list for dropdown
    const featureList = useMemo(() => {
        return Array.from(new Set(
            latestScan?.scan_results?.flatMap(iter =>
                iter.features?.filter(f => !["Index", "OK", "Processing Time (s)"].includes(f.name))
                .map(f => f.name)
            ) || []
        )).sort();
    }, [latestScan]);

    useEffect(() => {
        const fetchLatestScan = async () => {
            try {
                setLoading(true);
                const data = await apiService.getLatestScan();
                // Convert status.ok to boolean explicitly for each scan result
                const correctedData = {
                    ...data,
                    scan_results: data?.scan_results?.map(iteration => ({
                      ...iteration,
                      features: iteration?.features?.map(feature => ({
                        ...feature,
                        tolerance_check: {
                          ...feature.tolerance_check,
                          within_tolerance:
                            feature.tolerance_check?.within_tolerance === true ||
                            feature.tolerance_check?.within_tolerance === "true"
                        }
                      })) || [],
                      status: {
                        ...iteration.status,
                        ok:
                          iteration.status?.ok === true ||
                          iteration.status?.ok === "true"
                      }
                    })) || []
                  };
                  
                setLatestScan(correctedData);

                // Initialize all iterations as collapsed except the first one
                if (correctedData && correctedData.scan_results) {
                    const initialExpandState = {};
                    correctedData.scan_results.forEach((iteration, index) => {
                        initialExpandState[index] = index === 0; // Only first iteration expanded by default
                    });
                    setExpandedIterations(initialExpandState);
                }

                setLoading(false);
            } catch (error) {
                console.error('Latest scan could not be retrieved:', error);
                setError('Failed to load scan data. Please try again later.');
                setLoading(false);
            }
        };
        fetchLatestScan();
    }, []);

    // Filter iterations based on search query and status filter
    const filteredIterations = useMemo(() => {
        if (!latestScan?.scan_results) return [];
      
        return latestScan.scan_results.filter(iteration => {
          // Status filter
          if (filterStatus === "pass" && !iteration.status?.ok) return false;
          if (filterStatus === "fail" && iteration.status?.ok) return false;
      
          // No search query: pass all
          if (!searchQuery) return true;
      
          const query = searchQuery.toLowerCase();
      
          // Check iteration number (Index feature)
          const indexFeature = iteration.features?.find(f => f.name.toLowerCase() === "index");
          const indexMatch = indexFeature && String(indexFeature.value).toLowerCase().includes(query);
      
          // Check OK feature value
          const okFeature = iteration.features?.find(f => f.name.toLowerCase() === "ok");
          const okMatch = okFeature && String(okFeature.value).toLowerCase().includes(query);
      
          // Check processing time
          const timeFeature = iteration.features?.find(f => f.name.toLowerCase().includes("processing time"));
          const timeMatch = timeFeature && String(timeFeature.value).toLowerCase().includes(query);
      
          // Check all features: name, value, and tolerance_check details
          const featureMatch = iteration.features?.some(feature => {
            return (
              feature.name?.toLowerCase().includes(query) ||
              String(feature.value).toLowerCase().includes(query) ||
              Object.values(feature.tolerance_check || {}).some(val =>
                String(val).toLowerCase().includes(query)
              )
            );
          });
      
          // Check failure reasons
          const failureMatch = iteration.status?.failure_reasons?.some(reason =>
            reason.toLowerCase().includes(query)
          );
      
          return indexMatch || okMatch || timeMatch || featureMatch || failureMatch;
        });
      }, [latestScan, searchQuery, filterStatus]);
      

    const toggleIteration = (index) => {
        setExpandedIterations(prev => ({
            ...prev,
            [index]: !prev[index]
        }));
    };

    const expandAll = () => {
        const allExpanded = {};
        filteredIterations.forEach((_, index) => {
            allExpanded[index] = true;
        });
        setExpandedIterations(allExpanded);
    };

    const collapseAll = () => {
        const allCollapsed = {};
        filteredIterations.forEach((_, index) => {
            allCollapsed[index] = false;
        });
        setExpandedIterations(allCollapsed);
    };

    const filterFailedOnly = () => {
        setFilterStatus("fail");
    };

    // Calculate statistics for dashboard summary
    const calculateStats = () => {
        if (!latestScan?.scan_results) {
            return {
                total: 0,
                passed: 0,
                failed: 0,
                failureReasons: {},
                passRate: 0
            };
        }

        const stats = {
            total: latestScan.scan_results.length,
            passed: 0,
            failed: 0,
            failureReasons: {},
            color: "gray"
        };

        latestScan.scan_results.forEach(iteration => {
            if (iteration.status.ok) {
                stats.passed++;
            } else {
                stats.failed++;
                if (iteration.status.failure_reasons) {
                    iteration.status.failure_reasons.forEach(reason => {
                        // Extract the feature name from failure reason
                        const featureMatch = reason.match(/^(.*?)\s+out of tolerance/);
                        const featureName = featureMatch ? featureMatch[1] : reason;
                        
                        if (!stats.failureReasons[featureName]) {
                            stats.failureReasons[featureName] = 0;
                        }
                        stats.failureReasons[featureName]++;
                    });
                }
            }
        });

        stats.passRate = stats.total > 0 ? (stats.passed / stats.total * 100) : 0;
        
        // Determine summary color based on pass rate
        if (stats.passRate >= 80) {
            stats.color = "green";
        } else if (stats.passRate >= 50) {
            stats.color = "yellow";
        } else {
            stats.color = "red";
        }

        return stats;
    };

    const stats = calculateStats();

    // Loading state
    if (loading) {
        return (
            <div className="flex justify-center items-center h-64">
                <div className="flex flex-col items-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-600"></div>
                    <p className="mt-4 text-gray-600">Loading scan results...</p>
                </div>
            </div>
        );
    }

    // Error state
    if (error) {
        return (
            <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
                <div className="text-red-600 text-xl mb-2">Error Loading Data</div>
                <p className="text-red-700">{error}</p>
                <button 
                    className="mt-4 bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded"
                    onClick={() => window.location.reload()}
                >
                    Retry
                </button>
            </div>
        );
    }

    // No data state
    if (!latestScan || !latestScan.scan_results || latestScan.scan_results.length === 0) {
        return (
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 text-center">
                <div className="text-gray-600 text-xl mb-2">No Scan Data Available</div>
                <p className="text-gray-500">There are no scan results to display at this time.</p>
                <button 
                    className="mt-4 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
                    onClick={() => window.location.reload()}
                >
                    Refresh
                </button>
            </div>
        );
    }

    // Enhanced Summary section
    const renderEnhancedSummary = () => {
        return (
            <div className="mb-6 rounded-lg border overflow-hidden shadow-sm bg-white">
                <div className="p-3 font-bold bg-gray-100 border-b flex justify-between items-center">
                    <span>Scan Summary</span>
                    <span className="text-sm font-normal text-gray-500">
                        {new Date().toLocaleString()}
                    </span>
                </div>
                <div className={`p-4 bg-opacity-10 ${
                    stats.passRate >= 80 ? 'bg-green-100' : 
                    stats.passRate >= 50 ? 'bg-yellow-100' : 'bg-red-100'
                }`}>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                        <StatusCard
                            title="Total Iterations"
                            value={stats.total}
                            className=""
                            textColor="text-gray-800"
                            bgColor="bg-gray-100"
                            icon="📊"
                        />
                        <StatusCard
                            title="Passed"
                            value={stats.passed}
                            className=""
                            textColor="text-green-800"
                            bgColor="bg-green-100"
                            icon="✅"
                        />
                        <StatusCard
                            title="Failed"
                            value={stats.failed}
                            className=""
                            textColor="text-red-800"
                            bgColor="bg-red-100"
                            icon="❌"
                        />
                        <StatusCard
                            title="Pass Rate"
                            value={`${stats.passRate.toFixed(1)}%`}
                            className=""
                            textColor={`text-${stats.color === 'green' ? 'green' : stats.color === 'yellow' ? 'yellow' : 'red'}-800`}
                            bgColor={`bg-${stats.color === 'green' ? 'green' : stats.color === 'yellow' ? 'yellow' : 'red'}-100`}
                            icon="📈"
                        />
                    </div>

                    {/* Progress bar visualization of pass rate */}
                    <div className="mt-2 mb-4">
                        <div className="flex justify-between text-xs text-gray-600 mb-1">
                            <span>Pass Rate</span>
                            <span>{stats.passRate.toFixed(1)}%</span>
                        </div>
                        <div className="h-4 bg-gray-200 rounded-full overflow-hidden">
                            <div 
                                className={`h-full ${
                                    stats.passRate >= 80 ? 'bg-green-500' : 
                                    stats.passRate >= 50 ? 'bg-yellow-500' : 'bg-red-500'
                                }`}
                                style={{ width: `${Math.min(100, stats.passRate)}%` }}
                            ></div>
                        </div>
                    </div>
                </div>

                {/* Common failure reasons section */}
                {stats.failed > 0 && Object.keys(stats.failureReasons).length > 0 && (
                    <div className="p-4 bg-white border-t">
                        <p className="font-semibold mb-3">Common Failure Reasons:</p>
                        <div className="overflow-x-auto">
                            <table className="min-w-full bg-white">
                                <thead>
                                    <tr className="bg-gray-50">
                                        <th className="py-2 px-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Feature</th>
                                        <th className="py-2 px-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Occurrences</th>
                                        <th className="py-2 px-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Distribution</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {Object.entries(stats.failureReasons)
                                        .sort(([_, countA], [__, countB]) => countB - countA)
                                        .map(([reason, count], idx) => {
                                            const percentage = (count / stats.failed * 100).toFixed(1);
                                            return (
                                                <tr key={idx} className={idx % 2 === 0 ? "bg-gray-50" : "bg-white"}>
                                                    <td className="py-2 px-3 text-red-700">{reason}</td>
                                                    <td className="py-2 px-3">{count}</td>
                                                    <td className="py-2 px-3 w-1/3">
                                                        <div className="flex items-center">
                                                            <div className="w-full bg-gray-200 rounded-full h-2.5">
                                                                <div className="bg-red-600 h-2.5 rounded-full" style={{ width: `${percentage}%` }}></div>
                                                            </div>
                                                            <span className="ml-2 text-xs text-gray-500">{percentage}%</span>
                                                        </div>
                                                    </td>
                                                </tr>
                                            );
                                        })
                                    }
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}
            </div>
        );
    };

    // Control panel with search and filters
    const renderControlPanel = () => {
        return (
            <div className="mb-6 bg-white p-4 rounded-lg shadow-sm border">
                <div className="flex flex-col md:flex-row gap-4 mb-4">
                    <div className="flex-grow">
                        <label htmlFor="search" className="block text-sm font-medium text-gray-700 mb-1">Search</label>
                        <div className="relative">
                            <input
                                id="search"
                                type="text"
                                className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                placeholder="Search features, values, or failure reasons..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                            />
                            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                <svg className="h-5 w-5 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" />
                                </svg>
                            </div>
                        </div>
                    </div>
                    
                    <div>
                        <label htmlFor="statusFilter" className="block text-sm font-medium text-gray-700 mb-1">Status Filter</label>
                        <select
                            id="statusFilter"
                            className="block w-full py-2 px-3 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                            value={filterStatus}
                            onChange={(e) => setFilterStatus(e.target.value)}
                        >
                            <option value="all">All Results</option>
                            <option value="pass">Passed Only</option>
                            <option value="fail">Failed Only</option>
                        </select>
                    </div>
                    
                    <div>
                        <label htmlFor="featureSelect" className="block text-sm font-medium text-gray-700 mb-1">Feature Trend Analysis</label>
                        <select
                            id="featureSelect"
                            className="block w-full py-2 px-3 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                            value={selectedFeature}
                            onChange={(e) => setSelectedFeature(e.target.value)}
                        >
                            <option value="">Select a feature</option>
                            {featureList.map((name, idx) => (
                                <option key={idx} value={name}>{name}</option>
                            ))}
                        </select>
                    </div>
                </div>

                <div className="flex flex-wrap gap-2">
                    <button
                        onClick={expandAll}
                        className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm flex items-center"
                    >
                        <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path>
                        </svg>
                        Expand All
                    </button>
                    <button
                        onClick={collapseAll}
                        className="bg-gray-600 hover:bg-gray-700 text-white px-3 py-1 rounded text-sm flex items-center"
                    >
                        <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 15l7-7 7 7"></path>
                        </svg>
                        Collapse All
                    </button>
                    <button
                        onClick={filterFailedOnly}
                        className="bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded text-sm flex items-center"
                    >
                        <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                        </svg>
                        Show Failed Only
                    </button>
                    <button
                        onClick={() => {
                            setSearchQuery("");
                            setFilterStatus("all");
                        }}
                        className="bg-gray-400 hover:bg-gray-500 text-white px-3 py-1 rounded text-sm flex items-center"
                    >
                        <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
                        </svg>
                        Reset Filters
                    </button>
                </div>
            </div>
        );
    };

    // Improved iteration rendering with better visualization
    const renderIteration = (iterationData, index) => {
        const isExpanded = expandedIterations[index];
        const hasFailed = iterationData.status.ok === false;
        
        // Calculate feature statistics for this iteration
        // Compute passed/failed counts with strict boolean checks
// Compute passed/failed counts correctly
const validFeatures = iterationData.features.filter(f => 
    f.tolerance_check && 
    !f.tolerance_check.error
);

const passedFeatures = validFeatures.filter(f => 
    f.tolerance_check.within_tolerance===true
).length;

const failedFeaturesCount = validFeatures.filter(f => 
    f.tolerance_check.within_tolerance===false
).length;

const totalFeatures = validFeatures.length;
const passRate = totalFeatures > 0 ? (passedFeatures / totalFeatures) * 100 : 0;

        return (
            <div key={index} className="mb-4 border rounded-lg overflow-hidden shadow-sm bg-white">
                <div
                    className={`p-3 flex justify-between items-center cursor-pointer transition duration-150 ${
                        hasFailed 
                            ? "bg-red-50 hover:bg-red-100 border-b border-red-200" 
                            : "bg-green-50 hover:bg-green-100 border-b border-green-200"
                    }`}
                    onClick={() => toggleIteration(index)}
                >
                    <div className="flex items-center">
                        <span className="mr-2 text-gray-600 transition-transform duration-200" style={{
                            transform: isExpanded ? 'rotate(90deg)' : 'rotate(0)'
                        }}>
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
                            </svg>
                        </span>
                        <span className="font-medium text-gray-800">Iteration {iterationData.iteration}</span>
                        
                        {/* Feature pass rate indicator */}
                        <div className="ml-4 hidden sm:block">
                            <div className="flex items-center">
                                <div className="w-24 bg-gray-200 rounded-full h-2.5 mr-2">
                                    <div 
                                        className={hasFailed ? "bg-red-600 h-2.5 rounded-full" : "bg-green-600 h-2.5 rounded-full"}
                                        style={{ width: `${passRate}%` }}
                                    ></div>
                                </div>
                                <span className="text-xs text-gray-600">{passedFeatures-failedFeaturesCount}/{totalFeatures} features passed</span>
                            </div>
                        </div>
                    </div>
                    
                    <div className="flex items-center">
                        {/* Processing time if available */}
                        {iterationData.features.find(f => f.name === "Processing Time (s)") && (
                            <span className="mr-3 text-sm text-gray-500 hidden sm:block">
                                <span className="font-medium">Time:</span> {iterationData.features.find(f => f.name === "Processing Time (s)").value.toFixed(1)}s
                            </span>
                        )}
                        
                        <span
                            className={`px-3 py-1 rounded-full text-white text-sm font-medium ${
                                hasFailed ? "bg-red-600" : "bg-green-600"
                            }`}
                        >
                            {hasFailed ? "FAILED" : "PASSED"}
                        </span>
                    </div>
                </div>

                {isExpanded && (
                    <div className="bg-white">
                        {/* Failure reasons at the top if any */}
                        {hasFailed && iterationData.status.failure_reasons && iterationData.status.failure_reasons.length > 0 && (
                            <div className="p-3 bg-red-50 border-b border-red-100">
                                <p className="font-medium text-red-800 mb-1">Failure Reasons:</p>
                                <ul className="list-disc pl-5 text-red-700 space-y-1">
                                    {iterationData.status.failure_reasons.map((reason, idx) => (
                                        <li key={idx}>{reason}</li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        {/* Feature groups toggle */}
                        <div className="p-3 border-b bg-gray-50 flex flex-wrap gap-2">
                            <button 
                                className="text-xs bg-blue-100 hover:bg-blue-200 text-blue-800 font-medium py-1 px-2 rounded"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    const table = document.getElementById(`features-table-${index}`);
                                    const rows = table.querySelectorAll('tr');
                                    rows.forEach(row => {
                                        row.style.display = '';
                                    });
                                }}
                            >
                                Show All
                            </button>
                            <button 
                                className="text-xs bg-red-100 hover:bg-red-200 text-red-800 font-medium py-1 px-2 rounded"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    const table = document.getElementById(`features-table-${index}`);
                                    const rows = table.querySelectorAll('tr');
                                    rows.forEach(row => {
                                        const isFailedRow = row.classList.contains('failed-feature');
                                        row.style.display = isFailedRow ? '' : 'none';
                                    });
                                }}
                            >
                                Failed Only
                            </button>
                            <button 
                                className="text-xs bg-green-100 hover:bg-green-200 text-green-800 font-medium py-1 px-2 rounded"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    const table = document.getElementById(`features-table-${index}`);
                                    const rows = table.querySelectorAll('tr');
                                    rows.forEach(row => {
                                        const isPassedRow = row.classList.contains('passed-feature');
                                        row.style.display = isPassedRow ? '' : 'none';
                                    });
                                }}
                            >
                                Passed Only
                            </button>
                        </div>

                        <div className="overflow-x-auto">
                            <table id={`features-table-${index}`} className="min-w-full bg-white">
                                <thead>
                                    <tr className="bg-gray-100">
                                        <th className="py-2 px-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b w-1/4">Feature</th>
                                        <th className="py-2 px-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b w-1/4">Value</th>
                                        <th className="py-2 px-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b w-2/4">Tolerance Check</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {iterationData.features
                                        .filter(feature => feature.name !== "Index" && feature.name !== "OK")
                                        .map((feature, featureIdx) => {
                                            // Check if this feature has failed tolerance check
                                            const hasFailedTolerance = feature.tolerance_check &&
                                            !feature.tolerance_check.error &&
                                            !feature.tolerance_check.within_tolerance;

                                            const hasPassedTolerance = feature.tolerance_check &&
                                            !feature.tolerance_check.error &&
                                            feature.tolerance_check.within_tolerance;

                                            // Calculate tolerance utilization as a percentage
                                            let toleranceUtilization = 0;
                                            if (feature.tolerance_check && feature.tolerance_check.tolerance > 0) {
                                                toleranceUtilization = Math.abs(feature.tolerance_check.distance / feature.tolerance_check.tolerance) * 100;
                                            }

                                            return (
                                                <tr
                                                    key={featureIdx}
                                                    className={`border-b hover:bg-gray-50 ${
                                                        hasFailedTolerance ? 'bg-red-50 failed-feature' : 
                                                        hasPassedTolerance ? 'passed-feature' : ''
                                                    }`}
                                                >
                                                    <td className="py-3 px-4 font-medium">
                                                        <div className="flex items-center">
                                                            {hasFailedTolerance && (
                                                                <span className="inline-flex items-center justify-center mr-2 flex-shrink-0 w-5 h-5 bg-red-100 text-red-800 rounded-full">
                                                                    <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                                                        <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                                                                    </svg>
                                                                </span>
                                                            )}
                                                            {hasPassedTolerance && (
                                                                <span className="inline-flex items-center justify-center mr-2 flex-shrink-0 w-5 h-5 bg-green-100 text-green-800 rounded-full">
                                                                    <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                                                                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                                                    </svg>
                                                                </span>
                                                            )}
                                                            {feature.name}
                                                        </div>
                                                    </td>
                                                    <td
                                                        className="py-3 px-4 font-mono"
                                                        style={{
                                                            color: feature.value_color ? `#${feature.value_color}` : 'inherit',
                                                            fontWeight: hasFailedTolerance ? 'bold' : 'normal'
                                                        }}
                                                    >
                                                        {typeof feature.value === 'object'
                                                            ? JSON.stringify(feature.value)
                                                            : typeof feature.value === 'number'
                                                                ? feature.value.toFixed(3)
                                                                : feature.value}
                                                    </td>
                                                    <td className="py-3 px-4">
                                                        {feature.tolerance_check ? (
                                                            <div>
                                                                {feature.tolerance_check.error ? (
                                                                    <span className="text-gray-500 italic">{feature.tolerance_check.error}</span>
                                                                ) : (
                                                                    <div className="flex flex-col">
                                                                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-2">
                                                                            <div className="text-sm">
                                                                                <span className="text-gray-600 text-xs">Target:</span>
                                                                                <span className="ml-1 font-medium">{feature.tolerance_check.target}</span>
                                                                            </div>
                                                                            <div className="text-sm">
                                                                                <span className="text-gray-600 text-xs">Tolerance:</span>
                                                                                <span className="ml-1 font-medium">±{feature.tolerance_check.tolerance}</span>
                                                                            </div>
                                                                            <div className="text-sm">
                                                                                <span className="text-gray-600 text-xs">Distance:</span>
                                                                                <span 
                                                                                    className={`ml-1 font-medium ${hasFailedTolerance ? 'text-red-700' : 'text-gray-800'}`}
                                                                                >
                                                                                    {feature.tolerance_check.distance?.toFixed(3)}
                                                                                </span>
                                                                            </div>
                                                                            <div className="text-sm">
                                                                                <span className="text-gray-600 text-xs">Remaining:</span>
                                                                                <span 
                                                                                    className={`ml-1 font-medium ${
                                                                                        feature.tolerance_check.tolerance_remaining < 0 
                                                                                            ? 'text-red-700' 
                                                                                            : feature.tolerance_check.tolerance_remaining / feature.tolerance_check.tolerance < 0.2
                                                                                                ? 'text-yellow-700'
                                                                                                : 'text-green-700'
                                                                                    }`}
                                                                                >
                                                                                    {feature.tolerance_check.tolerance_remaining?.toFixed(3) || 'N/A'}
                                                                                </span>
                                                                            </div>
                                                                        </div>

                                                                        {/* Progress bar visualization with improved styling */}
                                                                        {feature.tolerance_check.tolerance > 0 && (
                                                                            <div className="mb-1">
                                                                                <div className="flex items-center">
                                                                                    <div className="flex-grow h-4 bg-gray-200 rounded-full overflow-hidden">
                                                                                        {/* Target indicator line */}
                                                                                        <div className="relative w-full h-full">
                                                                                            <div className="absolute inset-y-0 left-1/2 w-0.5 bg-black z-10"></div>
                                                                                            <div
                                                                                                className={`absolute inset-y-0 h-full ${hasFailedTolerance ? 'bg-red-600' : 'bg-green-600'}`}
                                                                                                style={{
                                                                                                    width: `${Math.min(100, toleranceUtilization)}%`,
                                                                                                    left: '50%',
                                                                                                    transform: feature.value < feature.tolerance_check.target ? 'translateX(-100%)' : 'none'
                                                                                                }}
                                                                                            ></div>
                                                                                        </div>
                                                                                    </div>
                                                                                    <span className={`ml-2 text-xs ${hasFailedTolerance ? 'text-red-700' : 'text-green-700'}`}>
                                                                                        {toleranceUtilization.toFixed(1)}%
                                                                                    </span>
                                                                                </div>
                                                                                <div className="flex justify-between text-xs text-gray-500 mt-1">
                                                                                    <span>{(feature.tolerance_check.target - feature.tolerance_check.tolerance).toFixed(1)}</span>
                                                                                    <span>{feature.tolerance_check.target}</span>
                                                                                    <span>{(feature.tolerance_check.target + feature.tolerance_check.tolerance).toFixed(1)}</span>
                                                                                </div>
                                                                            </div>
                                                                        )}
                                                                    </div>
                                                                )}
                                                            </div>
                                                        ) : (
                                                            <span className="text-gray-500 italic">No tolerance defined</span>
                                                        )}
                                                    </td>
                                                </tr>
                                            );
                                        })}
                                </tbody>
                            </table>
                        </div>
                        
                        {/* Bottom section with processing time and additional info */}
                        <div className="p-3 bg-gray-50 border-t text-sm text-gray-600 flex flex-wrap gap-4">
                            {iterationData.features.find(f => f.name === "Processing Time (s)") && (
                                <div>
                                    <span className="font-medium">Processing Time:</span> 
                                    {iterationData.features.find(f => f.name === "Processing Time (s)").value.toFixed(2)}s
                                </div>
                            )}
                            <div>
                                <span className="font-medium">Feature Pass Rate:</span> 
                                {passedFeatures}/{totalFeatures} ({(passRate).toFixed(1)}%)
                            </div>
                            <div>
                                <button
                                    className="text-blue-600 hover:text-blue-800 font-medium"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        // Find all available features in this iteration
                                        const features = iterationData.features
                                            .filter(f => f.name !== "Index" && f.name !== "OK" && f.name !== "Processing Time (s)");
                                        
                                        // If there are multiple failed features, select the first failed one
                                        const failedFeature = features.find(f => 
                                            f.tolerance_check && 
                                            !f.tolerance_check.error && 
                                            !f.tolerance_check.within_tolerance
                                        );
                                        
                                        if (failedFeature) {
                                            setSelectedFeature(failedFeature.name);
                                        } else if (features.length > 0) {
                                            setSelectedFeature(features[0].name);
                                        }
                                        
                                        // Scroll to chart
                                        document.getElementById('feature-chart-section').scrollIntoView({ behavior: 'smooth' });
                                    }}
                                >
                                    Analyze Features
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        );
    };

    return (
        <div className="max-w-6xl mx-auto p-4 md:p-6">
            <div className="bg-white shadow-md rounded-lg p-4 md:p-6 mb-8">
                <div className="flex flex-col md:flex-row justify-between items-center mb-6">
                    <h1 className="text-xl md:text-2xl font-bold text-blue-800">
                        <span className="flex items-center">
                            <svg className="w-6 h-6 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
                            </svg>
                            Scan Results Dashboard
                        </span>
                    </h1>
                </div>

                {/* Enhanced Summary section */}
                {renderEnhancedSummary()}

                {/* Control panel with search and filters */}
                {renderControlPanel()}

                {/* Feature Chart section */}
                <div id="feature-chart-section">
                    {selectedFeature && (
                        <FeatureChart
                            data={latestScan.scan_results}
                            selectedFeature={selectedFeature}
                        />
                    )}
                </div>
            </div>

            {/* Results count indicator */}
            <div className="mb-4 bg-white p-3 rounded-lg shadow-sm border flex justify-between items-center">
                <span className="text-gray-700">
                    Showing {filteredIterations.length} of {latestScan.scan_results.length} iterations
                    {searchQuery && <span className="ml-2 text-gray-500">filtered by "{searchQuery}"</span>}
                    {filterStatus !== "all" && (
                        <span className="ml-2 text-gray-500">
                            showing {filterStatus === "pass" ? "passed" : "failed"} iterations only
                        </span>
                    )}
                </span>
                {(searchQuery || filterStatus !== "all") && (
                    <button
                        className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                        onClick={() => {
                            setSearchQuery("");
                            setFilterStatus("all");
                        }}
                    >
                        Clear Filters
                    </button>
                )}
            </div>

            {/* Individual iteration sections */}
            <div>
                {filteredIterations.length > 0 ? (
                    filteredIterations.map((iteration, idx) => (
                        renderIteration(iteration, idx)
                    ))
                ) : (
                    <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 text-center">
                        <div className="text-gray-400 mb-2">
                            <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                            </svg>
                        </div>
                        <p className="text-gray-600 text-lg">No results match your filters</p>
                        <p className="text-gray-500 mt-1">Try adjusting your search criteria</p>
                    </div>
                )}
            </div>

            {/* Enhanced StatusCard Component */}
            {/* This would typically be in a separate file, but showing for reference */}
            {/* 
            // const StatusCard = ({ title, value, textColor, bgColor, icon }) => {
            //     return (
            //         <div className={`p-4 rounded-lg ${bgColor} border ${bgColor.replace('bg-', 'border-')} shadow-sm`}>
            //             <div className="flex justify-between items-start">
            //                 <div>
            //                     <p className="text-sm text-gray-600 mb-1">{title}</p>
            //                     <p className={`text-2xl font-bold ${textColor}`}>{value}</p>
            //                 </div>
            //                 {icon && <div className="text-xl">{icon}</div>}
            //             </div>
            //         </div>
            //     );
            // };
            */}
        </div>
    );
};

export default DebugDashboard;