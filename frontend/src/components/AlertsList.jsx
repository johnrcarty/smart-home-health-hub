import { useState, useEffect } from 'react';
import config from '../config';

const AlertsList = ({ onClose }) => {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showAcknowledged, setShowAcknowledged] = useState(false);

  useEffect(() => {
    fetchAlerts();
  }, [showAcknowledged]);

  const fetchAlerts = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(
        `${config.apiUrl}/api/monitoring/alerts?include_acknowledged=${showAcknowledged}`
      );

      if (!response.ok) {
        throw new Error(`Error fetching alerts: ${response.statusText}`);
      }

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
      const response = await fetch(
        `${config.apiUrl}/api/monitoring/alerts/${alertId}/acknowledge`,
        { method: 'POST' }
      );

      if (!response.ok) {
        throw new Error(`Error acknowledging alert: ${response.statusText}`);
      }

      fetchAlerts();
    } catch (err) {
      console.error(`Error acknowledging alert ${alertId}:`, err);
      setError('Failed to acknowledge alert. Please try again.');
    }
  };

  const formatDateTime = (isoString) => {
    if (!isoString) return 'N/A';
    const date = new Date(isoString);
    return date.toLocaleString();
  };

  const formatDuration = (start, end) => {
    if (!start || !end) return 'Ongoing';

    const startTime = new Date(start).getTime();
    const endTime = new Date(end).getTime();
    const durationMs = endTime - startTime;

    const minutes = Math.floor(durationMs / 60000);
    const seconds = Math.floor((durationMs % 60000) / 1000);

    return `${minutes}m ${seconds}s`;
  };

  return (
    <div className="alerts-list">
      <div className="alerts-controls">
        <button 
          onClick={fetchAlerts} 
          className="refresh-button"
          disabled={loading}
        >
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
        <table className="alerts-table">
          <thead>
            <tr>
              <th>Start Time</th>
              <th>Duration</th>
              <th>SpO₂ Min/Max</th>
              <th>BPM Min/Max</th>
              <th>Alarms</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {alerts.map(alert => (
              <tr key={alert.id} className={alert.acknowledged ? 'acknowledged' : 'unacknowledged'}>
                <td>{formatDateTime(alert.start_time)}</td>
                <td>{formatDuration(alert.start_time, alert.end_time)}</td>
                <td>
                  {alert.spo2_min !== null && alert.spo2_max !== null
                    ? `${alert.spo2_min} - ${alert.spo2_max}%`
                    : 'N/A'}
                </td>
                <td>
                  {alert.bpm_min !== null && alert.bpm_max !== null
                    ? `${alert.bpm_min} - ${alert.bpm_max} BPM`
                    : 'N/A'}
                </td>
                <td>
                  {alert.spo2_alarm_triggered ? 'SpO₂ ' : ''}
                  {alert.hr_alarm_triggered ? 'Heart Rate ' : ''}
                  {alert.external_alarm_triggered ? 'External ' : ''}
                  {!alert.spo2_alarm_triggered && !alert.hr_alarm_triggered && 
                   !alert.external_alarm_triggered ? 'None' : ''}
                </td>
                <td>
                  {!alert.end_time ? (
                    <span className="status active">Active</span>
                  ) : alert.acknowledged ? (
                    <span className="status acknowledged">Acknowledged</span>
                  ) : (
                    <span className="status unacknowledged">Unacknowledged</span>
                  )}
                </td>
                <td>
                  {!alert.acknowledged && (
                    <button 
                      onClick={() => acknowledgeAlert(alert.id)}
                      className="acknowledge-button"
                    >
                      Acknowledge
                    </button>
                  )}
                  <button className="view-button">View Details</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default AlertsList;
