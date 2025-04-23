import React, { useMemo } from "react";
import { Line } from "react-chartjs-2";
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Tooltip,
    Legend,
    Title,
    Filler
} from "chart.js";

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Tooltip,
    Legend,
    Title,
    Filler
);

const FeatureChart = ({ data, selectedFeature }) => {
    const chartData = useMemo(() => {
        // Extract feature data and tolerance information
        const featureValues = [];
        const toleranceInfo = { target: null, tolerance: null };
        
        data.forEach(item => {
            const feature = item.features.find(f => f.name === selectedFeature);
            
            if (feature) {
                featureValues.push({
                    iteration: item.iteration,
                    value: feature.value,
                    withinTolerance: feature.tolerance_check?.within_tolerance,
                    color: feature.value_color ? `#${feature.value_color}` : '#3b82f6'
                });
                
                // Store tolerance info from the first valid entry
                if (feature.tolerance_check && toleranceInfo.target === null) {
                    toleranceInfo.target = feature.tolerance_check.target;
                    toleranceInfo.tolerance = feature.tolerance_check.tolerance;
                }
            }
        });
        
        // Create upper and lower bound arrays if tolerance info exists
        const upperBoundData = [];
        const lowerBoundData = [];
        const targetLineData = [];
        
        if (toleranceInfo.target !== null) {
            data.forEach(() => {
                upperBoundData.push(toleranceInfo.target + toleranceInfo.tolerance);
                lowerBoundData.push(toleranceInfo.target - toleranceInfo.tolerance);
                targetLineData.push(toleranceInfo.target);
            });
        }
        
        return {
            labels: featureValues.map(item => `Iter ${item.iteration}`),
            datasets: [
                {
                    label: selectedFeature,
                    data: featureValues.map(item => item.value),
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    pointBackgroundColor: featureValues.map(item => item.color),
                    pointBorderColor: featureValues.map(item => item.withinTolerance === false ? '#FF0000' : '#00B050'),
                    pointBorderWidth: 2,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    tension: 0.3,
                    borderWidth: 2,
                    fill: false,
                },
                ...(toleranceInfo.target !== null ? [
                    {
                        label: 'Target',
                        data: targetLineData,
                        borderColor: '#000000',
                        borderWidth: 2,
                        borderDash: [5, 5],
                        pointRadius: 0,
                        fill: false,
                    },
                    {
                        label: 'Upper Bound',
                        data: upperBoundData,
                        borderColor: '#FF9800',
                        backgroundColor: 'rgba(255, 152, 0, 0.05)',
                        borderWidth: 1,
                        borderDash: [3, 3],
                        pointRadius: 0,
                        fill: '+1',
                    },
                    {
                        label: 'Lower Bound',
                        data: lowerBoundData,
                        borderColor: '#FF9800',
                        backgroundColor: 'rgba(255, 152, 0, 0.05)',
                        borderWidth: 1,
                        borderDash: [3, 3],
                        pointRadius: 0,
                        fill: false,
                    }
                ] : [])
            ]
        };
    }, [data, selectedFeature]);

    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'top',
                labels: {
                    usePointStyle: true,
                    padding: 20
                }
            },
            tooltip: {
                callbacks: {
                    label: function(context) {
                        let label = context.dataset.label || '';
                        if (label) {
                            label += ': ';
                        }
                        if (context.parsed.y !== null) {
                            label += context.parsed.y.toFixed(3);
                        }
                        return label;
                    },
                    footer: function(tooltipItems) {
                        const dataIndex = tooltipItems[0].dataIndex;
                        const feature = data[dataIndex]?.features.find(f => f.name === selectedFeature);
                        
                        if (feature?.tolerance_check) {
                            const { target, tolerance, distance, within_tolerance } = feature.tolerance_check;
                            return [
                                `Target: ${target}`,
                                `Tolerance: ±${tolerance}`,
                                `Distance: ${distance.toFixed(3)}`,
                                `Status: ${within_tolerance ? 'Within Tolerance' : 'Out of Tolerance'}`
                            ];
                        }
                        return '';
                    }
                }
            },
            title: {
                display: true,
                text: `Feature Trend Analysis: ${selectedFeature}`,
                font: {
                    size: 16,
                    weight: 'bold'
                },
                padding: {
                    top: 10,
                    bottom: 20
                }
            }
        },
        scales: {
            x: {
                grid: {
                    display: true,
                    color: 'rgba(0, 0, 0, 0.05)'
                }
            },
            y: {
                beginAtZero: false,
                grid: {
                    display: true,
                    color: 'rgba(0, 0, 0, 0.05)'
                }
            }
        }
    };

    // Compute feature statistics
    const featureStats = useMemo(() => {
        const values = data
            .map(item => item.features.find(f => f.name === selectedFeature)?.value)
            .filter(value => value !== undefined && value !== null);
        
        if (values.length === 0) return null;
        
        const sum = values.reduce((a, b) => a + b, 0);
        const avg = sum / values.length;
        const min = Math.min(...values);
        const max = Math.max(...values);
        
        const targetFeature = data[0]?.features.find(f => f.name === selectedFeature);
        const target = targetFeature?.tolerance_check?.target;
        const tolerance = targetFeature?.tolerance_check?.tolerance;
        
        return { avg, min, max, target, tolerance };
    }, [data, selectedFeature]);

    return (
        <div className="mb-8 bg-white p-4 rounded-lg shadow-md border border-gray-200">
            {selectedFeature ? (
                <>
                    {/* Feature stats summary */}
                    {featureStats && (
                        <div className="grid grid-cols-2 md:grid-cols-5 gap-2 mb-4">
                            <div className="bg-blue-50 p-3 rounded-md text-center border border-blue-100">
                                <div className="text-xs text-gray-500">Average</div>
                                <div className="font-bold text-blue-800">{featureStats.avg.toFixed(3)}</div>
                            </div>
                            <div className="bg-green-50 p-3 rounded-md text-center border border-green-100">
                                <div className="text-xs text-gray-500">Min</div>
                                <div className="font-bold text-green-800">{featureStats.min.toFixed(3)}</div>
                            </div>
                            <div className="bg-red-50 p-3 rounded-md text-center border border-red-100">
                                <div className="text-xs text-gray-500">Max</div>
                                <div className="font-bold text-red-800">{featureStats.max.toFixed(3)}</div>
                            </div>
                            {featureStats.target !== undefined && (
                                <>
                                    <div className="bg-purple-50 p-3 rounded-md text-center border border-purple-100">
                                        <div className="text-xs text-gray-500">Target</div>
                                        <div className="font-bold text-purple-800">{featureStats.target}</div>
                                    </div>
                                    <div className="bg-yellow-50 p-3 rounded-md text-center border border-yellow-100">
                                        <div className="text-xs text-gray-500">Tolerance</div>
                                        <div className="font-bold text-yellow-800">±{featureStats.tolerance}</div>
                                    </div>
                                </>
                            )}
                        </div>
                    )}
                    
                    {/* Chart container with fixed height */}
                    <div className="h-64 md:h-80">
                        <Line data={chartData} options={chartOptions} />
                    </div>
                    
                    {/* Legend explanation */}
                    <div className="mt-4 flex flex-wrap gap-4 justify-center text-sm text-gray-600">
                        <div className="flex items-center">
                            <span className="inline-block w-3 h-3 rounded-full bg-blue-500 mr-2"></span>
                            <span>Feature Values</span>
                        </div>
                        <div className="flex items-center">
                            <span className="inline-block w-3 h-3 rounded-full bg-black mr-2"></span>
                            <span>Target Value</span>
                        </div>
                        <div className="flex items-center">
                            <span className="inline-block w-6 h-1 bg-orange-500 mr-2"></span>
                            <span>Tolerance Range</span>
                        </div>
                        <div className="flex items-center">
                            <span className="inline-block w-3 h-3 rounded-full border-2 border-red-500 mr-2"></span>
                            <span>Out of Tolerance</span>
                        </div>
                        <div className="flex items-center">
                            <span className="inline-block w-3 h-3 rounded-full border-2 border-green-500 mr-2"></span>
                            <span>Within Tolerance</span>
                        </div>
                    </div>
                </>
            ) : (
                <div className="flex justify-center items-center h-64 text-gray-500">
                    Please select a feature to display its trend
                </div>
            )}
        </div>
    );
};

export default FeatureChart;