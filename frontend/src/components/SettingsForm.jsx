import React, { useState } from "react";

/**
 * Settings form component for system configuration
 */
const SettingsForm = () => {
  const [settings, setSettings] = useState({
    dataRefreshRate: 1000,
    chartTimespan: 5,
    darkMode: true,
    alarmEnabled: true,
    alarmThresholds: {
      spo2Min: 90,
      bpmMin: 50,
      bpmMax: 120,
      perfusionMin: 5
    }
  });

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    
    if (name.includes('.')) {
      // Handle nested properties like alarmThresholds.spo2Min
      const [parent, child] = name.split('.');
      setSettings({
        ...settings,
        [parent]: {
          ...settings[parent],
          [child]: type === 'checkbox' ? checked : Number(value)
        }
      });
    } else {
      setSettings({
        ...settings,
        [name]: type === 'checkbox' ? checked : (type === 'number' ? Number(value) : value)
      });
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    console.log('Settings saved:', settings);
    // Here you would save settings to backend/localStorage
    alert('Settings saved!');
  };

  return (
    <form className="settings-form" onSubmit={handleSubmit}>
      <div className="settings-section">
        <h3>Display Settings</h3>
        
        <div className="form-group">
          <label htmlFor="dataRefreshRate">Data Refresh Rate (ms):</label>
          <input
            type="number"
            id="dataRefreshRate"
            name="dataRefreshRate"
            value={settings.dataRefreshRate}
            onChange={handleInputChange}
            min="500"
            max="5000"
            step="100"
          />
        </div>

        <div className="form-group">
          <label htmlFor="chartTimespan">Chart Timespan (minutes):</label>
          <input
            type="number"
            id="chartTimespan"
            name="chartTimespan"
            value={settings.chartTimespan}
            onChange={handleInputChange}
            min="1"
            max="30"
          />
        </div>

        <div className="form-group checkbox-group">
          <input
            type="checkbox"
            id="darkMode"
            name="darkMode"
            checked={settings.darkMode}
            onChange={handleInputChange}
          />
          <label htmlFor="darkMode">Dark Mode</label>
        </div>
      </div>

      <div className="settings-section">
        <h3>Alarm Settings</h3>
        
        <div className="form-group checkbox-group">
          <input
            type="checkbox"
            id="alarmEnabled"
            name="alarmEnabled"
            checked={settings.alarmEnabled}
            onChange={handleInputChange}
          />
          <label htmlFor="alarmEnabled">Enable Alarms</label>
        </div>

        <div className="form-group">
          <label htmlFor="alarmThresholds.spo2Min">SpO₂ Minimum (%):</label>
          <input
            type="number"
            id="alarmThresholds.spo2Min"
            name="alarmThresholds.spo2Min"
            value={settings.alarmThresholds.spo2Min}
            onChange={handleInputChange}
            min="80"
            max="100"
          />
        </div>

        <div className="form-group">
          <label htmlFor="alarmThresholds.bpmMin">Heart Rate Minimum (BPM):</label>
          <input
            type="number"
            id="alarmThresholds.bpmMin"
            name="alarmThresholds.bpmMin"
            value={settings.alarmThresholds.bpmMin}
            onChange={handleInputChange}
            min="30"
            max="100"
          />
        </div>

        <div className="form-group">
          <label htmlFor="alarmThresholds.bpmMax">Heart Rate Maximum (BPM):</label>
          <input
            type="number"
            id="alarmThresholds.bpmMax"
            name="alarmThresholds.bpmMax"
            value={settings.alarmThresholds.bpmMax}
            onChange={handleInputChange}
            min="60"
            max="200"
          />
        </div>

        <div className="form-group">
          <label htmlFor="alarmThresholds.perfusionMin">Perfusion Minimum (%):</label>
          <input
            type="number"
            id="alarmThresholds.perfusionMin"
            name="alarmThresholds.perfusionMin"
            value={settings.alarmThresholds.perfusionMin}
            onChange={handleInputChange}
            min="1"
            max="20"
          />
        </div>
      </div>

      <div className="form-actions">
        <button type="submit" className="save-button">Save Settings</button>
      </div>
    </form>
  );
};

export default SettingsForm;