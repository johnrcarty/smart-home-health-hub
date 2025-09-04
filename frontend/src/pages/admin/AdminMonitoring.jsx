import React, { useState, useEffect } from 'react';
import config from '../../config';

const AdminMonitoring = () => {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('unacknowledged'); // 'unacknowledged', 'all', 'history'
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [showAlertModal, setShowAlertModal] = useState(false);
  const [availableDates, setAvailableDates] = useState([]);
  const [selectedDate, setSelectedDate] = useState('');
  const [dayAnalysis, setDayAnalysis] = useState(null);

  useEffect(() => {
    fetchAlerts();
    fetchAvailableDates();
  }, [activeTab]);

  const fetchAlerts = async () => {
    setLoading(true);
    try {
      const includeAcknowledged = activeTab === 'all' || activeTab === 'history';
      const response = await fetch(
        `${config.apiUrl}/api/monitoring/alerts?include_acknowledged=${includeAcknowledged}&limit=100&detailed=true`
      );
      const data = await response.json();
      setAlerts(data);
    } catch (error) {
      console.error('Error fetching alerts:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchAvailableDates = async () => {
    try {
      const response = await fetch(`${config.apiUrl}/api/monitoring/history/dates`);
      const data = await response.json();
      setAvailableDates(data);
    } catch (error) {
      console.error('Error fetching available dates:', error);
    }
  };

  const fetchDayAnalysis = async (date) => {
    try {
      const response = await fetch(`${config.apiUrl}/api/monitoring/history/analyze/${date}`);
      const data = await response.json();
      setDayAnalysis(data);
    } catch (error) {
      console.error('Error fetching day analysis:', error);
    }
  };

  const handleAcknowledgeAlert = async (alertId) => {
    const oxygenUsed = prompt('Oxygen used during this event (L/min):', '0');
    const oxygenHighest = prompt('Highest oxygen level used:', '');
    const oxygenUnit = prompt('Unit (L/min, mL/min, etc.):', 'L/min');

    if (oxygenUsed !== null) {
      try {
        const response = await fetch(`${config.apiUrl}/api/monitoring/alerts/${alertId}/acknowledge`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            oxygen_used: parseFloat(oxygenUsed) || 0,
            oxygen_highest: oxygenHighest || null,
            oxygen_unit: oxygenUnit || 'L/min'
          }),
        });

        if (response.ok) {
          fetchAlerts();
        } else {
          console.error('Failed to acknowledge alert');
        }
      } catch (error) {
        console.error('Error acknowledging alert:', error);
      }
    }
  };

  const handleViewAlertDetails = async (alertId) => {
    try {
      const response = await fetch(`${config.apiUrl}/api/monitoring/alerts/${alertId}/data`);
      const data = await response.json();
      setSelectedAlert(data);
      setShowAlertModal(true);
    } catch (error) {
      console.error('Error fetching alert details:', error);
    }
  };

  const formatDateTime = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  const formatDuration = (seconds) => {
    if (!seconds) return 'N/A';
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  };

  const getAlertSeverity = (alertType, value) => {
    // This could be enhanced based on your specific alert thresholds
    if (alertType === 'spo2' && value < 85) return 'Critical';
    if (alertType === 'spo2' && value < 90) return 'High';
    if (alertType === 'bpm' && (value < 50 || value > 120)) return 'High';
    return 'Medium';
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'Critical': return '#dc3545';
      case 'High': return '#fd7e14';
      case 'Medium': return '#ffc107';
      default: return '#6c757d';
    }
  };

  if (loading) {
    return <div className="admin-page">
      <div className="loading">Loading monitoring data...</div>
    </div>;
  }

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <h1 className="admin-page-title">Monitoring & Alerts</h1>
        <p className="admin-page-description">
          View and manage patient monitoring alerts and historical data
        </p>
      </div>

      <div className="admin-section">
        <div className="admin-section-header">
          <h2 className="admin-section-title">Patient Alerts</h2>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button 
              className={`btn ${activeTab === 'unacknowledged' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('unacknowledged')}
            >
              Unacknowledged
            </button>
            <button 
              className={`btn ${activeTab === 'all' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('all')}
            >
              All Alerts
            </button>
            <button 
              className={`btn ${activeTab === 'history' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('history')}
            >
              Historical Analysis
            </button>
          </div>
        </div>

        <div className="admin-section-content">
          {activeTab === 'history' ? (
            <div>
              <div className="admin-card" style={{ marginBottom: '2rem' }}>
                <h3 className="admin-card-title">Historical Data Analysis</h3>
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'end', marginBottom: '1rem' }}>
                  <div>
                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>
                      Select Date
                    </label>
                    <select
                      value={selectedDate}
                      onChange={(e) => setSelectedDate(e.target.value)}
                      style={{ padding: '0.5rem', border: '1px solid #ddd', borderRadius: '4px' }}
                    >
                      <option value="">Choose a date...</option>
                      {availableDates.map((date) => (
                        <option key={date} value={date}>
                          {new Date(date).toLocaleDateString()}
                        </option>
                      ))}
                    </select>
                  </div>
                  <button 
                    className="btn btn-primary"
                    onClick={() => selectedDate && fetchDayAnalysis(selectedDate)}
                    disabled={!selectedDate}
                  >
                    Analyze Day
                  </button>
                </div>

                {dayAnalysis && (
                  <div style={{ marginTop: '1.5rem' }}>
                    <h4>Analysis for {new Date(selectedDate).toLocaleDateString()}</h4>
                    <div className="admin-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
                      <div className="admin-card">
                        <h5>SpO₂ Statistics</h5>
                        <p><strong>Average:</strong> {dayAnalysis.spo2_avg?.toFixed(1)}%</p>
                        <p><strong>Minimum:</strong> {dayAnalysis.spo2_min}%</p>
                        <p><strong>Maximum:</strong> {dayAnalysis.spo2_max}%</p>
                        <p><strong>Below 90%:</strong> {dayAnalysis.spo2_below_90_count} readings</p>
                      </div>
                      
                      <div className="admin-card">
                        <h5>Heart Rate Statistics</h5>
                        <p><strong>Average:</strong> {dayAnalysis.bpm_avg?.toFixed(0)} BPM</p>
                        <p><strong>Minimum:</strong> {dayAnalysis.bpm_min} BPM</p>
                        <p><strong>Maximum:</strong> {dayAnalysis.bpm_max} BPM</p>
                      </div>
                      
                      <div className="admin-card">
                        <h5>Alert Summary</h5>
                        <p><strong>Total Alerts:</strong> {dayAnalysis.total_alerts}</p>
                        <p><strong>Alert Duration:</strong> {formatDuration(dayAnalysis.total_alert_duration)}</p>
                        <p><strong>Data Points:</strong> {dayAnalysis.total_readings}</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Date/Time</th>
                  <th>Type</th>
                  <th>Value</th>
                  <th>Duration</th>
                  <th>Severity</th>
                  <th>Oxygen Used</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {alerts.map((alert) => {
                  const severity = getAlertSeverity(alert.alert_type, alert.trigger_value);
                  return (
                    <tr key={alert.id}>
                      <td>{formatDateTime(alert.alert_time)}</td>
                      <td style={{ textTransform: 'uppercase', fontWeight: '600' }}>
                        {alert.alert_type}
                      </td>
                      <td>
                        {alert.trigger_value}
                        {alert.alert_type === 'spo2' ? '%' : 
                         alert.alert_type === 'bpm' ? ' BPM' : ''}
                      </td>
                      <td>{formatDuration(alert.duration)}</td>
                      <td>
                        <span style={{ 
                          color: getSeverityColor(severity), 
                          fontWeight: '600' 
                        }}>
                          {severity}
                        </span>
                      </td>
                      <td>
                        {alert.oxygen_used ? 
                          `${alert.oxygen_used} ${alert.oxygen_unit || 'L/min'}` : 
                          'Not recorded'
                        }
                      </td>
                      <td>
                        <span className={`status-badge ${alert.acknowledged ? 'status-active' : 'status-due'}`}>
                          {alert.acknowledged ? 'Acknowledged' : 'Pending'}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                          <button 
                            className="btn btn-secondary"
                            style={{ fontSize: '0.75rem', padding: '0.25rem 0.5rem' }}
                            onClick={() => handleViewAlertDetails(alert.id)}
                          >
                            Details
                          </button>
                          {!alert.acknowledged && (
                            <button 
                              className="btn btn-success"
                              style={{ fontSize: '0.75rem', padding: '0.25rem 0.5rem' }}
                              onClick={() => handleAcknowledgeAlert(alert.id)}
                            >
                              Acknowledge
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}

          {alerts.length === 0 && activeTab !== 'history' && (
            <div style={{ textAlign: 'center', padding: '2rem', color: '#666' }}>
              {activeTab === 'unacknowledged' ? 
                'No unacknowledged alerts found.' : 
                'No alerts found.'
              }
            </div>
          )}
        </div>
      </div>

      {/* Alert Details Modal */}
      {showAlertModal && selectedAlert && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            backgroundColor: 'white',
            borderRadius: '8px',
            padding: '2rem',
            maxWidth: '800px',
            width: '90%',
            maxHeight: '80vh',
            overflow: 'auto'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <h3 style={{ margin: 0 }}>
                Alert Details
              </h3>
              <button 
                className="btn btn-secondary"
                onClick={() => setShowAlertModal(false)}
              >
                Close
              </button>
            </div>

            <div className="admin-grid">
              <div className="admin-card">
                <h4>Alert Information</h4>
                <p><strong>Type:</strong> {selectedAlert.alert_type?.toUpperCase()}</p>
                <p><strong>Time:</strong> {formatDateTime(selectedAlert.alert_time)}</p>
                <p><strong>Value:</strong> {selectedAlert.trigger_value}</p>
                <p><strong>Duration:</strong> {formatDuration(selectedAlert.duration)}</p>
              </div>

              <div className="admin-card">
                <h4>Response Data</h4>
                <p><strong>Oxygen Used:</strong> {selectedAlert.oxygen_used || 'Not recorded'}</p>
                <p><strong>Highest Oxygen:</strong> {selectedAlert.oxygen_highest || 'Not recorded'}</p>
                <p><strong>Unit:</strong> {selectedAlert.oxygen_unit || 'N/A'}</p>
                <p><strong>Acknowledged:</strong> {selectedAlert.acknowledged ? 'Yes' : 'No'}</p>
              </div>
            </div>

            {selectedAlert.readings && selectedAlert.readings.length > 0 && (
              <div style={{ marginTop: '1.5rem' }}>
                <h4>Related Readings</h4>
                <div style={{ maxHeight: '200px', overflow: 'auto', border: '1px solid #ddd', borderRadius: '4px' }}>
                  <table className="admin-table" style={{ margin: 0 }}>
                    <thead>
                      <tr>
                        <th>Time</th>
                        <th>SpO₂</th>
                        <th>BPM</th>
                        <th>Perfusion</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedAlert.readings.slice(0, 20).map((reading, index) => (
                        <tr key={index}>
                          <td>{new Date(reading.datetime).toLocaleTimeString()}</td>
                          <td>{reading.spo2}%</td>
                          <td>{reading.bpm}</td>
                          <td>{reading.perfusion}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {selectedAlert.readings.length > 20 && (
                  <p style={{ textAlign: 'center', color: '#666', marginTop: '0.5rem' }}>
                    Showing first 20 of {selectedAlert.readings.length} readings
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminMonitoring;
