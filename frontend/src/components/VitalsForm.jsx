import { useState } from 'react';
import config from '../config';

const VitalsForm = ({ onSave, onClose }) => {
  const [formData, setFormData] = useState({
    bloodPressure: { systolic: '', diastolic: '' },
    temperature: { body: '' },
    nutrition: { calories: '', water: '' },
    weight: '',
    notes: '',
    bathroom: { type: '', size: '' }
  });
  const [showNutrition, setShowNutrition] = useState(false);
  const [showWeight, setShowWeight] = useState(false);
  const [showNotes, setShowNotes] = useState(false);
  const [showBathroom, setShowBathroom] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const handleInputChange = (category, field, value) => {
    if (category) {
      setFormData(prev => ({
        ...prev,
        [category]: {
          ...prev[category],
          [field]: value
        }
      }));
    } else {
      setFormData(prev => ({
        ...prev,
        [field]: value
      }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    
    try {
      // Prepare the data in the format expected by the API
      const payload = {
        datetime: new Date().toISOString(),
        bp: {
          systolic_bp: formData.bloodPressure.systolic ? parseInt(formData.bloodPressure.systolic) : null,
          diastolic_bp: formData.bloodPressure.diastolic ? parseInt(formData.bloodPressure.diastolic) : null,
          map_bp: calculateMAP(formData.bloodPressure.systolic, formData.bloodPressure.diastolic)
        },
        temp: {
          body_temp: formData.temperature.body ? parseFloat(formData.temperature.body) : null,
        },
        nutrition: {
          calories: formData.nutrition.calories ? parseInt(formData.nutrition.calories) : null,
          water_ml: formData.nutrition.water ? parseInt(formData.nutrition.water) : null,
        },
        weight: formData.weight ? parseFloat(formData.weight) : null,
        notes: formData.notes
      };
      
      console.log("Submitting vitals payload:", payload);
      
      // Send data to API
      const response = await fetch(`${config.apiUrl}/api/vitals/manual`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });
      
      const responseData = await response.json();
      
      if (!response.ok) {
        throw new Error(responseData.message || `Error saving vitals: ${response.statusText}`);
      }
      
      console.log("Vitals saved successfully:", responseData);
      
      setSuccess(true);
      if (onSave) {
        onSave(responseData);
      }
      
      // Reset form after successful submission
      setTimeout(() => {
        setFormData({
          bloodPressure: {
            systolic: '',
            diastolic: '',
          },
          temperature: {
            body: '',
          },
          nutrition: {
            calories: '',
            water: '',
          },
          weight: '',
          notes: '',
          bathroom: { type: '', size: '' } // <-- Ensure bathroom field is always present
        });
        setSuccess(false);
      }, 2000);
      
    } catch (err) {
      console.error("Error saving vitals:", err);
      setError(err.message || "Error saving vitals. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };
  
  // Calculate MAP (Mean Arterial Pressure)
  const calculateMAP = (systolic, diastolic) => {
    if (!systolic || !diastolic) return null;
    const sys = parseInt(systolic);
    const dia = parseInt(diastolic);
    return Math.round(dia + (sys - dia) / 3);
  };

  return (
    <form onSubmit={handleSubmit} className="vitals-form">
      <div className="expandable-buttons-row" style={{ marginBottom: 24 }}>
        <button type="button" className="expand-btn" onClick={() => setShowNutrition(v => !v)}>Nutrition {showNutrition ? '-' : '+'}</button>
        <button type="button" className="expand-btn" onClick={() => setShowWeight(v => !v)}>Weight {showWeight ? '-' : '+'}</button>
        <button type="button" className="expand-btn" onClick={() => setShowNotes(v => !v)}>Notes {showNotes ? '-' : '+'}</button>
        <button type="button" className="expand-btn" onClick={() => setShowBathroom(v => !v)}>Bathroom {showBathroom ? '-' : '+'}</button>
      </div>
      <div className="form-section">
        <h3>Blood Pressure</h3>
        <div className="form-row">
          <div className="form-group">
            <label htmlFor="systolic">Systolic (mmHg)</label>
            <input
              type="number"
              id="systolic"
              value={formData.bloodPressure.systolic}
              onChange={(e) => handleInputChange('bloodPressure', 'systolic', e.target.value)}
              placeholder="120"
              min="60"
              max="250"
            />
          </div>
          <div className="form-group">
            <label htmlFor="diastolic">Diastolic (mmHg)</label>
            <input
              type="number"
              id="diastolic"
              value={formData.bloodPressure.diastolic}
              onChange={(e) => handleInputChange('bloodPressure', 'diastolic', e.target.value)}
              placeholder="80"
              min="30"
              max="150"
            />
          </div>
        </div>
      </div>
      <div className="form-section">
        <h3>Temperature</h3>
        <div className="form-group">
          <label htmlFor="body-temp">Body Temperature (°F)</label>
          <input
            type="number"
            id="body-temp"
            value={formData.temperature.body}
            onChange={(e) => handleInputChange('temperature', 'body', e.target.value)}
            placeholder="98.6"
            step="0.1"
            min="95"
            max="105"
          />
        </div>
      </div>
      {showNutrition && (
        <div className="form-section">
          <h3>Nutrition</h3>
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="calories">Calories</label>
              <input
                type="number"
                id="calories"
                value={formData.nutrition.calories}
                onChange={(e) => handleInputChange('nutrition', 'calories', e.target.value)}
                placeholder="2000"
                min="0"
              />
            </div>
            <div className="form-group">
              <label htmlFor="water">Water (mL)</label>
              <input
                type="number"
                id="water"
                value={formData.nutrition.water}
                onChange={(e) => handleInputChange('nutrition', 'water', e.target.value)}
                placeholder="2000"
                min="0"
              />
            </div>
          </div>
        </div>
      )}
      {showWeight && (
        <div className="form-section">
          <h3>Weight</h3>
          <div className="form-group">
            <label htmlFor="weight">Weight (lbs)</label>
            <input
              type="number"
              id="weight"
              value={formData.weight}
              onChange={(e) => handleInputChange(null, 'weight', e.target.value)}
              placeholder="150"
              step="0.1"
              min="0"
            />
          </div>
        </div>
      )}
      {showNotes && (
        <div className="form-section">
          <h3>Notes</h3>
          <div className="form-group">
            <label htmlFor="notes">Notes</label>
            <textarea
              id="notes"
              value={formData.notes}
              onChange={(e) => handleInputChange(null, 'notes', e.target.value)}
              placeholder="Any additional notes..."
              rows="3"
            ></textarea>
          </div>
        </div>
      )}
      {showBathroom && (
        <div className="form-section">
          <h3>Bathroom</h3>
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="bathroom-type">Type</label>
              <select id="bathroom-type" value={formData.bathroom.type} onChange={e => handleInputChange('bathroom', 'type', e.target.value)}>
                <option value="">Select</option>
                <option value="dry">Dry</option>
                <option value="wet">Wet</option>
                <option value="solid">Solid</option>
                <option value="mix">Mix</option>
              </select>
            </div>
            <div className="form-group">
              <label htmlFor="bathroom-size">Size</label>
              <select id="bathroom-size" value={formData.bathroom.size} onChange={e => handleInputChange('bathroom', 'size', e.target.value)}>
                <option value="">Select</option>
                <option value="smear">Smear</option>
                <option value="s">Small</option>
                <option value="m">Medium</option>
                <option value="l">Large</option>
                <option value="xl">Extra Large</option>
              </select>
            </div>
          </div>
        </div>
      )}
      {error && <div className="error-message">{error}</div>}
      {success && <div className="success-message">Vitals saved successfully!</div>}
      <div className="form-actions">
        <button type="button" onClick={onClose} className="button secondary">Cancel</button>
        <button type="submit" className="button primary" disabled={isSubmitting}>
          {isSubmitting ? 'Saving...' : 'Save Vitals'}
        </button>
      </div>
    </form>
  );
};

export default VitalsForm;