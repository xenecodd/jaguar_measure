import React, { useEffect, useState } from "react";
import { apiService } from "../services/api.service";
import { Check, Save, Loader, HelpCircle } from "lucide-react";

const Config = () => {
  const [config, setConfig] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [activeTooltip, setActiveTooltip] = useState(null);
  
  const editableKeys = [
    "pick",
    "use_agg",
    "put_back",
    "drop_object",
    "vel_mul",
    "range_",
    "save_point_clouds",
    "save_to_db",
    "same_object",
    "same_place_index",
  ];

  // Descriptions for each config option (you can customize these)
  const descriptions = {
    "pick": "Enable item pickup functionality",
    "use_agg": "Enable matplotlib aggregation for disable plot window",
    "put_back": "Allow putting items back in their original position",
    "drop_object": "Enable dropping objects in the scene",
    "vel_mul": "Velocity multiplier for movement",
    "range_": "Cycle range",
    "save_point_clouds": "Save point cloud data to disk",
    "save_to_db": "Store results in database",
    "same_object": "Treat as same object instance",
    "same_place_index": "Index for same place identification"
  };

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const data = await apiService.GetConfig();
        setConfig(data);
      } catch (error) {
        console.error("Config loading failed:", error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchConfig();
  }, []);

  const handleChange = (key, value) => {
    setConfig((prev) => ({
      ...prev,
      [key]: value,
    }));
    setSaveSuccess(false);
  };

  const handleSubmit = async () => {
    setIsSaving(true);
    try {
      await apiService.SetConfig(config);
      setSaveSuccess(true);
      
      // Reset success message after 3 seconds
      setTimeout(() => {
        setSaveSuccess(false);
      }, 3000);
    } catch (error) {
      console.error("Config update failed:", error);
      alert("Update failed. Please try again.");
    } finally {
      setIsSaving(false);
    }
  };

  const formatLabel = (key) => {
    return key
      .replace(/_/g, ' ')
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <Loader className="w-8 h-8 mx-auto animate-spin text-blue-500" />
          <p className="mt-2 text-gray-600">Loading configuration...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-8 bg-white rounded-lg shadow-md">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-800">Configuration Settings</h2>
        <button
          onClick={handleSubmit}
          disabled={isSaving}
          className={`flex items-center gap-2 px-4 py-2 rounded-md text-white font-medium transition-all ${
            saveSuccess 
              ? "bg-green-500 hover:bg-green-600" 
              : "bg-blue-500 hover:bg-blue-600"
          } disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          {isSaving ? (
            <Loader className="w-4 h-4 animate-spin" />
          ) : saveSuccess ? (
            <Check className="w-4 h-4" />
          ) : (
            <Save className="w-4 h-4" />
          )}
          {saveSuccess ? "Saved" : isSaving ? "Saving..." : "Save Changes"}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {editableKeys.map((key) => {
          const value = config[key];
          const isBoolean = typeof value === "boolean";
          const isNumber = typeof value === "number";
          const isString = typeof value === "string";
          const isSimpleValue = isBoolean || isNumber || isString;
          
          return (
            <div key={key} className="relative">
              <div className="bg-gray-50 p-4 rounded-lg border border-gray-200 hover:border-gray-300 transition-all">
                <div className="flex justify-between items-start mb-2">
                  <label className="text-sm font-medium text-gray-700 flex items-center gap-1">
                    {formatLabel(key)}
                    <div className="relative">
                      <HelpCircle 
                        className="w-4 h-4 text-gray-400 cursor-help" 
                        onMouseEnter={() => setActiveTooltip(key)}
                        onMouseLeave={() => setActiveTooltip(null)}
                      />
                      {activeTooltip === key && (
                        <div className="absolute left-0 bottom-6 w-48 p-2 bg-gray-800 text-white text-xs rounded shadow-lg z-10">
                          {descriptions[key] || "Configuration setting"}
                        </div>
                      )}
                    </div>
                  </label>
                  {isBoolean && (
                    <div className="relative inline-block w-10 align-middle select-none">
                      <input
                        type="checkbox"
                        id={`toggle-${key}`}
                        className="sr-only"
                        checked={value}
                        onChange={(e) => handleChange(key, e.target.checked)}
                      />
                      <label
                        htmlFor={`toggle-${key}`}
                        className={`block overflow-hidden h-6 rounded-full cursor-pointer transition-colors ${
                          value ? "bg-blue-500" : "bg-gray-300"
                        }`}
                      >
                        <span
                          className={`block h-6 w-6 rounded-full bg-white shadow transform transition-transform ${
                            value ? "translate-x-4" : "translate-x-0"
                          }`}
                        />
                      </label>
                    </div>
                  )}
                </div>

                {isNumber && (
                  <input
                    type="number"
                    value={value}
                    onChange={(e) => handleChange(key, Number(e.target.value))}
                    className="w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                )}

                {isString && (
                  <input
                    type="text"
                    value={value}
                    onChange={(e) => handleChange(key, e.target.value)}
                    className="w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                )}

                {!isSimpleValue && (
                  <div>
                    <textarea
                      value={JSON.stringify(value, null, 2)}
                      onChange={(e) => {
                        try {
                          handleChange(key, JSON.parse(e.target.value));
                        } catch (error) {
                        }
                      }}
                      rows={3}
                      className="w-full p-2 font-mono text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default Config;