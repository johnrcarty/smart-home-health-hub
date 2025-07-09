import { useState, useEffect, useMemo } from 'react';
import SimpleEventChart from './SimpleEventChart';
import config from '../config';

const AlertDetailModal = ({ alert, onClose, onAcknowledge }) => {
  const [eventData, setEventData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchEventData();
  }, [alert.id]);

  const fetchEventData = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch(`${config.apiUrl}/api/monitoring/alerts/${alert.id}/data`);
      if (!response.ok) throw new Error(`Error fetching alert data: ${response.statusText}`);
      const data = await response.json();
      
      // Add debug logs to check the data
      console.log(`Received ${data.length} data points for alert ${alert.id}`);
      if (data.length > 0) {
        console.log(`First data point:`, data[0]);
        console.log(`Data has spo2: ${data[0].spo2 !== undefined}, bpm: ${data[0].bpm !== undefined}`);
      }
      
      setEventData(data);
    } catch (err) {
      console.error(`Error fetching data for alert ${alert.id}:`, err);
      setError('Failed to load event data. Please try again.');
    } finally {
      setLoading(false);
    }
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

  const spo2ChartData = useMemo(() => {
    if (!eventData || eventData.length === 0) return [];
    return eventData.map((point) => ({
      x: new Date(point.timestamp).toLocaleTimeString(),
      y: point.spo2
    }));
  }, [eventData]);

  const bpmChartData = useMemo(() => {
    if (!eventData || eventData.length === 0) return [];
    return eventData.map((point) => ({
      x: new Date(point.timestamp).toLocaleTimeString(),
      y: point.bpm
    }));
  }, [eventData]);

  return (
    <div className="modal-backdrop">
      <div className="modal-content alert-detail-modal">
        <div className="modal-header">
          <h2>Alert Event Details</h2>
          <button className="close-button" onClick={onClose}>×</button>
        </div>

        <div className="modal-body">
          <div className="alert-info-grid">
            <div className="info-item">
              <span className="label">Start Time:</span>
              <span className="value">{formatDateTime(alert.start_time)}</span>
            </div>
            <div className="info-item">
              <span className="label">End Time:</span>
              <span className="value">{formatDateTime(alert.end_time) || 'Ongoing'}</span>
            </div>
            <div className="info-item">
              <span className="label">Duration:</span>
              <span className="value">{formatDuration(alert.start_time, alert.end_time)}</span>
            </div>
            <div className="info-item">
              <span className="label">Status:</span>
              <span className={`value status ${!alert.end_time ? 'active' : alert.acknowledged ? 'acknowledged' : 'unacknowledged'}`}>
                {!alert.end_time ? 'Active' : alert.acknowledged ? 'Acknowledged' : 'Unacknowledged'}
              </span>
            </div>
          </div>

          <div className="alert-values">
            <div className="alert-value-box">
              <h3>SpO₂ Range</h3>
              <div className="range-value">
                {alert.spo2_min !== null && alert.spo2_max !== null
                  ? `${alert.spo2_min} - ${alert.spo2_max}%`
                  : 'N/A'}
              </div>
              {alert.spo2_alarm_triggered && <div className="alarm-indicator">Alarm Triggered</div>}
            </div>
            
            <div className="alert-value-box">
              <h3>Heart Rate Range</h3>
              <div className="range-value">
                {alert.bpm_min !== null && alert.bpm_max !== null
                  ? `${alert.bpm_min} - ${alert.bpm_max} BPM`
                  : 'N/A'}
              </div>
              {alert.hr_alarm_triggered && <div className="alarm-indicator">Alarm Triggered</div>}
            </div>
          </div>

          <div className="event-charts">
            <h3>Event Data</h3>
            {loading ? (
              <div className="loading">Loading event data...</div>
            ) : error ? (
              <div className="error-message">{error}</div>
            ) : !eventData || eventData.length === 0 ? (
              <div className="no-data">No data available for this event</div>
            ) : (
              <div className="charts-container">
                <div className="chart-wrapper">
                  <h4>SpO₂ During Event</h4>
                  <div className="chart">
                    {loading ? (
                      <div className="loading">Loading data...</div>
                    ) : error ? (
                      <div className="error-message">{error}</div>
                    ) : !eventData || eventData.length === 0 ? (
                      <div className="no-data">No data available</div>
                    ) : (
                      <SimpleEventChart
                        title="Blood Oxygen"
                        color="#48BB78"
                        unit="SpO₂ (%)"
                        data={spo2ChartData}
                      />
                    )}
                  </div>
                </div>
                
                <div className="chart-wrapper">
                  <h4>Heart Rate During Event</h4>
                  <div className="chart">
                    {loading ? (
                      <div className="loading">Loading data...</div>
                    ) : error ? (
                      <div className="error-message">{error}</div>
                    ) : !eventData || eventData.length === 0 ? (
                      <div className="no-data">No data available</div>
                    ) : (
                      <SimpleEventChart
                        title="Pulse Rate"
                        color="#F56565"
                        unit="BPM"
                        data={bpmChartData}
                      />
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="modal-footer">
          {!alert.acknowledged && (
            <button 
              onClick={() => onAcknowledge(alert.id)} 
              className="primary-button acknowledge-button"
            >
              Acknowledge
            </button>
          )}
          <button onClick={onClose} className="secondary-button">Close</button>
        </div>
      </div>
    </div>
  );
};

export default AlertDetailModal;