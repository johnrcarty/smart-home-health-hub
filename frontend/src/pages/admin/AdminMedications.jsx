import React, { useState, useEffect } from 'react';
import config from '../../config';

const AdminMedications = () => {
  const [medications, setMedications] = useState([]);
  const [schedules, setSchedules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('active'); // 'active', 'inactive', 'schedules'
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingMedication, setEditingMedication] = useState(null);
  
  const [newMedication, setNewMedication] = useState({
    name: '',
    concentration: '',
    quantity: '',
    quantity_unit: 'mg',
    instructions: '',
    start_date: new Date().toISOString().split('T')[0],
    end_date: '',
    as_needed: false,
    notes: ''
  });

  useEffect(() => {
    fetchData();
  }, [activeTab]);

  const fetchData = async () => {
    setLoading(true);
    try {
      if (activeTab === 'schedules') {
        const response = await fetch(`${config.apiUrl}/api/schedules`);
        const data = await response.json();
        setSchedules(data);
      } else {
        const endpoint = activeTab === 'active' ? '/api/medications/active' : '/api/medications/inactive';
        const response = await fetch(`${config.apiUrl}${endpoint}`);
        const data = await response.json();
        setMedications(data);
      }
    } catch (error) {
      console.error('Error fetching medications:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddMedication = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch(`${config.apiUrl}/api/add/medication`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newMedication),
      });

      if (response.ok) {
        setShowAddForm(false);
        setNewMedication({
          name: '',
          concentration: '',
          quantity: '',
          quantity_unit: 'mg',
          instructions: '',
          start_date: new Date().toISOString().split('T')[0],
          end_date: '',
          as_needed: false,
          notes: ''
        });
        fetchData();
      } else {
        console.error('Failed to add medication');
      }
    } catch (error) {
      console.error('Error adding medication:', error);
    }
  };

  const handleUpdateMedication = async (medicationId, updates) => {
    try {
      const response = await fetch(`${config.apiUrl}/api/medications/${medicationId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updates),
      });

      if (response.ok) {
        fetchData();
        setEditingMedication(null);
      } else {
        console.error('Failed to update medication');
      }
    } catch (error) {
      console.error('Error updating medication:', error);
    }
  };

  const handleToggleActive = async (medicationId) => {
    try {
      const response = await fetch(`${config.apiUrl}/api/medications/${medicationId}/toggle-active`, {
        method: 'POST',
      });

      if (response.ok) {
        fetchData();
      } else {
        console.error('Failed to toggle medication status');
      }
    } catch (error) {
      console.error('Error toggling medication status:', error);
    }
  };

  const handleDeleteMedication = async (medicationId) => {
    if (window.confirm('Are you sure you want to delete this medication?')) {
      try {
        const response = await fetch(`${config.apiUrl}/api/medications/${medicationId}`, {
          method: 'DELETE',
        });

        if (response.ok) {
          fetchData();
        } else {
          console.error('Failed to delete medication');
        }
      } catch (error) {
        console.error('Error deleting medication:', error);
      }
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString();
  };

  if (loading) {
    return <div className="admin-page">
      <div className="loading">Loading medications...</div>
    </div>;
  }

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <h1 className="admin-page-title">Medication Management</h1>
        <p className="admin-page-description">
          Manage medications, schedules, and administration tracking
        </p>
      </div>

      <div className="admin-section">
        <div className="admin-section-header">
          <h2 className="admin-section-title">Medications</h2>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
            <div className="tab-buttons" style={{ display: 'flex', gap: '0.5rem' }}>
              <button 
                className={`btn ${activeTab === 'active' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setActiveTab('active')}
              >
                Active ({medications.length})
              </button>
              <button 
                className={`btn ${activeTab === 'inactive' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setActiveTab('inactive')}
              >
                Inactive
              </button>
              <button 
                className={`btn ${activeTab === 'schedules' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setActiveTab('schedules')}
              >
                Schedules
              </button>
            </div>
            <button 
              className="btn btn-success"
              onClick={() => setShowAddForm(true)}
            >
              + Add Medication
            </button>
          </div>
        </div>

        <div className="admin-section-content">
          {showAddForm && (
            <div className="admin-card" style={{ marginBottom: '2rem', background: '#f8f9fa' }}>
              <h3 className="admin-card-title">Add New Medication</h3>
              <form onSubmit={handleAddMedication}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
                  <div>
                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Name *</label>
                    <input
                      type="text"
                      required
                      value={newMedication.name}
                      onChange={(e) => setNewMedication({ ...newMedication, name: e.target.value })}
                      style={{ width: '100%', padding: '0.5rem', border: '1px solid #ddd', borderRadius: '4px' }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Concentration *</label>
                    <input
                      type="text"
                      required
                      value={newMedication.concentration}
                      onChange={(e) => setNewMedication({ ...newMedication, concentration: e.target.value })}
                      style={{ width: '100%', padding: '0.5rem', border: '1px solid #ddd', borderRadius: '4px' }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Quantity *</label>
                    <input
                      type="number"
                      required
                      step="0.01"
                      value={newMedication.quantity}
                      onChange={(e) => setNewMedication({ ...newMedication, quantity: e.target.value })}
                      style={{ width: '100%', padding: '0.5rem', border: '1px solid #ddd', borderRadius: '4px' }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Unit *</label>
                    <select
                      value={newMedication.quantity_unit}
                      onChange={(e) => setNewMedication({ ...newMedication, quantity_unit: e.target.value })}
                      style={{ width: '100%', padding: '0.5rem', border: '1px solid #ddd', borderRadius: '4px' }}
                    >
                      <option value="mg">mg</option>
                      <option value="ml">ml</option>
                      <option value="tablets">tablets</option>
                      <option value="capsules">capsules</option>
                      <option value="drops">drops</option>
                      <option value="puffs">puffs</option>
                    </select>
                  </div>
                </div>
                
                <div style={{ marginBottom: '1rem' }}>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Instructions *</label>
                  <textarea
                    required
                    value={newMedication.instructions}
                    onChange={(e) => setNewMedication({ ...newMedication, instructions: e.target.value })}
                    style={{ width: '100%', padding: '0.5rem', border: '1px solid #ddd', borderRadius: '4px', minHeight: '80px' }}
                  />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
                  <div>
                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Start Date *</label>
                    <input
                      type="date"
                      required
                      value={newMedication.start_date}
                      onChange={(e) => setNewMedication({ ...newMedication, start_date: e.target.value })}
                      style={{ width: '100%', padding: '0.5rem', border: '1px solid #ddd', borderRadius: '4px' }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>End Date</label>
                    <input
                      type="date"
                      value={newMedication.end_date}
                      onChange={(e) => setNewMedication({ ...newMedication, end_date: e.target.value })}
                      style={{ width: '100%', padding: '0.5rem', border: '1px solid #ddd', borderRadius: '4px' }}
                    />
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <input
                      type="checkbox"
                      id="as_needed"
                      checked={newMedication.as_needed}
                      onChange={(e) => setNewMedication({ ...newMedication, as_needed: e.target.checked })}
                    />
                    <label htmlFor="as_needed" style={{ fontWeight: '600' }}>As Needed (PRN)</label>
                  </div>
                </div>

                <div style={{ marginBottom: '1rem' }}>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Notes</label>
                  <textarea
                    value={newMedication.notes}
                    onChange={(e) => setNewMedication({ ...newMedication, notes: e.target.value })}
                    style={{ width: '100%', padding: '0.5rem', border: '1px solid #ddd', borderRadius: '4px', minHeight: '60px' }}
                  />
                </div>

                <div className="admin-actions">
                  <button type="submit" className="btn btn-success">
                    Add Medication
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

          {activeTab !== 'schedules' ? (
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Concentration</th>
                  <th>Quantity</th>
                  <th>Instructions</th>
                  <th>Start Date</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {medications.map((medication) => (
                  <tr key={medication.id}>
                    <td style={{ fontWeight: '600' }}>{medication.name}</td>
                    <td>{medication.concentration}</td>
                    <td>{medication.quantity} {medication.quantity_unit}</td>
                    <td style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {medication.instructions}
                    </td>
                    <td>{formatDate(medication.start_date)}</td>
                    <td>
                      <span className={`status-badge ${medication.active ? 'status-active' : 'status-inactive'}`}>
                        {medication.active ? 'Active' : 'Inactive'}
                      </span>
                      {medication.as_needed && (
                        <span className="status-badge" style={{ marginLeft: '0.5rem', background: '#e2e3e5', color: '#495057' }}>
                          PRN
                        </span>
                      )}
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                        <button 
                          className="btn btn-primary"
                          style={{ fontSize: '0.75rem', padding: '0.25rem 0.5rem' }}
                          onClick={() => setEditingMedication(medication)}
                        >
                          Edit
                        </button>
                        <button 
                          className={`btn ${medication.active ? 'btn-warning' : 'btn-success'}`}
                          style={{ fontSize: '0.75rem', padding: '0.25rem 0.5rem' }}
                          onClick={() => handleToggleActive(medication.id)}
                        >
                          {medication.active ? 'Deactivate' : 'Activate'}
                        </button>
                        <button 
                          className="btn btn-danger"
                          style={{ fontSize: '0.75rem', padding: '0.25rem 0.5rem' }}
                          onClick={() => handleDeleteMedication(medication.id)}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div>
              <p style={{ color: '#666', textAlign: 'center', padding: '2rem' }}>
                Medication schedules management coming soon...
              </p>
            </div>
          )}

          {medications.length === 0 && activeTab !== 'schedules' && (
            <div style={{ textAlign: 'center', padding: '2rem', color: '#666' }}>
              No {activeTab} medications found.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AdminMedications;
