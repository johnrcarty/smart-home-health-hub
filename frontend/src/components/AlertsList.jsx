import { useState, useEffect } from 'react';
import config from '../config';
import AlertDetailModal from './AlertDetailModal';

const AlertsList = ({ onClose }) => {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showAcknowledged, setShowAcknowledged] = useState(false);
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [showAcknowledgeForm, setShowAcknowledgeForm] = useState(false);

  useEffect(() => {
    fetchAlerts();
  }, [showAcknowledged]);

  const fetchAlerts = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch(`${config.apiUrl}/api/monitoring/alerts?include_acknowledged=${showAcknowledged}`);
      if (!response.ok) throw new Error(`Error fetching alerts: ${response.statusText}`);
      const data = await response.json();
      setAlerts(data);
    } catch (err) {
      console.error('Error fetching alerts:', err);
      setError('Failed to load alerts. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const acknowledgeAlert = async (alertId) => {
    try {
      // Don't directly acknowledge from here anymore - let AlertDetailModal handle it
      // This will be called by the AlertDetailModal after it collects oxygen data
      console.log(`Alert ${alertId} acknowledged successfully via modal`);
      fetchAlerts(); // Refresh the alerts list
    } catch (err) {
      console.error(`Error acknowledging alert ${alertId}:`, err);
      setError('Failed to acknowledge alert. Please try again.');
    }
  };

  const handleViewDetails = (alert) => {
    setSelectedAlert(alert);
    setShowDetailModal(true);
  };

  const closeDetailModal = () => {
    setShowDetailModal(false);
    setSelectedAlert(null);
  };

  const handleAcknowledge = async (alertId) => {
    setSelectedAlert(alerts.find(a => a.id === alertId));
    setShowAcknowledgeForm(true);
  };

  const formatDateTime = (isoString) => {
    if (!isoString) return 'N/A';
    return new Date(isoString).toLocaleString();
  };

  const formatDuration = (start, end) => {
    if (!start || !end) return 'Ongoing';
    const durationMs = new Date(end) - new Date(start);
    const minutes = Math.floor(durationMs / 60000);
    const seconds = Math.floor((durationMs % 60000) / 1000);
    return `${minutes}m ${seconds}s`;
  };

  return (
    <div className="alerts-list">
      <div className="alerts-controls">
        <button onClick={fetchAlerts} className="refresh-button" disabled={loading}>
          {loading ? 'Loading...' : 'Refresh'}
        </button>
        <label className="toggle-switch">
          <input
            type="checkbox"
            checked={showAcknowledged}
            onChange={() => setShowAcknowledged(!showAcknowledged)}
          />
          <span className="slider round"></span>
          <span className="toggle-label">Show Acknowledged</span>
        </label>
      </div>

      {error && <div className="error-message">{error}</div>}

      {loading ? (
        <div className="loading">Loading alerts...</div>
      ) : alerts.length === 0 ? (
        <div className="no-data">No alerts found</div>
      ) : (
        <div className="alerts-grid">
          {alerts.map(alert => (
            <div
              key={alert.id}
              className={`alert-card ${alert.acknowledged ? 'acknowledged' : 'unacknowledged'}`}
            >
              <div className="alert-header">
                <div>
                  <strong>Start:</strong> {formatDateTime(alert.start_time)}
                </div>
                <div className="alert-status">
                  {!alert.end_time ? 'Active' : alert.acknowledged ? 'Acknowledged' : 'Unacknowledged'}
                </div>
              </div>

              <div className="alert-body">
                <div>
                  <strong>Duration:</strong> {formatDuration(alert.start_time, alert.end_time)}
                </div>
                <div>
                  <strong>SpO₂:</strong>{' '}
                  {alert.spo2_min !== null && alert.spo2_max !== null
                    ? `${alert.spo2_min} - ${alert.spo2_max}%`
                    : 'N/A'}
                </div>
                <div>
                  <strong>BPM:</strong>{' '}
                  {alert.bpm_min !== null && alert.bpm_max !== null
                    ? `${alert.bpm_min} - ${alert.bpm_max} BPM`
                    : 'N/A'}
                </div>
                <div>
                  <strong>Alarms:</strong>{' '}
                  {alert.alarm1_triggered ? 'Alarm1 ' : ''}
                  {alert.alarm2_triggered ? 'Alarm2 ' : ''}
                  {alert.spo2_alarm_triggered ? 'SpO₂ ' : ''}
                  {alert.hr_alarm_triggered ? 'BPM ' : ''}
                  {!alert.alarm1_triggered && !alert.alarm2_triggered && !alert.spo2_alarm_triggered && !alert.hr_alarm_triggered ? 'None' : ''}
                </div>
              </div>

              <div className="alert-actions">
                {!alert.acknowledged && (
                  <button onClick={() => handleAcknowledge(alert.id)} className="acknowledge-button">
                    Acknowledge
                  </button>
                )}
                <button 
                  className="view-button" 
                  onClick={() => handleViewDetails(alert)}
                >
                  View Details
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {selectedAlert && (
        <AlertDetailModal 
          alert={selectedAlert} 
          onClose={() => {
            setSelectedAlert(null);
            setShowAcknowledgeForm(false);
          }} 
          onAcknowledge={acknowledgeAlert}
          initiateAcknowledge={showAcknowledgeForm}
        />
      )}
    </div>
  );
};

export default AlertsList;
