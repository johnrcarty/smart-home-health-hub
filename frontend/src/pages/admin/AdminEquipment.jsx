import React, { useState, useEffect } from 'react';
import config from '../../config';

const AdminEquipment = () => {
  const [equipment, setEquipment] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [selectedEquipment, setSelectedEquipment] = useState(null);
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [equipmentHistory, setEquipmentHistory] = useState([]);
  
  const [newEquipment, setNewEquipment] = useState({
    name: '',
    quantity: 1,
    scheduled_replacement: true,
    last_changed: new Date().toISOString().split('T')[0],
    useful_days: 30
  });

  useEffect(() => {
    fetchEquipment();
  }, []);

  const fetchEquipment = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${config.apiUrl}/api/equipment`);
      const data = await response.json();
      setEquipment(data);
    } catch (error) {
      console.error('Error fetching equipment:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddEquipment = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch(`${config.apiUrl}/api/equipment`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newEquipment),
      });

      if (response.ok) {
        setShowAddForm(false);
        setNewEquipment({
          name: '',
          quantity: 1,
          scheduled_replacement: true,
          last_changed: new Date().toISOString().split('T')[0],
          useful_days: 30
        });
        fetchEquipment();
      } else {
        console.error('Failed to add equipment');
      }
    } catch (error) {
      console.error('Error adding equipment:', error);
    }
  };

  const handleReceiveEquipment = async (equipmentId) => {
    const amount = prompt('How many items did you receive?', '1');
    if (amount && !isNaN(amount) && parseInt(amount) > 0) {
      try {
        const response = await fetch(`${config.apiUrl}/api/equipment/${equipmentId}/receive`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ amount: parseInt(amount) }),
        });

        if (response.ok) {
          fetchEquipment();
        } else {
          console.error('Failed to receive equipment');
        }
      } catch (error) {
        console.error('Error receiving equipment:', error);
      }
    }
  };

  const handleOpenEquipment = async (equipmentId) => {
    const amount = prompt('How many items did you open/use?', '1');
    if (amount && !isNaN(amount) && parseInt(amount) > 0) {
      try {
        const response = await fetch(`${config.apiUrl}/api/equipment/${equipmentId}/open`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ amount: parseInt(amount) }),
        });

        if (response.ok) {
          fetchEquipment();
        } else {
          console.error('Failed to open equipment');
        }
      } catch (error) {
        console.error('Error opening equipment:', error);
      }
    }
  };

  const handleChangeEquipment = async (equipmentId) => {
    const changedAt = prompt('When was this equipment changed? (YYYY-MM-DD)', new Date().toISOString().split('T')[0]);
    if (changedAt) {
      try {
        const response = await fetch(`${config.apiUrl}/api/equipment/${equipmentId}/change`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ changed_at: changedAt }),
        });

        if (response.ok) {
          fetchEquipment();
        } else {
          console.error('Failed to log equipment change');
        }
      } catch (error) {
        console.error('Error logging equipment change:', error);
      }
    }
  };

  const handleViewHistory = async (equipmentId) => {
    try {
      const response = await fetch(`${config.apiUrl}/api/equipment/${equipmentId}/history`);
      const data = await response.json();
      setEquipmentHistory(data);
      setSelectedEquipment(equipment.find(eq => eq.id === equipmentId));
      setShowHistoryModal(true);
    } catch (error) {
      console.error('Error fetching equipment history:', error);
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString();
  };

  const calculateDaysUntilDue = (lastChanged, usefulDays) => {
    if (!lastChanged || !usefulDays) return null;
    const lastChangedDate = new Date(lastChanged);
    const dueDate = new Date(lastChangedDate.getTime() + (usefulDays * 24 * 60 * 60 * 1000));
    const today = new Date();
    const diffTime = dueDate - today;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  };

  const getStatusColor = (daysUntilDue) => {
    if (daysUntilDue === null) return 'status-inactive';
    if (daysUntilDue <= 0) return 'status-overdue';
    if (daysUntilDue <= 3) return 'status-due';
    return 'status-active';
  };

  const getStatusText = (daysUntilDue) => {
    if (daysUntilDue === null) return 'No Schedule';
    if (daysUntilDue <= 0) return `Overdue by ${Math.abs(daysUntilDue)} days`;
    if (daysUntilDue <= 3) return `Due in ${daysUntilDue} days`;
    return `${daysUntilDue} days left`;
  };

  if (loading) {
    return <div className="admin-page">
      <div className="loading">Loading equipment...</div>
    </div>;
  }

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <h1 className="admin-page-title">Equipment Management</h1>
        <p className="admin-page-description">
          Manage medical equipment inventory and replacement schedules
        </p>
      </div>

      <div className="admin-section">
        <div className="admin-section-header">
          <h2 className="admin-section-title">Equipment Inventory</h2>
          <button 
            className="btn btn-success"
            onClick={() => setShowAddForm(true)}
          >
            + Add Equipment
          </button>
        </div>

        <div className="admin-section-content">
          {showAddForm && (
            <div className="admin-card" style={{ marginBottom: '2rem', background: '#f8f9fa' }}>
              <h3 className="admin-card-title">Add New Equipment</h3>
              <form onSubmit={handleAddEquipment}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
                  <div>
                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Equipment Name *</label>
                    <input
                      type="text"
                      required
                      value={newEquipment.name}
                      onChange={(e) => setNewEquipment({ ...newEquipment, name: e.target.value })}
                      style={{ width: '100%', padding: '0.5rem', border: '1px solid #ddd', borderRadius: '4px' }}
                      placeholder="e.g., Pulse Oximeter Sensors"
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Initial Quantity *</label>
                    <input
                      type="number"
                      required
                      min="0"
                      value={newEquipment.quantity}
                      onChange={(e) => setNewEquipment({ ...newEquipment, quantity: parseInt(e.target.value) })}
                      style={{ width: '100%', padding: '0.5rem', border: '1px solid #ddd', borderRadius: '4px' }}
                    />
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <input
                      type="checkbox"
                      id="scheduled_replacement"
                      checked={newEquipment.scheduled_replacement}
                      onChange={(e) => setNewEquipment({ ...newEquipment, scheduled_replacement: e.target.checked })}
                    />
                    <label htmlFor="scheduled_replacement" style={{ fontWeight: '600' }}>
                      Scheduled Replacement
                    </label>
                  </div>
                </div>

                {newEquipment.scheduled_replacement && (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
                    <div>
                      <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Last Changed Date *</label>
                      <input
                        type="date"
                        required
                        value={newEquipment.last_changed}
                        onChange={(e) => setNewEquipment({ ...newEquipment, last_changed: e.target.value })}
                        style={{ width: '100%', padding: '0.5rem', border: '1px solid #ddd', borderRadius: '4px' }}
                      />
                    </div>
                    <div>
                      <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Useful Days *</label>
                      <input
                        type="number"
                        required
                        min="1"
                        value={newEquipment.useful_days}
                        onChange={(e) => setNewEquipment({ ...newEquipment, useful_days: parseInt(e.target.value) })}
                        style={{ width: '100%', padding: '0.5rem', border: '1px solid #ddd', borderRadius: '4px' }}
                        placeholder="Days until replacement needed"
                      />
                    </div>
                  </div>
                )}

                <div className="admin-actions">
                  <button type="submit" className="btn btn-success">
                    Add Equipment
                  </button>
                  <button 
                    type="button" 
                    className="btn btn-secondary"
                    onClick={() => setShowAddForm(false)}
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          )}

          <table className="admin-table">
            <thead>
              <tr>
                <th>Equipment Name</th>
                <th>Quantity</th>
                <th>Last Changed</th>
                <th>Useful Days</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {equipment.map((item) => {
                const daysUntilDue = calculateDaysUntilDue(item.last_changed, item.useful_days);
                return (
                  <tr key={item.id}>
                    <td style={{ fontWeight: '600' }}>{item.name}</td>
                    <td>{item.quantity}</td>
                    <td>
                      {item.last_changed ? formatDate(item.last_changed) : 'Not set'}
                    </td>
                    <td>{item.useful_days || 'N/A'} days</td>
                    <td>
                      <span className={`status-badge ${getStatusColor(daysUntilDue)}`}>
                        {getStatusText(daysUntilDue)}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                        <button 
                          className="btn btn-success"
                          style={{ fontSize: '0.75rem', padding: '0.25rem 0.5rem' }}
                          onClick={() => handleReceiveEquipment(item.id)}
                          title="Receive new stock"
                        >
                          + Receive
                        </button>
                        <button 
                          className="btn btn-warning"
                          style={{ fontSize: '0.75rem', padding: '0.25rem 0.5rem' }}
                          onClick={() => handleOpenEquipment(item.id)}
                          title="Use/Open equipment"
                        >
                          - Use
                        </button>
                        {item.scheduled_replacement && (
                          <button 
                            className="btn btn-primary"
                            style={{ fontSize: '0.75rem', padding: '0.25rem 0.5rem' }}
                            onClick={() => handleChangeEquipment(item.id)}
                            title="Log equipment change"
                          >
                            Change
                          </button>
                        )}
                        <button 
                          className="btn btn-secondary"
                          style={{ fontSize: '0.75rem', padding: '0.25rem 0.5rem' }}
                          onClick={() => handleViewHistory(item.id)}
                          title="View history"
                        >
                          History
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          {equipment.length === 0 && (
            <div style={{ textAlign: 'center', padding: '2rem', color: '#666' }}>
              No equipment found. Add some equipment to get started.
            </div>
          )}
        </div>
      </div>

      {/* History Modal */}
      {showHistoryModal && (
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
            maxWidth: '600px',
            width: '90%',
            maxHeight: '80vh',
            overflow: 'auto'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <h3 style={{ margin: 0 }}>
                Equipment History: {selectedEquipment?.name}
              </h3>
              <button 
                className="btn btn-secondary"
                onClick={() => setShowHistoryModal(false)}
              >
                Close
              </button>
            </div>

            {equipmentHistory.length > 0 ? (
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Action</th>
                    <th>Quantity Change</th>
                  </tr>
                </thead>
                <tbody>
                  {equipmentHistory.map((entry, index) => (
                    <tr key={index}>
                      <td>{formatDate(entry.date)}</td>
                      <td>{entry.action}</td>
                      <td>{entry.quantity_change}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p style={{ textAlign: 'center', color: '#666' }}>
                No history available for this equipment.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminEquipment;
