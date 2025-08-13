import React, { useState, useEffect } from 'react';
import { getSettings, updateSettings } from '../../services/settings';
import config from '../../config';

/**
 * Dashboard settings component for configuring what's displayed on the main dashboard
 */
const DashboardSettings = () => {
  const [formData, setFormData] = useState({
    chart_time_range: '5m', // '1m', '3m', '5m', '10m', '30m', '1h'
    show_blood_pressure_card: true,
    show_temperature_card: true,
    show_alerts_count: true,
    chart_refresh_rate: 1000, // milliseconds
    data_retention_minutes: 30,
    show_statistics: true,
    temperature_display_mode: 'both', // 'body', 'skin', 'both'
    dashboard_chart_1_vital: '', // First sub-chart vital type
    dashboard_chart_2_vital: '', // Second sub-chart vital type
  });

  const [availableVitals, setAvailableVitals] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  // Load dashboard settings on component mount
  useEffect(() => {
    const loadDashboardSettings = async () => {
      try {
        setIsLoading(true);
        
        // Load both settings and available vitals in parallel
        const [settingsResponse, vitalsResponse] = await Promise.all([
          getSettings(),
          fetch(`${config.apiUrl}/api/vitals/types`)
        ]);
        
        console.log('Loaded settings from backend:', settingsResponse);
        
        // Process vitals response
        let vitalsData = [];
        if (vitalsResponse.ok) {
          vitalsData = await vitalsResponse.json();
          console.log('Loaded available vitals:', vitalsData);
        }
        
        // Add default vital types that are always available
        const defaultVitals = ['bp', 'temperature'];
        const allVitals = [...new Set([...defaultVitals, ...vitalsData])];
        setAvailableVitals(allVitals);
        
        const dashboardFormData = {};
        for (const [key, setting] of Object.entries(settingsResponse)) {
          // Only include dashboard-related settings
          if (key.startsWith('show_') || key.includes('chart_') || key.includes('dashboard_') || key.includes('display_mode') || key.includes('retention') || key.includes('time_range')) {
            dashboardFormData[key] = setting.value;
            console.log(`Found dashboard setting: ${key} = ${setting.value}`);
          }
        }
        
        console.log('Dashboard form data to apply:', dashboardFormData);
        
        // Only update state if we received some dashboard settings
        if (Object.keys(dashboardFormData).length > 0) {
          setFormData(prev => ({
            ...prev,
            ...dashboardFormData
          }));
        }
        
        setError(null);
      } catch (err) {
        console.error("Error loading dashboard settings:", err);
        setError("Failed to load dashboard settings. Please try again.");
      } finally {
        setIsLoading(false);
      }
    };

    loadDashboardSettings();
  }, []);

  const handleInputChange = (key, value) => {
    setFormData(prev => ({
      ...prev,
      [key]: value
    }));
  };

  // Helper function to get available options for each chart dropdown
  const getAvailableVitalsForChart = (chartNumber) => {
    const otherChartKey = chartNumber === 1 ? 'dashboard_chart_2_vital' : 'dashboard_chart_1_vital';
    const otherChartValue = formData[otherChartKey];
    
    return availableVitals.filter(vital => vital !== otherChartValue || vital === '');
  };

  // Helper function to format vital display names
  const formatVitalDisplayName = (vital) => {
    const displayNames = {
      'bp': 'Blood Pressure',
      'temperature': 'Temperature',
      'bathroom': 'Bathroom',
      'weight': 'Weight',
      'calories': 'Calories',
      'water': 'Water Intake'
    };
    
    return displayNames[vital] || vital.charAt(0).toUpperCase() + vital.slice(1);
  };

  const handleSubmit = async () => {
    setError(null);
    setSuccess(false);
    setIsSubmitting(true);

    try {
      // Convert numeric inputs to numbers
      const settingsToUpdate = {
        chart_time_range: formData.chart_time_range,
        show_blood_pressure_card: formData.show_blood_pressure_card,
        show_temperature_card: formData.show_temperature_card,
        show_alerts_count: formData.show_alerts_count,
        chart_refresh_rate: parseInt(formData.chart_refresh_rate),
        data_retention_minutes: parseInt(formData.data_retention_minutes),
        show_statistics: formData.show_statistics,
        temperature_display_mode: formData.temperature_display_mode,
        dashboard_chart_1_vital: formData.dashboard_chart_1_vital,
        dashboard_chart_2_vital: formData.dashboard_chart_2_vital,
      };

      console.log('Saving dashboard settings:', settingsToUpdate);
      const result = await updateSettings(settingsToUpdate);
      console.log('Settings save result:', result);
      
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      console.error("Error saving dashboard settings:", err);
      setError("Failed to save dashboard settings. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return <div style={{ color: '#ffffff', textAlign: 'center', padding: '20px' }}>Loading dashboard settings...</div>;
  }

  return (
    <div>
      <h3 style={{ 
        color: '#ffffff', 
        fontSize: '1.25rem', 
        marginBottom: '16px',
        fontWeight: '600'
      }}>Dashboard Configuration</h3>
      
      {/* Chart Time Range */}
      <div style={{ marginBottom: '24px' }}>
        <h4 style={{ 
          color: '#ffffff', 
          fontSize: '1.1rem', 
          marginBottom: '12px',
          fontWeight: '500'
        }}>Chart Time Range</h4>
        <div>
          <label style={{ 
            color: '#e2e8f0', 
            fontSize: '13px', 
            fontWeight: '500', 
            marginBottom: '6px', 
            display: 'block' 
          }}>Time Range Displayed in Charts</label>
          <select
            value={formData.chart_time_range}
            onChange={(e) => handleInputChange('chart_time_range', e.target.value)}
            style={{
              width: '100%',
              padding: '10px 12px',
              backgroundColor: '#2d3748',
              border: '1px solid #4a5568',
              borderRadius: '6px',
              color: '#ffffff',
              fontSize: '14px',
              outline: 'none',
              cursor: 'pointer',
              boxSizing: 'border-box'
            }}
          >
            <option value="1m">1 Minute</option>
            <option value="3m">3 Minutes</option>
            <option value="5m">5 Minutes</option>
            <option value="10m">10 Minutes</option>
            <option value="30m">30 Minutes</option>
            <option value="1h">1 Hour</option>
          </select>
          <div style={{ 
            color: '#cbd5e0', 
            fontSize: '12px', 
            marginTop: '6px',
            fontStyle: 'italic'
          }}>
            Controls how much historical data is shown in the SpO₂, Heart Rate, and Perfusion charts
          </div>
        </div>
      </div>

        {/* Card Display Options */}
        <div style={{ marginBottom: '24px' }}>
          <h4 style={{ 
            color: '#ffffff', 
            fontSize: '1.1rem', 
            marginBottom: '12px',
            fontWeight: '500'
          }}>Dashboard Cards</h4>
          
          {/* Sub-chart Selection */}
          <div style={{ marginBottom: '16px' }}>
            <h5 style={{ 
              color: '#e2e8f0', 
              fontSize: '1rem', 
              marginBottom: '8px',
              fontWeight: '500'
            }}>Vital Charts Selection</h5>
            <div style={{ 
              color: '#cbd5e0', 
              fontSize: '12px', 
              marginBottom: '12px',
              fontStyle: 'italic'
            }}>
              Choose which vitals to display in the two sub-charts. Each vital can only be used once.
            </div>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <div>
                <label style={{ 
                  color: '#e2e8f0', 
                  fontSize: '13px', 
                  fontWeight: '500', 
                  marginBottom: '6px', 
                  display: 'block' 
                }}>Chart 1 - Vital Type</label>
                <select
                  value={formData.dashboard_chart_1_vital}
                  onChange={(e) => handleInputChange('dashboard_chart_1_vital', e.target.value)}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    backgroundColor: '#2d3748',
                    border: '1px solid #4a5568',
                    borderRadius: '6px',
                    color: '#ffffff',
                    fontSize: '14px',
                    outline: 'none',
                    cursor: 'pointer',
                    boxSizing: 'border-box'
                  }}
                >
                  <option value="">Select a vital type...</option>
                  {getAvailableVitalsForChart(1).map(vital => (
                    <option key={vital} value={vital}>
                      {formatVitalDisplayName(vital)}
                    </option>
                  ))}
                </select>
              </div>
              
              <div>
                <label style={{ 
                  color: '#e2e8f0', 
                  fontSize: '13px', 
                  fontWeight: '500', 
                  marginBottom: '6px', 
                  display: 'block' 
                }}>Chart 2 - Vital Type</label>
                <select
                  value={formData.dashboard_chart_2_vital}
                  onChange={(e) => handleInputChange('dashboard_chart_2_vital', e.target.value)}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    backgroundColor: '#2d3748',
                    border: '1px solid #4a5568',
                    borderRadius: '6px',
                    color: '#ffffff',
                    fontSize: '14px',
                    outline: 'none',
                    cursor: 'pointer',
                    boxSizing: 'border-box'
                  }}
                >
                  <option value="">Select a vital type...</option>
                  {getAvailableVitalsForChart(2).map(vital => (
                    <option key={vital} value={vital}>
                      {formatVitalDisplayName(vital)}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>
          
          {/* Existing Card Toggles */}
          <div style={{ display: 'grid', gap: '12px' }}>
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '10px', 
              padding: '12px',
              backgroundColor: '#1a202c',
              borderRadius: '6px',
              border: '1px solid #4a5568'
            }}>
              <input
                type="checkbox"
                checked={formData.show_blood_pressure_card}
                onChange={(e) => handleInputChange('show_blood_pressure_card', e.target.checked)}
                style={{
                  width: '18px',
                  height: '18px',
                  accentColor: '#007bff',
                  cursor: 'pointer'
                }}
              />
              <label style={{ 
                color: '#ffffff', 
                fontSize: '14px', 
                fontWeight: '500',
                cursor: 'pointer'
              }}>Show Blood Pressure Card</label>
            </div>
            
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '10px', 
              padding: '12px',
              backgroundColor: '#1a202c',
              borderRadius: '6px',
              border: '1px solid #4a5568'
            }}>
              <input
                type="checkbox"
                checked={formData.show_temperature_card}
                onChange={(e) => handleInputChange('show_temperature_card', e.target.checked)}
                style={{
                  width: '18px',
                  height: '18px',
                  accentColor: '#007bff',
                  cursor: 'pointer'
                }}
              />
              <label style={{ 
                color: '#ffffff', 
                fontSize: '14px', 
                fontWeight: '500',
                cursor: 'pointer'
              }}>Show Temperature Card</label>
            </div>
            
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '10px', 
              padding: '12px',
              backgroundColor: '#1a202c',
              borderRadius: '6px',
              border: '1px solid #4a5568'
            }}>
              <input
                type="checkbox"
                checked={formData.show_statistics}
                onChange={(e) => handleInputChange('show_statistics', e.target.checked)}
                style={{
                  width: '18px',
                  height: '18px',
                  accentColor: '#007bff',
                  cursor: 'pointer'
                }}
              />
              <label style={{ 
                color: '#ffffff', 
                fontSize: '14px', 
                fontWeight: '500',
                cursor: 'pointer'
              }}>Show Value Statistics (Min/Max/Avg)</label>
            </div>
          </div>
        </div>

        {/* Performance Settings */}
        <div style={{ marginBottom: '24px' }}>
          <h4 style={{ 
            color: '#ffffff', 
            fontSize: '1.1rem', 
            marginBottom: '12px',
            fontWeight: '500'
          }}>Performance & Data</h4>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div>
              <label style={{ 
                color: '#e2e8f0', 
                fontSize: '13px', 
                fontWeight: '500', 
                marginBottom: '6px', 
                display: 'block' 
              }}>Chart Refresh Rate (ms)</label>
              <input
                type="number"
                value={formData.chart_refresh_rate}
                onChange={(e) => handleInputChange('chart_refresh_rate', e.target.value)}
                min="100"
                max="5000"
                step="100"
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  backgroundColor: '#2d3748',
                  border: '1px solid #4a5568',
                  borderRadius: '6px',
                  color: '#ffffff',
                  fontSize: '14px',
                  outline: 'none',
                  boxSizing: 'border-box'
                }}
              />
            </div>
            <div>
              <label style={{ 
                color: '#e2e8f0', 
                fontSize: '13px', 
                fontWeight: '500', 
                marginBottom: '6px', 
                display: 'block' 
              }}>Data Retention (minutes)</label>
              <input
                type="number"
                value={formData.data_retention_minutes}
                onChange={(e) => handleInputChange('data_retention_minutes', e.target.value)}
                min="5"
                max="120"
                step="5"
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  backgroundColor: '#2d3748',
                  border: '1px solid #4a5568',
                  borderRadius: '6px',
                  color: '#ffffff',
                  fontSize: '14px',
                  outline: 'none',
                  boxSizing: 'border-box'
                }}
              />
            </div>
          </div>
        </div>

        {/* Temperature Display Mode */}
        <div style={{ marginBottom: '24px' }}>
          <h4 style={{ 
            color: '#ffffff', 
            fontSize: '1.1rem', 
            marginBottom: '12px',
            fontWeight: '500'
          }}>Temperature Display</h4>
          <div>
            <label style={{ 
              color: '#e2e8f0', 
              fontSize: '13px', 
              fontWeight: '500', 
              marginBottom: '6px', 
              display: 'block' 
            }}>Temperature Display Mode</label>
            <select
              value={formData.temperature_display_mode}
              onChange={(e) => handleInputChange('temperature_display_mode', e.target.value)}
              style={{
                width: '100%',
                padding: '10px 12px',
                backgroundColor: '#2d3748',
                border: '1px solid #4a5568',
                borderRadius: '6px',
                color: '#ffffff',
                fontSize: '14px',
                outline: 'none',
                cursor: 'pointer',
                boxSizing: 'border-box'
              }}
            >
              <option value="both">Show Both Body & Skin Temperature</option>
              <option value="body">Show Body Temperature Only</option>
              <option value="skin">Show Skin Temperature Only</option>
            </select>
          </div>
        </div>

        {error && (
          <div style={{ 
            backgroundColor: '#fed7d7', 
            color: '#c53030', 
            padding: '10px 12px', 
            borderRadius: '6px', 
            marginBottom: '12px',
            fontSize: '13px'
          }}>{error}</div>
        )}
        {success && (
          <div style={{ 
            backgroundColor: '#c6f6d5', 
            color: '#2f855a', 
            padding: '10px 12px', 
            borderRadius: '6px', 
            marginBottom: '12px',
            fontSize: '13px'
          }}>Dashboard settings saved successfully!</div>
        )}
        
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '16px' }}>
          <button 
            onClick={handleSubmit}
            disabled={isSubmitting}
            style={{
              backgroundColor: '#007bff',
              color: '#ffffff',
              border: 'none',
              borderRadius: '6px',
              padding: '10px 24px',
              fontSize: '14px',
              fontWeight: '500',
              cursor: isSubmitting ? 'not-allowed' : 'pointer',
              opacity: isSubmitting ? 0.6 : 1,
              transition: 'all 0.2s ease'
            }}
          >
            {isSubmitting ? 'Saving...' : 'Save Dashboard Settings'}
          </button>
        </div>
    </div>
  );
};

export default DashboardSettings;
