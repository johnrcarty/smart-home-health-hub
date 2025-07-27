import React, { useState, useEffect } from "react";
import { getSettings, updateSettings } from '../services/settings';
import config from '../config';

/**
 * Settings form component for system configuration
 */
const SettingsForm = () => {
  const [formData, setFormData] = useState({
    device_name: '',
    device_location: '',
    min_spo2: 90,
    max_spo2: 100,
    min_bpm: 55,
    max_bpm: 155,
    temp_unit: 'F',
    weight_unit: 'lbs',
    dark_mode: true,
  });

  const [gpioSettings, setGpioSettings] = useState({
    alarm1_device: 'vent',
    alarm2_device: 'pulseox',
    alarm1_recovery_time: 30,
    alarm2_recovery_time: 30,
    gpio_enabled: false
  });

  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [gpioLoading, setGpioLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [gpioError, setGpioError] = useState(null);
  const [gpioSuccess, setGpioSuccess] = useState(false);
  const [activeTab, setActiveTab] = useState('general');

  // Load settings on component mount
  useEffect(() => {
    const loadSettings = async () => {
      try {
        setIsLoading(true);
        const settings = await getSettings();
        
        const newFormData = {};
        for (const [key, setting] of Object.entries(settings)) {
          newFormData[key] = setting.value;
        }
        
        // Only update state if we received some settings
        if (Object.keys(newFormData).length > 0) {
          setFormData(prev => ({
            ...prev,
            ...newFormData
          }));
        }
        
        setError(null);
      } catch (err) {
        console.error("Error loading settings:", err);
        setError("Failed to load settings. Please try again.");
      } finally {
        setIsLoading(false);
      }
    };

    // Load GPIO settings
    const fetchGpioSettings = async () => {
      try {
        setGpioLoading(true);
        const response = await fetch(`${config.apiUrl}/api/settings`);
        if (!response.ok) throw new Error('Failed to load settings');
        const data = await response.json();
        const newSettings = {
          alarm1_device: data.alarm1_device?.value || 'vent',
          alarm2_device: data.alarm2_device?.value || 'pulseox',
          alarm1_recovery_time: data.alarm1_recovery_time?.value || 30,
          alarm2_recovery_time: data.alarm2_recovery_time?.value || 30,
          gpio_enabled: data.gpio_enabled?.value === true || data.gpio_enabled?.value === 'true' ? true : false
        };
        setGpioSettings(newSettings);
        setGpioError(null);
      } catch (err) {
        setGpioError('Failed to load GPIO settings. Please try again.');
      } finally {
        setGpioLoading(false);
      }
    };

    loadSettings();
    fetchGpioSettings();
  }, []);

  const handleInputChange = (key, value) => {
    setFormData(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const handleGpioChange = (e) => {
    const { name, value, type, checked } = e.target;
    setGpioSettings(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccess(false);
    setIsSubmitting(true);

    try {
      // Convert numeric inputs to numbers
      const settingsToUpdate = {
        device_name: formData.device_name,
        device_location: formData.device_location,
        min_spo2: parseInt(formData.min_spo2),
        max_spo2: parseInt(formData.max_spo2),
        min_bpm: parseInt(formData.min_bpm),
        max_bpm: parseInt(formData.max_bpm),
        temp_unit: formData.temp_unit,
        weight_unit: formData.weight_unit,
        dark_mode: formData.dark_mode,
      };

      await updateSettings(settingsToUpdate);
      setSuccess(true);
    } catch (err) {
      console.error("Error saving settings:", err);
      setError("Failed to save settings. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleGpioSubmit = async (e) => {
    e.preventDefault();
    setGpioError(null);
    setGpioSuccess(false);
    setGpioLoading(true);
    try {
      const payload = {
        settings: {
          alarm1_device: gpioSettings.alarm1_device,
          alarm2_device: gpioSettings.alarm2_device,
          alarm1_recovery_time: parseInt(gpioSettings.alarm1_recovery_time),
          alarm2_recovery_time: parseInt(gpioSettings.alarm2_recovery_time),
          gpio_enabled: gpioSettings.gpio_enabled
        }
      };
      const response = await fetch(`${config.apiUrl}/api/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!response.ok) throw new Error('Failed to save GPIO settings');
      setGpioSuccess(true);
      setTimeout(() => setGpioSuccess(false), 3000);
    } catch (err) {
      setGpioError('Failed to save GPIO settings. Please try again.');
    } finally {
      setGpioLoading(false);
    }
  };

  if (isLoading) {
    return <div className="loading">Loading settings...</div>;
  }

  return (
    <div className="settings-tabs-container">
      <div className="settings-tabs">
        <button
          className={activeTab === 'general' ? 'tab active' : 'tab'}
          onClick={() => setActiveTab('general')}
        >
          General
        </button>
        <button
          className={activeTab === 'thresholds' ? 'tab active' : 'tab'}
          onClick={() => setActiveTab('thresholds')}
        >
          Thresholds
        </button>
      </div>
      <form onSubmit={handleSubmit} className="settings-form">
        {activeTab === 'general' && (
          <>
            <div className="form-section">
              <h3>Device Settings</h3>
              <div className="form-group">
                <label htmlFor="device_name">Device Name</label>
                <input
                  type="text"
                  id="device_name"
                  value={formData.device_name}
                  onChange={(e) => handleInputChange('device_name', e.target.value)}
                />
              </div>
              <div className="form-group">
                <label htmlFor="device_location">Location</label>
                <input
                  type="text"
                  id="device_location"
                  value={formData.device_location}
                  onChange={(e) => handleInputChange('device_location', e.target.value)}
                />
              </div>
            </div>
            <div className="form-section">
              <h3>Display Settings</h3>
              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="temp_unit">Temperature Unit</label>
                  <select
                    id="temp_unit"
                    value={formData.temp_unit}
                    onChange={(e) => handleInputChange('temp_unit', e.target.value)}
                  >
                    <option value="F">Fahrenheit (°F)</option>
                    <option value="C">Celsius (°C)</option>
                  </select>
                </div>
                <div className="form-group">
                  <label htmlFor="weight_unit">Weight Unit</label>
                  <select
                    id="weight_unit"
                    value={formData.weight_unit}
                    onChange={(e) => handleInputChange('weight_unit', e.target.value)}
                  >
                    <option value="lbs">Pounds (lbs)</option>
                    <option value="kg">Kilograms (kg)</option>
                  </select>
                </div>
              </div>
              <div className="form-group checkbox-group">
                <label>
                  <input
                    type="checkbox"
                    checked={formData.dark_mode}
                    onChange={(e) => handleInputChange('dark_mode', e.target.checked)}
                  />
                  Dark Mode
                </label>
              </div>
            </div>
          </>
        )}
        {activeTab === 'thresholds' && (
          <>
            <div className="form-section">
              <h3>Alert Thresholds</h3>
              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="min_spo2">Min SpO₂ (%)</label>
                  <input
                    type="number"
                    id="min_spo2"
                    value={formData.min_spo2}
                    onChange={(e) => handleInputChange('min_spo2', e.target.value)}
                    min="80"
                    max="99"
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="max_spo2">Max SpO₂ (%)</label>
                  <input
                    type="number"
                    id="max_spo2"
                    value={formData.max_spo2}
                    onChange={(e) => handleInputChange('max_spo2', e.target.value)}
                    min="90"
                    max="100"
                  />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="min_bpm">Min Heart Rate (BPM)</label>
                  <input
                    type="number"
                    id="min_bpm"
                    value={formData.min_bpm}
                    onChange={(e) => handleInputChange('min_bpm', e.target.value)}
                    min="40"
                    max="100"
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="max_bpm">Max Heart Rate (BPM)</label>
                  <input
                    type="number"
                    id="max_bpm"
                    value={formData.max_bpm}
                    onChange={(e) => handleInputChange('max_bpm', e.target.value)}
                    min="100"
                    max="220"
                  />
                </div>
              </div>
            </div>
            <div className="settings-section">
              <h2>External Alarm Configuration</h2>
              <form onSubmit={handleGpioSubmit} className="gpio-settings-form">
                <div className="gpio-settings-card" style={{ background: 'rgba(30,32,40,0.9)', borderRadius: 18, padding: 32, marginBottom: 24 }}>
                  <h3>RJ9 Alarm Settings</h3>
                  {gpioError && <div className="error-message">{gpioError}</div>}
                  {gpioSuccess && <div className="success-message">Settings saved successfully!</div>}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px 32px', alignItems: 'center' }}>
                    <div style={{ gridColumn: '1 / span 2', marginBottom: 8 }}>
                      <label style={{ display: 'flex', alignItems: 'center', fontSize: '1.2em' }}>
                        <input
                          type="checkbox"
                          name="gpio_enabled"
                          checked={gpioSettings.gpio_enabled}
                          onChange={handleGpioChange}
                          style={{ marginRight: 12, transform: 'scale(1.5)' }}
                        />
                        Enable GPIO Monitoring
                      </label>
                    </div>
                    <div className="setting-group">
                      <label>RJ9 Port #1 Device Type:</label>
                      <select 
                        name="alarm1_device"
                        value={gpioSettings.alarm1_device}
                        onChange={handleGpioChange}
                      >
                        <option value="vent">Ventilator</option>
                        <option value="pulseox">Pulse Oximeter</option>
                        <option value="other">Other Device</option>
                      </select>
                    </div>
                    <div className="setting-group">
                      <label>RJ9 Port #1 Recovery Time (seconds):</label>
                      <input
                        type="number"
                        name="alarm1_recovery_time"
                        value={gpioSettings.alarm1_recovery_time}
                        onChange={handleGpioChange}
                        min="5"
                        max="300"
                      />
                    </div>
                    <div className="setting-group">
                      <label>RJ9 Port #2 Device Type:</label>
                      <select 
                        name="alarm2_device"
                        value={gpioSettings.alarm2_device}
                        onChange={handleGpioChange}
                      >
                        <option value="vent">Ventilator</option>
                        <option value="pulseox">Pulse Oximeter</option>
                        <option value="other">Other Device</option>
                      </select>
                    </div>
                    <div className="setting-group">
                      <label>RJ9 Port #2 Recovery Time (seconds):</label>
                      <input
                        type="number"
                        name="alarm2_recovery_time"
                        value={gpioSettings.alarm2_recovery_time}
                        onChange={handleGpioChange}
                        min="5"
                        max="300"
                      />
                    </div>
                  </div>
                  <div className="button-row" style={{ marginTop: 24 }}>
                    <button 
                      className="primary-button"
                      disabled={gpioLoading}
                      type="submit"
                    >
                      {gpioLoading ? 'Saving...' : 'Save Settings'}
                    </button>
                  </div>
                  <div className="info-section" style={{ marginTop: 24 }}>
                    <h4>About RJ9 Alarm Connections</h4>
                    <p>
                      These settings configure how external device alarms connected via RJ9 phone lines
                      are processed. For each port, you can specify the device type and recovery time
                      (how long to wait before accepting a new alarm after an alert ends).
                    </p>
                    <p>
                      <strong>Note:</strong> Changes will take effect immediately without requiring a system restart.
                    </p>
                  </div>
                </div>
              </form>
            </div>
          </>
        )}
        {error && <div className="error-message">{error}</div>}
        {success && <div className="success-message">Settings saved successfully!</div>}
        <div className="form-actions">
          <button type="submit" className="button primary" disabled={isSubmitting}>
            {isSubmitting ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default SettingsForm;