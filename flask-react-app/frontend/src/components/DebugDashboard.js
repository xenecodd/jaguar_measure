import React, { useEffect, useState } from "react";
import { apiService } from "../services/api.service";
import StatusCard from "./StatusCard"

const DebugDashboard = () => {
    const [latestScan, setLatestScan] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [expandedIterations, setExpandedIterations] = useState({});

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
                        status: {
                            ...iteration.status,
                            ok: iteration.status?.ok === true || iteration.status?.ok === "true"
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

                // Log processed scan results for debugging
                console.log(
                    "Processed scan results:",
                    correctedData.scan_results.map(scan => ({
                        iteration: scan.iteration,
                        ok: scan.status.ok
                    }))
                );

                setLoading(false);
            } catch (error) {
                console.error('Latest scan could not be retrieved:', error);
                setError('Failed to load scan data. Please try again later.');
                setLoading(false);
            }
        };
        fetchLatestScan();
    }, []);

    const toggleIteration = (index) => {
        setExpandedIterations(prev => ({
            ...prev,
            [index]: !prev[index]
        }));
    };

    const expandAll = () => {
        const allExpanded = {};
        if (latestScan && latestScan.scan_results) {
            latestScan.scan_results.forEach((_, index) => {
                allExpanded[index] = true;
            });
        }
        setExpandedIterations(allExpanded);
    };

    const collapseAll = () => {
        const allCollapsed = {};
        if (latestScan && latestScan.scan_results) {
            latestScan.scan_results.forEach((_, index) => {
                allCollapsed[index] = false;
            });
        }
        setExpandedIterations(allCollapsed);
    };

    const filterFailedOnly = () => {
        const failedOnly = {};
        if (latestScan && latestScan.scan_results) {
            latestScan.scan_results.forEach((iteration, index) => {
                // Expand only the failed iterations
                failedOnly[index] = !iteration.status.ok;
            });
        }
        setExpandedIterations(failedOnly);
    };

    if (loading) {
        return (
            <div className="flex justify-center items-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-jaguar-blue"></div>
            </div>
        );
    }

    if (error) {
        return <div className="text-red-500 p-4 text-center">{error}</div>;
    }

    if (!latestScan || !latestScan.scan_results) {
        return <div className="text-gray-500 p-4 text-center">No scan data available</div>;
    }

    // Calculate statistics for QA
    const calculateStats = () => {
        const stats = {
            total: latestScan.scan_results.length,
            passed: 0,
            failed: 0,
            failureReasons: {}
        };

        latestScan.scan_results.forEach(iteration => {
            if (iteration.status.ok) {
                stats.passed++;
            } else {
                stats.failed++;
                if (iteration.status.failure_reasons) {
                    iteration.status.failure_reasons.forEach(reason => {
                        if (!stats.failureReasons[reason]) {
                            stats.failureReasons[reason] = 0;
                        }
                        stats.failureReasons[reason]++;
                    });
                }
            }
        });

        return stats;
    };

    const stats = calculateStats();

    // Enhanced Summary section
    const renderEnhancedSummary = () => {
        const { total, passed, failed, color } = calculateStats();
        const passRate = (passed / total * 100) || 0;

        return (
            <div className="mb-6 rounded-lg border overflow-hidden">
                <div className="p-3 font-bold bg-gray-100 border-b">
                    Scan Summary
                </div>
                <div className="p-4" style={{ backgroundColor: `#${color ||'ffffff'}30` }}>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                        <StatusCard
                            title="Total Iterations"
                            value={total}
                            className=""
                            textColor="text-black"
                            bgColor="bg-gray-200"
                        />
                        <StatusCard
                            title="Passed"
                            value={passed}
                            className=""
                            textColor="text-"
                            bgColor="bg-green-600"
                        />
                        <StatusCard
                            title="Failed"
                            value={failed}
                            className=""
                            textColor="text-black"
                            bgColor="bg-red-600"
                        />
                        <StatusCard
                            title="Pass Rate"
                            value={`${passRate.toFixed(1)}%`}
                            className=""
                            textColor={`text-${color || 'black'}`}
                            bgColor="bg-blue-600"
                        />
                    </div>
                </div>

                {/* Common failure reasons section */}
                {stats.failed > 0 && (
                    <div className="mt-4 bg-white p-3 rounded shadow">
                        <p className="font-semibold mb-2">Common Failure Reasons:</p>
                        <ul className="list-disc pl-5">
                            {Object.entries(stats.failureReasons)
                                .sort(([_, countA], [__, countB]) => countB - countA)
                                .map(([reason, count], idx) => (
                                    <li key={idx} className="text-red-700">
                                        {reason} <span className="text-gray-600">({count} occurrences)</span>
                                    </li>
                                ))
                            }
                        </ul>
                    </div>
                )}
            </div>
        );
    };

    // Control buttons for QA
    const renderControls = () => {
        return (
            <div className="mb-4 flex gap-2 flex-wrap">
                <button
                    onClick={expandAll}
                    className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm"
                >
                    Expand All
                </button>
                <button
                    onClick={collapseAll}
                    className="bg-gray-600 hover:bg-gray-700 text-white px-3 py-1 rounded text-sm"
                >
                    Collapse All
                </button>
                <button
                    onClick={filterFailedOnly}
                    className="bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded text-sm"
                >
                    Show Failed Only
                </button>
            </div>
        );
    };

    // Renders a single iteration section with its features
    const renderIteration = (iterationData, index) => {
        const isExpanded = expandedIterations[index];
        const hasFailed = !iterationData.status.ok;

        return (
            <div key={index} className="mb-4 border rounded-lg overflow-hidden">
                <div
                    className="p-3 font-semibold flex justify-between items-center cursor-pointer"
                    style={{
                        backgroundColor: hasFailed
                            ? "#FFEBEE" // Light red background for failed iterations
                            : `#${iterationData.background_color || 'f5f5f5'}`
                    }}
                    onClick={() => toggleIteration(index)}
                >
                    <div className="flex items-center">
                        <span className="mr-2">
                            {isExpanded ? "▼" : "►"}
                        </span>
                        <span>Iteration {iterationData.iteration}</span>
                    </div>
                    <span
                        className="px-3 py-1 rounded-full text-white text-sm"
                        style={{ backgroundColor: `#${iterationData.status.color || '000000'}` }}
                    >
                        {iterationData.status.ok ? "PASS" : "FAIL"}
                    </span>
                </div>

                {isExpanded && (
                    <div className="bg-white">
                        {/* Failure reasons at the top if any */}
                        {hasFailed && iterationData.status.failure_reasons && iterationData.status.failure_reasons.length > 0 && (
                            <div className="p-3 bg-red-50 border-b">
                                <p className="font-semibold text-red-700">Failure Reasons:</p>
                                <ul className="list-disc pl-5 text-red-700">
                                    {iterationData.status.failure_reasons.map((reason, idx) => (
                                        <li key={idx}>{reason}</li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        <div className="overflow-x-auto">
                            <table className="min-w-full bg-white border-b">
                                <thead>
                                    <tr className="bg-gray-100">
                                        <th className="py-2 px-4 text-left border-b w-1/4">Feature</th>
                                        <th className="py-2 px-4 text-left border-b w-1/4">Value</th>
                                        <th className="py-2 px-4 text-left border-b w-2/4">Tolerance Check</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {iterationData.features.map((feature, featureIdx) => {
                                        // Check if this feature has failed tolerance check
                                        const hasFailedTolerance = feature.tolerance_check &&
                                            !feature.tolerance_check.error &&
                                            !feature.tolerance_check.within_tolerance;

                                        return (
                                            <tr
                                                key={featureIdx}
                                                className={`border-b ${hasFailedTolerance ? 'bg-red-50' : ''}`}
                                            >
                                                <td className="py-2 px-4 font-medium">{feature.name}</td>
                                                <td
                                                    className="py-2 px-4 font-mono"
                                                    style={{
                                                        color: feature.value_color ? `#${feature.value_color}` : 'inherit',
                                                        fontWeight: hasFailedTolerance ? 'bold' : 'normal'
                                                    }}
                                                >
                                                    {typeof feature.value === 'object'
                                                        ? JSON.stringify(feature.value)
                                                        : feature.value}
                                                </td>
                                                <td className="py-2 px-4">
                                                    {feature.tolerance_check ? (
                                                        <div>
                                                            {feature.tolerance_check.error ? (
                                                                <span className="text-gray-500 italic">{feature.tolerance_check.error}</span>
                                                            ) : (
                                                                <div className="flex flex-col">
                                                                    <div className="grid grid-cols-2 gap-2 mb-2">
                                                                        <div>
                                                                            <span className="text-gray-600 text-sm">Target:</span>
                                                                            <span className="ml-2 font-medium">{feature.tolerance_check.target}</span>
                                                                        </div>
                                                                        <div>
                                                                            <span className="text-gray-600 text-sm">Tolerance:</span>
                                                                            <span className="ml-2 font-medium">±{feature.tolerance_check.tolerance}</span>
                                                                        </div>
                                                                        <div>
                                                                            <span className="text-gray-600 text-sm">Distance:</span>
                                                                            <span className="ml-2 font-medium">{feature.tolerance_check.distance?.toFixed(3)}</span>
                                                                        </div>
                                                                        <div>
                                                                            <span className="text-gray-600 text-sm">Remaining:</span>
                                                                            <span className="ml-2 font-medium">{feature.tolerance_check.tolerance_remaining?.toFixed(3) || 'N/A'}</span>
                                                                        </div>
                                                                    </div>

                                                                    {/* Progress bar visualization */}
                                                                    {feature.tolerance_check.tolerance > 0 && (
                                                                        <div className="mb-2">
                                                                            <div className="h-4 bg-gray-200 rounded overflow-hidden">
                                                                                <div
                                                                                    className="h-full"
                                                                                    style={{
                                                                                        width: `${Math.min(100, (feature.tolerance_check.distance / feature.tolerance_check.tolerance) * 100)}%`,
                                                                                        backgroundColor: `#${feature.tolerance_check.gradient_color || feature.tolerance_check.color || '000000'}`
                                                                                    }}
                                                                                ></div>
                                                                            </div>
                                                                            <div className="flex justify-between text-xs text-gray-600 mt-1">
                                                                                <span>0</span>
                                                                                <span>Tolerance: {feature.tolerance_check.tolerance}</span>
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
                    </div>
                )}
            </div>
        );
    };

    return (
        <div className="max-w-6xl mx-auto p-4 md:p-6">
            <div className="bg-white shadow-md rounded-lg p-4 md:p-6 mb-8">
                <div className="flex justify-between items-center mb-6">
                    <h1 className="text-xl md:text-2xl font-bold text-jaguar-blue">Scan Results Dashboard</h1>
                    <div className="text-sm text-gray-500">
                        {new Date().toLocaleString()}
                    </div>
                </div>

                {/* Enhanced Summary section */}
                {renderEnhancedSummary()}

                {/* Control buttons */}
                {renderControls()}

                {/* Individual iteration sections */}
                <div>
                    {latestScan.scan_results.map((iteration, idx) => (
                        renderIteration(iteration, idx)
                    ))}
                </div>
            </div>
        </div>
    );
};

export default DebugDashboard;