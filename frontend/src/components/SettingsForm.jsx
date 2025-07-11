import React, { useState, useEffect } from "react";
import { getSettings, updateSettings } from '../services/settings';
import config from '../config';
import GpioSettings from './GpioSettings';

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

  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

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

    loadSettings();
  }, []);

  const handleInputChange = (key, value) => {
    setFormData(prev => ({
      ...prev,
      [key]: value
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

  if (isLoading) {
    return <div className="loading">Loading settings...</div>;
  }

  return (
    <form onSubmit={handleSubmit} className="settings-form">
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
      
      <div className="settings-section">
        <h2>External Alarm Configuration</h2>
        <GpioSettings />
      </div>
      
      {error && <div className="error-message">{error}</div>}
      {success && <div className="success-message">Settings saved successfully!</div>}
      
      <div className="form-actions">
        <button type="submit" className="button primary" disabled={isSubmitting}>
          {isSubmitting ? 'Saving...' : 'Save Settings'}
        </button>
      </div>
    </form>
  );
};

export default SettingsForm;