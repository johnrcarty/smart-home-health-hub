import React, { useState, useEffect } from 'react';
import config from '../../config';

const AdminDashboard = () => {
  const [stats, setStats] = useState({
    totalMedications: 0,
    activeMedications: 0,
    totalCareTask: 0,
    activeCareTask: 0,
    totalEquipment: 0,
    equipmentDue: 0,
    totalAlerts: 0,
    unacknowledgedAlerts: 0
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        // Fetch medication stats
        const [activeMeds, inactiveMeds] = await Promise.all([
          fetch(`${config.apiUrl}/api/medications/active`).then(r => r.json()),
          fetch(`${config.apiUrl}/api/medications/inactive`).then(r => r.json())
        ]);

        // Fetch care task stats
        const [activeTasks, inactiveTasks] = await Promise.all([
          fetch(`${config.apiUrl}/api/care-tasks/active`).then(r => r.json()),
          fetch(`${config.apiUrl}/api/care-tasks/inactive`).then(r => r.json())
        ]);

        // Fetch equipment stats
        const [equipment, equipmentDue] = await Promise.all([
          fetch(`${config.apiUrl}/api/equipment`).then(r => r.json()),
          fetch(`${config.apiUrl}/api/equipment/due/count`).then(r => r.json())
        ]);

        // Fetch alert stats
        const alertsCount = await fetch(`${config.apiUrl}/api/monitoring/alerts/count`).then(r => r.json());

        setStats({
          totalMedications: activeMeds.length + inactiveMeds.length,
          activeMedications: activeMeds.length,
          totalCareTask: activeTasks.length + inactiveTasks.length,
          activeCareTask: activeTasks.length,
          totalEquipment: equipment.length,
          equipmentDue: equipmentDue.count || 0,
          totalAlerts: 0, // We might need to add this endpoint
          unacknowledgedAlerts: alertsCount.count || 0
        });
      } catch (error) {
        console.error('Error fetching stats:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  if (loading) {
    return <div className="admin-page">
      <div className="loading">Loading dashboard statistics...</div>
    </div>;
  }

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <h1 className="admin-page-title">Admin Dashboard</h1>
        <p className="admin-page-description">
          Manage all aspects of the Smart Home Health monitoring system
        </p>
      </div>

      <div className="admin-grid">
        <div className="admin-card">
          <h3 className="admin-card-title">Medications</h3>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#007acc', marginBottom: '1rem' }}>
            {stats.activeMedications} / {stats.totalMedications}
          </div>
          <p style={{ color: '#666', marginBottom: '1rem' }}>
            Active medications out of total registered
          </p>
          <div className="admin-actions">
            <a href="/admin/medications" className="btn btn-primary">
              Manage Medications
            </a>
          </div>
        </div>

        <div className="admin-card">
          <h3 className="admin-card-title">Care Tasks</h3>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#28a745', marginBottom: '1rem' }}>
            {stats.activeCareTask} / {stats.totalCareTask}
          </div>
          <p style={{ color: '#666', marginBottom: '1rem' }}>
            Active care tasks out of total defined
          </p>
          <div className="admin-actions">
            <a href="/admin/care-tasks" className="btn btn-success">
              Manage Care Tasks
            </a>
          </div>
        </div>

        <div className="admin-card">
          <h3 className="admin-card-title">Equipment</h3>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#ffc107', marginBottom: '1rem' }}>
            {stats.equipmentDue} / {stats.totalEquipment}
          </div>
          <p style={{ color: '#666', marginBottom: '1rem' }}>
            Equipment items due for replacement
          </p>
          <div className="admin-actions">
            <a href="/admin/equipment" className="btn btn-warning">
              Manage Equipment
            </a>
          </div>
        </div>

        <div className="admin-card">
          <h3 className="admin-card-title">Monitoring Alerts</h3>
          <div style={{ 
            fontSize: '2rem', 
            fontWeight: 'bold', 
            color: stats.unacknowledgedAlerts > 0 ? '#dc3545' : '#28a745',
            marginBottom: '1rem' 
          }}>
            {stats.unacknowledgedAlerts}
          </div>
          <p style={{ color: '#666', marginBottom: '1rem' }}>
            Unacknowledged monitoring alerts
          </p>
          <div className="admin-actions">
            <a href="/admin/monitoring" className="btn btn-danger">
              View Alerts
            </a>
          </div>
        </div>

        <div className="admin-card">
          <h3 className="admin-card-title">System Settings</h3>
          <p style={{ color: '#666', marginBottom: '1rem' }}>
            Configure MQTT, sensors, alarms, and other system settings
          </p>
          <div className="admin-actions">
            <a href="/admin/settings" className="btn btn-secondary">
              System Settings
            </a>
          </div>
        </div>

        <div className="admin-card">
          <h3 className="admin-card-title">Quick Actions</h3>
          <p style={{ color: '#666', marginBottom: '1rem' }}>
            Common administrative tasks and shortcuts
          </p>
          <div className="admin-actions">
            <button 
              className="btn btn-primary"
              onClick={() => window.location.href = '/'}
            >
              Touch Dashboard
            </button>
            <button 
              className="btn btn-secondary"
              onClick={() => window.open(`${config.apiUrl}/api/status/modules`, '_blank')}
            >
              System Status
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;
