import { useState, useEffect } from 'react';
import config from '../config';

const GpioSettings = () => {
  const [settings, setSettings] = useState({
    alarm1_device: 'vent',
    alarm2_device: 'pulseox',
    alarm1_recovery_time: 30,
    alarm2_recovery_time: 30,
    gpio_enabled: false
  });
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    // Load settings from the API
    const fetchSettings = async () => {
      try {
        setLoading(true);
        const response = await fetch(`${config.apiUrl}/api/settings`);
        if (!response.ok) throw new Error('Failed to load settings');
        const data = await response.json();
        // Extract the settings we need
        const newSettings = {
          alarm1_device: data.alarm1_device?.value || 'vent',
          alarm2_device: data.alarm2_device?.value || 'pulseox',
          alarm1_recovery_time: data.alarm1_recovery_time?.value || 30,
          alarm2_recovery_time: data.alarm2_recovery_time?.value || 30,
          gpio_enabled: data.gpio_enabled?.value === true || data.gpio_enabled?.value === 'true' ? true : false
        };
        setSettings(newSettings);
        setError(null);
      } catch (err) {
        console.error('Error loading settings:', err);
        setError('Failed to load settings. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    fetchSettings();
  }, []);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setSettings(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleSubmit = async () => {
    try {
      setLoading(true);
      setError(null);
      // Prepare the settings payload
      const payload = {
        settings: {
          alarm1_device: settings.alarm1_device,
          alarm2_device: settings.alarm2_device,
          alarm1_recovery_time: parseInt(settings.alarm1_recovery_time),
          alarm2_recovery_time: parseInt(settings.alarm2_recovery_time),
          gpio_enabled: settings.gpio_enabled
        }
      };
      
      const response = await fetch(`${config.apiUrl}/api/settings`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });
      
      if (!response.ok) throw new Error('Failed to save settings');
      
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      console.error('Error saving settings:', err);
      setError('Failed to save settings. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (loading && !settings.alarm1_device) {
    return <div className="loading">Loading settings...</div>;
  }

  return (
    <div className="gpio-settings">
      <h3>RJ9 Alarm Settings</h3>
      {error && <div className="error-message">{error}</div>}
      {success && <div className="success-message">Settings saved successfully!</div>}
      <div className="settings-grid">
        <div className="setting-group">
          <label>
            <input
              type="checkbox"
              name="gpio_enabled"
              checked={settings.gpio_enabled}
              onChange={handleChange}
            />
            Enable GPIO Monitoring
          </label>
        </div>
        <div className="setting-group">
          <label>RJ9 Port #1 Device Type:</label>
          <select 
            name="alarm1_device"
            value={settings.alarm1_device}
            onChange={handleChange}
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
            value={settings.alarm1_recovery_time}
            onChange={handleChange}
            min="5"
            max="300"
          />
        </div>
        <div className="setting-group">
          <label>RJ9 Port #2 Device Type:</label>
          <select 
            name="alarm2_device"
            value={settings.alarm2_device}
            onChange={handleChange}
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
            value={settings.alarm2_recovery_time}
            onChange={handleChange}
            min="5"
            max="300"
          />
        </div>
      </div>
      <div className="button-row">
        <button 
          className="primary-button"
          disabled={loading}
          onClick={handleSubmit}
        >
          {loading ? 'Saving...' : 'Save Settings'}
        </button>
      </div>
      <div className="info-section">
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
  );
};

export default GpioSettings;