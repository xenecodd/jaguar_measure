import React, { useEffect, useState, useMemo } from "react";
import { apiService } from "../services/api.service";
import StatusCard from "./StatusCard";
import FeatureChart from "./FeatureChart";
import FileDownload from 'js-file-download';
import Button from "../components/Button";

const DebugDashboard = () => {
    const [latestScan, setLatestScan] = useState(null);
    const [loading, setLoading] = useState(true);
    const [filesLoading, setFilesLoading] = useState(true);
    const [error, setError] = useState(null);
    const [warning, setWarning] = useState(null);
    const [expandedIterations, setExpandedIterations] = useState({});
    const [selectedFeature, setSelectedFeature] = useState("");
    const [searchQuery, setSearchQuery] = useState("");
    const [filterStatus, setFilterStatus] = useState("all");
    const [showResults, setShowResults] = useState(false);
    const [selectedFile, setSelectedFile] = useState("");
    const [availableFiles, setAvailableFiles] = useState([]);

    // New state for historical data functionality
    const [dataMode, setDataMode] = useState("latest"); // "latest" or "historical"
    const [availableDates, setAvailableDates] = useState([]);
    const [startDate, setStartDate] = useState("");
    const [endDate, setEndDate] = useState("");
    const [datesLoading, setDatesLoading] = useState(false);

    // Extract feature list for dropdown
    const featureList = useMemo(() => {
        return Array.from(new Set(
            latestScan?.scan_results?.flatMap(iter =>
                iter.features?.filter(f => !["Index", "OK", "Processing Time (s)"].includes(f.name))
                    .map(f => f.name)
            ) || []
        ));
    }, [latestScan]);

    // Initialize default dates (yesterday)
    useEffect(() => {
        const yesterday = new Date();
        yesterday.setDate(yesterday.getDate() - 1);
        const yesterdayStr = yesterday.toISOString().split('T')[0];

        setStartDate(yesterdayStr);
        setEndDate(yesterdayStr);
    }, []);

    // Fetch available dates when component mounts
    useEffect(() => {
        fetchAvailableDates();
    }, []);

    useEffect(() => {
        // Fetch available files for latest mode
        const fetchAvailableFiles = async () => {
            try {
                setFilesLoading(true);
                const response = await apiService.getLatestScan('scan_output.json');
                if (response.available_files) {
                    setAvailableFiles(response.available_files);
                    setSelectedFile(response.available_files[0]?.name || 'scan_output.json');
                } else {
                    setError('No available files found');
                }
                setFilesLoading(false);
            } catch (err) {
                setError('Failed to load available files');
                setFilesLoading(false);
            }
        };

        if (dataMode === "latest") {
            fetchAvailableFiles();
        }
    }, [dataMode]);

    useEffect(() => {
        if (dataMode === "latest" && selectedFile) {
            fetchLatestScan();
        }
    }, [selectedFile, dataMode]);

    const submitDateRange = () => {
        if (dataMode === "historical" && startDate && endDate) {
            fetchHistoricalScan();
        }
    };

    const fetchAvailableDates = async () => {
        try {
            setDatesLoading(true);
            const response = await apiService.getAvailableDates();
            setAvailableDates(response.available_dates || []);
            setDatesLoading(false);
        } catch (err) {
            setWarning('Failed to load available dates for historical data');
            setDatesLoading(false);
        }
    };

    const fetchLatestScan = async () => {
        try {
            setLoading(true);
            setError(null);
            setWarning(null);
            setSearchQuery(""); // Reset search query
            setFilterStatus("all"); // Reset filter status
            setExpandedIterations({}); // Reset expanded iterations

            const data = await apiService.getLatestScan(selectedFile);

            // Handle error response
            if (data.message && data.available_files) {
                setError(data.message);
                setAvailableFiles(data.available_files);
                setLoading(false);
                return;
            }

            // Convert status.ok to boolean explicitly
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

            // Initialize first iteration as expanded
            if (correctedData?.scan_results) {
                const initialExpandState = {};
                correctedData.scan_results.forEach((_, index) => {
                    initialExpandState[index] = index === 0;
                });
                setExpandedIterations(initialExpandState);
            }

            setLoading(false);
        } catch (error) {
            setError('Failed to load scan data');
            setLoading(false);
        }
    };

    const fetchHistoricalScan = async () => {
        try {
            setLoading(true);
            setError(null);
            setWarning(null);
            setSearchQuery(""); // Reset search query
            setFilterStatus("all"); // Reset filter status
            setExpandedIterations({}); // Reset expanded iterations

            const data = await apiService.getHistoricalScan(startDate, endDate);

            // Handle case where no data found
            if (data.message && data.data && data.data.length === 0) {
                setWarning(`No data found for the date range ${startDate} to ${endDate}`);
                setLatestScan(null);
                setLoading(false);
                return;
            }

            // Convert status.ok to boolean explicitly
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

            // Initialize first iteration as expanded
            if (correctedData?.scan_results) {
                const initialExpandState = {};
                correctedData.scan_results.forEach((_, index) => {
                    initialExpandState[index] = index === 0;
                });
                setExpandedIterations(initialExpandState);
            }

            setLoading(false);
        } catch (error) {
            setError('Failed to load historical scan data');
            console.error('Error fetching historical scan:', error);
            setLoading(false);
        }
    };

    // Filter iterations based on search query and status filter
    const filteredIterations = useMemo(() => {
        if (!latestScan?.scan_results) return [];

        return latestScan.scan_results.filter(iteration => {
            if (filterStatus === "pass" && !iteration.status?.ok) return false;
            if (filterStatus === "fail" && iteration.status?.ok) return false;
            if (!searchQuery) return true;

            const query = searchQuery.toLowerCase();
            const indexFeature = iteration.features?.find(f => f.name.toLowerCase() === "index");
            const indexMatch = indexFeature && String(indexFeature.value).toLowerCase().includes(query);
            const okFeature = iteration.features?.find(f => f.name.toLowerCase() === "ok");
            const okMatch = okFeature && String(okFeature.value).toLowerCase().includes(query);
            const timeFeature = iteration.features?.find(f => f.name.toLowerCase().includes("processing time"));
            const timeMatch = timeFeature && String(timeFeature.value).toLowerCase().includes(query);
            const featureMatch = iteration.features?.some(feature =>
                feature.name?.toLowerCase().includes(query) ||
                String(feature.value).toLowerCase().includes(query) ||
                Object.values(feature.tolerance_check || {}).some(val =>
                    String(val).toLowerCase().includes(query)
                )
            );
            const failureMatch = iteration.status?.failure_reasons?.some(reason =>
                reason.toLowerCase().includes(query)
            );

            return indexMatch || okMatch || timeMatch || featureMatch || failureMatch;
        });
    }, [latestScan, searchQuery, filterStatus]);

    const downloadExcel = () => {
        if (dataMode === "latest") {
            apiService.downloadExcel(selectedFile).then((res) => {
                FileDownload(res.data, `${selectedFile || 'data'}.xlsx`);
            });
        } else {
            // For historical data, we might need a different endpoint or approach
            // This depends on your backend implementation
            setWarning('Excel download for historical data is not yet implemented');
        }
    };

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

    const calculateStats = () => {
        if (!latestScan?.scan_results) {
            return { total: 0, passed: 0, failed: 0, failureReasons: {}, passRate: 0 };
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
                        const featureMatch = reason.match(/^(.*?)\s+out of tolerance/);
                        const featureName = featureMatch ? featureMatch[1] : reason;
                        stats.failureReasons[featureName] = (stats.failureReasons[featureName] || 0) + 1;
                    });
                }
            }
        });

        stats.passRate = stats.total > 0 ? (stats.passed / stats.total * 100) : 0;
        stats.color = stats.passRate >= 80 ? "green" : stats.passRate >= 50 ? "yellow" : "red";

        return stats;
    };

    const stats = calculateStats();

    if (filesLoading || datesLoading) {
        return (
            <div className="flex justify-center items-center h-64">
                <div className="flex flex-col items-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-600"></div>
                    <p className="mt-4 text-gray-600">Loading available data...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
                <div className="text-red-600 text-xl mb-2">{error}</div>
                <button
                    className="mt-4 bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded"
                    onClick={() => window.location.reload()}
                >
                    Retry
                </button>
            </div>
        );
    }

    if (warning && (!latestScan || !latestScan.scan_results || latestScan.scan_results.length === 0)) {
        return (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
                <div className="text-yellow-600 text-xl mb-2">{warning}</div>
                <p className="text-yellow-500">Try selecting a different date range or switch to latest data mode.</p>
                <div className="mt-4 space-x-2">
                    <button
                        className="bg-yellow-600 hover:bg-yellow-700 text-white px-4 py-2 rounded"
                        onClick={() => setDataMode("latest")}
                    >
                        Switch to Latest
                    </button>
                    <button
                        className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
                        onClick={() => window.location.reload()}
                    >
                        Refresh
                    </button>
                </div>
            </div>
        );
    }

    const renderEnhancedSummary = () => {
        return (
            <div className="mb-6 rounded-lg border overflow-hidden shadow-sm bg-white">
                <div className="p-3 font-bold bg-gray-100 border-b flex justify-between items-center">
                    <span>Scan Summary</span>
                    <span className="text-sm font-normal text-gray-500">
                        {dataMode === "historical" && startDate && endDate ?
                            `${startDate} to ${endDate}` :
                            new Date().toLocaleString()
                        }
                    </span>
                </div>
                <div className={`p-4 bg-opacity-10 ${stats.passRate >= 80 ? 'bg-green-100' :
                    stats.passRate >= 50 ? 'bg-yellow-100' : 'bg-red-100'
                    }`}>
                    {warning && (
                        <div className="mb-4 p-3 bg-yellow-100 border border-yellow-300 rounded-md">
                            <div className="flex">
                                <div className="flex-shrink-0">
                                    <svg className="h-5 w-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
                                        <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                                    </svg>
                                </div>
                                <div className="ml-3">
                                    <p className="text-sm text-yellow-700">{warning}</p>
                                </div>
                            </div>
                        </div>
                    )}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                        <StatusCard
                            title="Total Iterations"
                            value={stats.total}
                            textColor="text-gray-800"
                            bgColor="bg-gray-100"
                            icon="📊"
                        />
                        <StatusCard
                            title="Passed"
                            value={stats.passed}
                            textColor="text-green-800"
                            bgColor="bg-green-100"
                            icon="✅"
                        />
                        <StatusCard
                            title="Failed"
                            value={stats.failed}
                            textColor="text-red-800"
                            bgColor="bg-red-100"
                            icon="❌"
                        />
                        <StatusCard
                            title="Pass Rate"
                            value={`${stats.passRate.toFixed(1)}%`}
                            textColor={`text-${stats.color}-800`}
                            bgColor={`bg-${stats.color}-100`}
                            icon="📈"
                        />
                    </div>
                    <div className="mt-2 mb-4">
                        <div className="flex justify-between text-xs text-gray-600 mb-1">
                            <span>Pass Rate</span>
                            <span>{stats.passRate.toFixed(1)}%</span>
                        </div>
                        <div className="h-4 bg-gray-200 rounded-full overflow-hidden">
                            <div
                                className={`h-full ${stats.passRate >= 80 ? 'bg-green-500' :
                                    stats.passRate >= 50 ? 'bg-yellow-500' : 'bg-red-500'
                                    }`}
                                style={{ width: `${Math.min(100, stats.passRate)}%` }}
                            ></div>
                        </div>
                    </div>
                </div>
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
                                        .sort((a, b) => (b[1] / stats.total) - (a[1] / stats.total))
                                        .map(([reason, count], idx) => {
                                            const percentage = (count / stats.total * 100).toFixed(1);
                                            return (
                                                <tr key={idx} className={idx % 2 === 0 ? "bg-gray-50" : "bg-white"}>
                                                    <td className="py-2 px-3 text-red-700">{reason}</td>
                                                    <td className="py-2 px-3">{count}</td>
                                                    <td className="py-2 px-3 w-1/3">
                                                        <div className="flex items-center">
                                                            <div className="w-full bg-gray-200 rounded-full h-2.5 mr-2">
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

    const renderControlPanel = () => {
        return (
            <div className="mb-6 bg-white p-4 rounded-lg shadow-sm border">
                {/* Data Mode Toggle */}
                <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-1">Data Mode</label>
                    <div className="flex space-x-4">
                        <label className="flex items-center">
                            <input
                                type="radio"
                                className="form-radio h-4 w-4 text-blue-600"
                                name="dataMode"
                                value="latest"
                                checked={dataMode === "latest"}
                                onChange={(e) => setDataMode(e.target.value)}
                            />
                            <span className="ml-2 text-sm text-gray-700">Latest Data</span>
                        </label>
                        <label className="flex items-center">
                            <input
                                type="radio"
                                className="form-radio h-4 w-4 text-blue-600"
                                name="dataMode"
                                value="historical"
                                checked={dataMode === "historical"}
                                onChange={(e) => setDataMode(e.target.value)}
                            />
                            <span className="ml-2 text-sm text-gray-700">Historical Data</span>
                        </label>
                    </div>
                </div>

                {/* Latest Data Controls */}
                {dataMode === "latest" && (
                    <div className="mb-4">
                        <label htmlFor="fileSelector" className="block text-sm font-medium text-gray-700 mb-1">Data Source</label>
                        {filesLoading ? (
                            <div className="flex items-center">
                                <div className="animate-spin rounded-full h-5 w-5 border-t-2 border-b-2 border-blue-600 mr-2"></div>
                                <span>Loading files...</span>
                            </div>
                        ) : (
                            <>
                                <select
                                    id="fileSelector"
                                    className="block w-full py-2 px-3 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                    value={selectedFile}
                                    onChange={(e) => setSelectedFile(e.target.value)}
                                >
                                    {availableFiles.map((file, index) => (
                                        <option key={index} value={file.name}>{file.label}</option>
                                    ))}
                                </select>
                                <Button
                                    text="Download Excel"
                                    type="secondary"
                                    className="text-xs mt-2 px-2 py-1"
                                    onClick={downloadExcel}
                                />
                            </>
                        )}
                    </div>
                )}

                {/* Historical Data Controls */}
                {dataMode === "historical" && (
                    <div className="mb-4 space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label htmlFor="startDate" className="block text-sm font-medium text-gray-700 mb-1">Start Date</label>
                                <input
                                    type="date"
                                    id="startDate"
                                    className="block w-full py-2 px-3 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                    value={startDate}
                                    onChange={(e) => setStartDate(e.target.value)}
                                />
                            </div>
                            <div>
                                <label htmlFor="endDate" className="block text-sm font-medium text-gray-700 mb-1">End Date</label>
                                <input
                                    type="date"
                                    id="endDate"
                                    className="block w-full py-2 px-3 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                                    value={endDate}
                                    onChange={(e) => setEndDate(e.target.value)}
                                />
                            </div>
                        </div>
                        <div className="flex justify-start">
                            <Button
                                text="Search Date Range"
                                onClick={submitDateRange}
                                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
                            />
                        </div>
                        {availableDates.length > 0 && (
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Available Dates ({availableDates.length} total)
                                </label>
                                <div className="text-xs text-gray-500 bg-gray-50 p-2 rounded border max-h-24 overflow-y-auto">
                                    {availableDates.slice(0, 10).join(', ')}
                                    {availableDates.length > 10 && ` ... and ${availableDates.length - 10} more`}
                                </div>
                            </div>
                        )}
                    </div>
                )}

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
                        onClick={() => setFilterStatus('fail')}
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

    const renderIteration = (iterationData, index) => {
        // FIX: Define displayFeatures and processingTimeFeature
        const displayFeatures = iterationData.features.filter(
            (f) => !["Index", "OK", "Processing Time (s)"].includes(f.name)
        );
        const processingTimeFeature = iterationData.features.find(
            (f) => f.name.toLowerCase().includes("processing time")
        );
        const isExpanded = expandedIterations[index];
        const hasFailed = iterationData.status.ok === false;
        const validFeatures = iterationData.features.filter(f => f.tolerance_check && !f.tolerance_check.error);
        const passedFeatures = validFeatures.filter(f => f.tolerance_check.within_tolerance === true).length;
        const failedFeaturesCount = validFeatures.filter(f => f.tolerance_check.within_tolerance === false).length;
        const totalFeatures = validFeatures.length;
        const passRate = totalFeatures > 0 ? (passedFeatures / totalFeatures) * 100 : 0;

        return (
            <div key={index} className="mb-4 border rounded-lg overflow-hidden shadow-sm bg-white">
                <div
                    className={`p-3 flex justify-between items-center cursor-pointer transition duration-150 ${hasFailed
                        ? "bg-red-50 hover:bg-red-100 border-b border-red-200"
                        : "bg-green-50 hover:bg-green-100 border-b border-green-200"
                        }`}
                    onClick={() => toggleIteration(index)}
                >
                    <div className="flex items-center">
                        <span
                            className="mr-2 text-gray-600 transition-transform duration-200"
                            style={{ transform: isExpanded ? "rotate(90deg)" : "rotate(0)" }}
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
                            </svg>
                        </span>

                        <span className="font-medium text-gray-800">
                            {(() => {
                                const indexFeature = iterationData.features?.find(
                                    (f) => f.name?.toLowerCase() === "index"
                                );
                                return indexFeature ? (
                                    <span>Index: {indexFeature.value}</span>
                                ) : null;
                            })()}
                        </span>

                        <div className="ml-4 hidden sm:block">
                            <div className="flex items-center">
                                <div className="w-24 bg-gray-200 rounded-full h-2.5 mr-2">
                                    <div
                                        className={`${hasFailed ? "bg-red-600" : "bg-green-600"} h-2.5 rounded-full`}
                                        style={{ width: `${passRate}%` }}
                                    ></div>
                                </div>
                                <span className="text-xs text-gray-600">
                                    {passedFeatures}/{totalFeatures} features passed
                                </span>
                            </div>
                        </div>
                    </div>

                    <div className="flex items-center">
                        {processingTimeFeature && (
                            <span className="mr-3 text-sm text-gray-500 hidden sm:block">
                                <span className="font-medium">Time:</span> {processingTimeFeature.value.toFixed(1)}s
                            </span>
                        )}
                        <span
                            className={`px-3 py-1 rounded-full text-white text-sm font-medium ${hasFailed ? "bg-red-600" : "bg-green-600"
                                }`}
                        >
                            {hasFailed ? "FAILED" : "PASSED"}
                        </span>
                    </div>
                </div>

                {isExpanded && (
                    <div className="bg-white">
                        {hasFailed && iterationData.status.failure_reasons?.length > 0 && (
                            <div className="p-3 bg-red-50 border-b border-red-100">
                                <p className="font-medium text-red-800 mb-1">Failure Reasons:</p>
                                <ul className="list-disc pl-5 text-red-700 space-y-1">
                                    {iterationData.status.failure_reasons.map((reason, idx) => (
                                        <li key={idx}>{reason}</li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        <div className="p-3 border-b bg-gray-50 flex flex-wrap gap-2">
                            <button
                                className="text-xs bg-blue-100 hover:bg-blue-200 text-blue-800 font-medium py-1 px-2 rounded"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    const table = document.getElementById(`features-table-${index}`);
                                    const rows = table.querySelectorAll("tbody tr");
                                    rows.forEach((row) => (row.style.display = ""));
                                }}
                            >
                                Show All
                            </button>
                            <button
                                className="text-xs bg-red-100 hover:bg-red-200 text-red-800 font-medium py-1 px-2 rounded"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    const table = document.getElementById(`features-table-${index}`);
                                    const rows = table.querySelectorAll("tbody tr");
                                    rows.forEach((row) => {
                                        row.style.display = row.classList.contains("failed-feature") ? "" : "none";
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
                                    const rows = table.querySelectorAll("tbody tr");
                                    rows.forEach((row) => {
                                        row.style.display = row.classList.contains("passed-feature") ? "" : "none";
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
                                        <th className="py-2 px-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b w-1/4">
                                            Feature
                                        </th>
                                        <th className="py-2 px-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b w-1/4">
                                            Value
                                        </th>
                                        <th className="py-2 px-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b w-2/4">
                                            Tolerance Check
                                        </th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {displayFeatures.map((feature, featureIdx) => {
                                        const tc = feature.tolerance_check;
                                        const hasFailed = tc && !tc.error && !tc.within_tolerance;
                                        const hasPassed = tc && !tc.error && tc.within_tolerance;
                                        const tolerance = tc?.tolerance || 0;
                                        const distance = tc?.distance || 0;
                                        const utilization = tolerance > 0 ? Math.abs(distance / tolerance) * 100 : 0;

                                        return (
                                            <tr
                                                key={featureIdx}
                                                className={`border-b hover:bg-gray-50 ${hasFailed ? "bg-red-50 failed-feature" : hasPassed ? "passed-feature" : ""
                                                    }`}
                                            >
                                                <td className="py-3 px-4 font-medium">
                                                    <div className="flex items-center">
                                                        {hasFailed && (
                                                            <span className="inline-flex items-center justify-center mr-2 w-5 h-5 bg-red-100 text-red-800 rounded-full">
                                                                ×
                                                            </span>
                                                        )}
                                                        {hasPassed && (
                                                            <span className="inline-flex items-center justify-center mr-2 w-5 h-5 bg-green-100 text-green-800 rounded-full">
                                                                ✓
                                                            </span>
                                                        )}
                                                        {feature.name}
                                                    </div>
                                                </td>
                                                <td
                                                    className="py-3 px-4 font-mono"
                                                    style={{
                                                        color: feature.value_color?.startsWith("#")
                                                            ? feature.value_color
                                                            : feature.value_color
                                                                ? `#${feature.value_color}`
                                                                : undefined,
                                                        fontWeight: hasFailed ? "bold" : "normal",
                                                    }}
                                                >
                                                    {typeof feature.value === "object" && feature.value !== null
                                                        ? JSON.stringify(feature.value)
                                                        : typeof feature.value === "number"
                                                            ? feature.value.toFixed(3)
                                                            : feature.value}
                                                </td>
                                                <td className="py-3 px-4">
                                                    {!tc ? (
                                                        <span className="text-gray-500 italic">No tolerance defined</span>
                                                    ) : tc.error ? (
                                                        <span className="text-gray-500 italic">{tc.error}</span>
                                                    ) : (
                                                        <div>
                                                            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-2 text-sm">
                                                                <div>
                                                                    <span className="text-gray-600 text-xs">Target:</span>{" "}
                                                                    <span className="ml-1 font-medium">{tc.target}</span>
                                                                </div>
                                                                <div>
                                                                    <span className="text-gray-600 text-xs">Tolerance:</span>{" "}
                                                                    <span className="ml-1 font-medium">±{tc.tolerance}</span>
                                                                </div>
                                                                <div>
                                                                    <span className="text-gray-600 text-xs">Distance:</span>{" "}
                                                                    <span
                                                                        className={`ml-1 font-medium ${hasFailed ? "text-red-700" : "text-gray-800"
                                                                            }`}
                                                                    >
                                                                        {distance.toFixed(3)}
                                                                    </span>
                                                                </div>
                                                                <div>
                                                                    <span className="text-gray-600 text-xs">Remaining:</span>{" "}
                                                                    <span
                                                                        className={`ml-1 font-medium ${tc.tolerance_remaining < 0
                                                                            ? "text-red-700"
                                                                            : tc.tolerance_remaining / tolerance < 0.2
                                                                                ? "text-yellow-700"
                                                                                : "text-green-700"
                                                                            }`}
                                                                    >
                                                                        {tc.tolerance_remaining?.toFixed(3) || "N/A"}
                                                                    </span>
                                                                </div>
                                                            </div>
                                                            {tolerance > 0 && (
                                                                <div className="mb-1">
                                                                    <div className="flex items-center">
                                                                        <div className="flex-grow h-4 bg-gray-200 rounded-full overflow-hidden relative">
                                                                            <div className="absolute inset-y-0 left-1/2 w-0.5 bg-black z-10"></div>
                                                                            <div
                                                                                className={`absolute inset-y-0 h-full ${hasFailed ? "bg-red-600" : "bg-green-600"
                                                                                    }`}
                                                                                style={{
                                                                                    width: `${Math.min(100, utilization)}%`,
                                                                                    left: "50%",
                                                                                    transform:
                                                                                        feature.value < tc.target
                                                                                            ? "translateX(-100%)"
                                                                                            : "none",
                                                                                }}
                                                                            ></div>
                                                                        </div>
                                                                        <span
                                                                            className={`ml-2 text-xs ${hasFailed ? "text-red-700" : "text-green-700"
                                                                                }`}
                                                                        >
                                                                            {utilization.toFixed(1)}%
                                                                        </span>
                                                                    </div>
                                                                    <div className="flex justify-between text-xs text-gray-500 mt-1">
                                                                        <span>{(tc.target - tc.tolerance).toFixed(1)}</span>
                                                                        <span>{tc.target}</span>
                                                                        <span>{(tc.target + tc.tolerance).toFixed(1)}</span>
                                                                    </div>
                                                                </div>
                                                            )}
                                                        </div>
                                                    )}
                                                </td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>

                        <div className="p-3 bg-gray-50 border-t text-sm text-gray-600 flex flex-wrap gap-4">
                            {processingTimeFeature && (
                                <div>
                                    <span className="font-medium">Processing Time:</span>{" "}
                                    {processingTimeFeature.value.toFixed(2)}s
                                </div>
                            )}
                            <div>
                                <span className="font-medium">Feature Pass Rate:</span> {passedFeatures}/{totalFeatures} (
                                {passRate.toFixed(1)}%)
                            </div>
                            <div>
                                <button
                                    className="text-blue-600 hover:text-blue-800 font-medium"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        const failed = displayFeatures.find(
                                            (f) => f.tolerance_check && !f.tolerance_check.error && !f.tolerance_check.within_tolerance
                                        );
                                        const first = displayFeatures[0];
                                        setSelectedFeature(failed ? failed.name : first?.name);
                                        document.getElementById("feature-chart-section")?.scrollIntoView({ behavior: "smooth" });
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
        <div className="min-h-screen flex flex-col lg:flex-row">
            <div
                className={`w-full ${showResults ? 'lg:w-1/2' : 'lg:w-full'} bg-white shadow-md rounded-lg p-4 md:p-6 overflow-y-auto lg:h-screen lg:sticky lg:top-20`}
            >
                <div className="flex flex-col md:flex-row justify-between items-center mb-6">
                    <h1 className="text-xl md:text-2xl font-bold text-blue-800">
                        <span className="flex items-center">
                            <svg
                                className="w-6 h-6 mr-2"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                                xmlns="http://www.w3.org/2000/svg"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth="2"
                                    d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                                ></path>
                            </svg>
                            Scan Results Dashboard
                        </span>
                    </h1>
                    <button
                        onClick={() => setShowResults((prev) => !prev)}
                        className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                    >
                        {showResults ? 'Hide Results' : 'Show Results'}
                    </button>
                </div>
                {renderEnhancedSummary()}
                {renderControlPanel()}
                <div id="feature-chart-section">
                    {selectedFeature && (
                        <FeatureChart
                            data={latestScan.scan_results}
                            selectedFeature={selectedFeature}
                        />
                    )}
                </div>
            </div>
            {showResults && (
                <div className="w-full lg:w-1/2 bg-white p-4 md:p-6 overflow-y-auto lg:h-screen">
                    <div className="mb-4 bg-white p-3 rounded-lg shadow-sm border flex justify-between items-center">
                        <span className="text-gray-700">
                            Showing {filteredIterations.length} of{' '}
                            {latestScan.scan_results.length} iterations
                        </span>
                    </div>
                    <div className="flex flex-col gap-4">
                        {filteredIterations.length > 0 ? (
                            filteredIterations.slice().reverse().map((iteration, idx) => (
                                <div key={idx} className="w-full">
                                    {renderIteration(iteration, idx)}
                                </div>
                            ))
                        ) : (
                            <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 text-center">
                                <div className="text-gray-400 mb-2">
                                    <svg
                                        className="w-12 h-12 mx-auto"
                                        fill="none"
                                        stroke="currentColor"
                                        viewBox="0 0 24 24"
                                        xmlns="http://www.w3.org/2000/svg"
                                    >
                                        <path
                                            strokeLinecap="round"
                                            strokeLinejoin="round"
                                            strokeWidth="2"
                                            d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                                        ></path>
                                    </svg>
                                </div>
                                <p className="text-gray-600 text-lg">
                                    No results match your filters
                                </p>
                                <p className="text-gray-500 mt-1">
                                    Try adjusting your search criteria
                                </p>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

export default DebugDashboard;