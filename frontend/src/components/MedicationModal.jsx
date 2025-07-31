import React, { useState, useEffect } from 'react';
import ModalBase from './ModalBase';

const MedicationModal = ({ onClose }) => {
  const [tab, setTab] = useState('scheduled');
  const [medications, setMedications] = useState([]);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingMed, setEditingMed] = useState(null);
  
  // Remove endDate from formData
  const [formData, setFormData] = useState({
    name: '',
    concentration: '',
    quantity: '',
    quantityUnit: 'tablets',
    instructions: '',
    startDate: '',
    asNeeded: false,
    notes: ''
  });

  // Load medications from localStorage on component mount
  useEffect(() => {
    const savedMeds = localStorage.getItem('medications');
    if (savedMeds) {
      setMedications(JSON.parse(savedMeds));
    }
  }, []);

  // Save medications to localStorage whenever medications change
  useEffect(() => {
    localStorage.setItem('medications', JSON.stringify(medications));
  }, [medications]);

  const resetForm = () => {
    setFormData({
      name: '',
      concentration: '',
      quantity: '',
      quantityUnit: 'tablets',
      instructions: '',
      startDate: '',
      asNeeded: false,
      notes: ''
    });
    setEditingMed(null);
    setShowAddForm(false);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    
    const newMed = {
      id: editingMed ? editingMed.id : Date.now(),
      ...formData,
      createdAt: editingMed ? editingMed.createdAt : new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      active: true
    };

    if (editingMed) {
      setMedications(prev => prev.map(med => med.id === editingMed.id ? newMed : med));
    } else {
      setMedications(prev => [...prev, newMed]);
    }

    resetForm();
  };

  const handleEdit = (med) => {
    setFormData(med);
    setEditingMed(med);
    setShowAddForm(true);
  };

  const handleDelete = (id) => {
    if (confirm('Are you sure you want to delete this medication?')) {
      setMedications(prev => prev.filter(med => med.id !== id));
    }
  };

  const toggleActive = (id) => {
    setMedications(prev => prev.map(med => 
      med.id === id ? { ...med, active: !med.active } : med
    ));
  };

  const formatSchedule = (med) => {
    if (med.asNeeded) return 'As needed';
    
    if (med.scheduleDays && med.scheduleDays.length > 0) {
      const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
      const selectedDays = med.scheduleDays.map(day => days[day]).join(', ');
      return `${selectedDays} at ${med.scheduleTime}`;
    }
    
    return 'No schedule set';
  };

  const activeMedications = medications.filter(med => med.active);
  const inactiveMedications = medications.filter(med => !med.active);

  const renderMedicationCard = (med) => (
    <div key={med.id} className="medication-card" style={{
      backgroundColor: '#fff',
      borderRadius: '8px',
      padding: '16px',
      marginBottom: '12px',
      boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
      border: `2px solid ${med.active ? '#28a745' : '#6c757d'}`
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ flex: 1 }}>
          <h4 style={{ margin: '0 0 8px 0', color: '#333', fontSize: '18px', fontWeight: '600' }}>
            {med.name}
          </h4>
          {med.concentration && (
            <div style={{ marginBottom: '8px' }}>
              <span style={{ fontWeight: '500', color: '#666' }}>Concentration: </span>
              <span style={{ color: '#333' }}>{med.concentration}</span>
            </div>
          )}
          <div style={{ marginBottom: '8px' }}>
            <span style={{ fontWeight: '500', color: '#666' }}>Quantity: </span>
            <span style={{ color: '#333' }}>{med.quantity} {med.quantityUnit || ''}</span>
          </div>
          {med.notes && (
            <div style={{ marginBottom: '8px' }}>
              <span style={{ fontWeight: '500', color: '#666' }}>Notes: </span>
              <span style={{ color: '#333' }}>{med.notes}</span>
            </div>
          )}
          {(med.startDate) && (
            <div style={{ fontSize: '14px', color: '#666' }}>
              {med.startDate && `Start: ${new Date(med.startDate).toLocaleDateString()}`}
            </div>
          )}
        </div>
        <div style={{ display: 'flex', gap: '8px', marginLeft: '16px' }}>
          <button
            onClick={() => handleEdit(med)}
            style={{
              padding: '6px 12px',
              border: 'none',
              borderRadius: '4px',
              backgroundColor: '#007bff',
              color: '#fff',
              cursor: 'pointer',
              fontSize: '12px'
            }}
          >
            Edit
          </button>
          <button
            onClick={() => toggleActive(med.id)}
            style={{
              padding: '6px 12px',
              border: 'none',
              borderRadius: '4px',
              backgroundColor: med.active ? '#6c757d' : '#28a745',
              color: '#fff',
              cursor: 'pointer',
              fontSize: '12px'
            }}
          >
            {med.active ? 'Pause' : 'Resume'}
          </button>
          <button
            onClick={() => handleDelete(med.id)}
            style={{
              padding: '6px 12px',
              border: 'none',
              borderRadius: '4px',
              backgroundColor: '#dc3545',
              color: '#fff',
              cursor: 'pointer',
              fontSize: '12px'
            }}
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );

  const renderForm = () => (
    <div style={{
      backgroundColor: '#fff',
      borderRadius: '8px',
      padding: '24px',
      boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
    }}>
      <h3 style={{ margin: '0 0 24px 0', color: '#333' }}>
        {editingMed ? 'Edit Medication' : 'Add New Medication'}
      </h3>
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600', color: '#333' }}>
              Medication Name *
            </label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
              style={{
                width: '100%',
                padding: '12px',
                border: '2px solid #ddd',
                borderRadius: '6px',
                fontSize: '14px',
                boxSizing: 'border-box',
                backgroundColor: '#f8f9fa',
                color: '#333'
              }}
              placeholder="Enter medication name"
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600', color: '#333' }}>
              Concentration
            </label>
            <input
              type="text"
              value={formData.concentration}
              onChange={(e) => setFormData(prev => ({ ...prev, concentration: e.target.value }))}
              style={{
                width: '100%',
                padding: '12px',
                border: '2px solid #ddd',
                borderRadius: '6px',
                fontSize: '14px',
                boxSizing: 'border-box',
                backgroundColor: '#f8f9fa',
                color: '#333'
              }}
              placeholder="e.g., 500mg/tablet, 25mg/5ml"
            />
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600', color: '#333' }}>
              Quantity *
            </label>
            <div style={{ display: 'flex', gap: '8px' }}>
              <input
                type="number"
                step="0.001"
                min="0"
                required
                value={formData.quantity}
                onChange={(e) => setFormData(prev => ({ ...prev, quantity: e.target.value }))}
                style={{
                  flex: '2',
                  padding: '12px',
                  border: '2px solid #ddd',
                  borderRadius: '6px',
                  fontSize: '14px',
                  boxSizing: 'border-box',
                  backgroundColor: '#f8f9fa',
                  color: '#333'
                }}
                placeholder="0.000"
              />
              <select
                value={formData.quantityUnit}
                onChange={(e) => setFormData(prev => ({ ...prev, quantityUnit: e.target.value }))}
                style={{
                  flex: '1',
                  padding: '12px',
                  border: '2px solid #ddd',
                  borderRadius: '6px',
                  fontSize: '14px',
                  boxSizing: 'border-box',
                  backgroundColor: '#f8f9fa',
                  color: '#333'
                }}
              >
                <option value="tablets">tablets</option>
                <option value="capsules">capsules</option>
                <option value="pills">pills</option>
                <option value="ml">ml</option>
                <option value="cc">cc</option>
                <option value="bottles">bottles</option>
                <option value="boxes">boxes</option>
                <option value="packets">packets</option>
                <option value="vials">vials</option>
                <option value="tubes">tubes</option>
                <option value="patches">patches</option>
                <option value="inhalers">inhalers</option>
                <option value="syringes">syringes</option>
                <option value="ampules">ampules</option>
                <option value="doses">doses</option>
                <option value="units">units</option>
                <option value="grams">grams</option>
                <option value="ounces">ounces</option>
              </select>
            </div>
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600', color: '#333' }}>
              Start Date
            </label>
            <input
              type="date"
              value={formData.startDate}
              onChange={(e) => setFormData(prev => ({ ...prev, startDate: e.target.value }))}
              style={{
                width: '100%',
                padding: '12px',
                border: '2px solid #ddd',
                borderRadius: '6px',
                fontSize: '14px',
                boxSizing: 'border-box',
                backgroundColor: '#f8f9fa',
                color: '#333'
              }}
            />
          </div>
        </div>

        <div>
          <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600', color: '#333' }}>
            Notes
          </label>
          <textarea
            value={formData.notes}
            onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
            style={{
              width: '100%',
              padding: '12px',
              border: '2px solid #ddd',
              borderRadius: '6px',
              fontSize: '14px',
              boxSizing: 'border-box',
              backgroundColor: '#f8f9fa',
              color: '#333',
              minHeight: '60px',
              resize: 'vertical'
            }}
            placeholder="Additional notes or instructions"
          />
        </div>

        <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end', marginTop: '16px' }}>
          <button
            type="button"
            onClick={resetForm}
            style={{
              padding: '12px 24px',
              border: '2px solid #6c757d',
              borderRadius: '6px',
              backgroundColor: '#fff',
              color: '#6c757d',
              cursor: 'pointer',
              fontWeight: '500',
              fontSize: '14px'
            }}
          >
            Cancel
          </button>
          <button
            type="submit"
            style={{
              padding: '12px 24px',
              border: 'none',
              borderRadius: '6px',
              backgroundColor: '#007bff',
              color: '#fff',
              cursor: 'pointer',
              fontWeight: '500',
              fontSize: '14px'
            }}
          >
            {editingMed ? 'Update Medication' : 'Add Medication'}
          </button>
        </div>
      </form>
    </div>
  );

  return (
    <ModalBase isOpen={true} onClose={onClose} title="Medication Tracker">
      <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        <div style={{ 
          display: 'flex', 
          gap: '10px', 
          marginBottom: '20px',
          borderBottom: '1px solid #e9ecef',
          paddingBottom: '10px'
        }}>
          <button
            onClick={() => setTab('scheduled')}
            style={{
              padding: '10px 20px',
              border: 'none',
              borderRadius: '6px',
              backgroundColor: tab === 'scheduled' ? '#007bff' : '#f8f9fa',
              color: tab === 'scheduled' ? '#fff' : '#333',
              cursor: 'pointer',
              fontWeight: '500',
              fontSize: '14px'
            }}
          >
            Scheduled
          </button>
          <button
            onClick={() => setTab('active')}
            style={{
              padding: '10px 20px',
              border: 'none',
              borderRadius: '6px',
              backgroundColor: tab === 'active' ? '#007bff' : '#f8f9fa',
              color: tab === 'active' ? '#fff' : '#333',
              cursor: 'pointer',
              fontWeight: '500',
              fontSize: '14px'
            }}
          >
            Active ({activeMedications.length})
          </button>
          <button
            onClick={() => setTab('inactive')}
            style={{
              padding: '10px 20px',
              border: 'none',
              borderRadius: '6px',
              backgroundColor: tab === 'inactive' ? '#007bff' : '#f8f9fa',
              color: tab === 'inactive' ? '#fff' : '#333',
              cursor: 'pointer',
              fontWeight: '500',
              fontSize: '14px'
            }}
          >
            Inactive ({inactiveMedications.length})
          </button>
          <button
            onClick={() => setShowAddForm(true)}
            style={{
              padding: '10px 20px',
              border: 'none',
              borderRadius: '6px',
              backgroundColor: showAddForm ? '#28a745' : '#007bff',
              color: '#fff',
              cursor: 'pointer',
              fontWeight: '500',
              fontSize: '14px',
              marginLeft: 'auto'
            }}
          >
            {showAddForm ? 'Cancel' : 'Add Medication'}
          </button>
        </div>

        <div style={{ flex: 1, overflow: 'auto' }}>
          {showAddForm ? (
            renderForm()
          ) : (
            <div>
              {tab === 'scheduled' ? (
                <div style={{ textAlign: 'center', color: '#888', padding: '40px' }}>
                  <p>Scheduled medications will be managed here.</p>
                </div>
              ) : tab === 'active' ? (
                activeMedications.length === 0 ? (
                  <div style={{
                    textAlign: 'center',
                    padding: '40px',
                    color: '#666',
                    backgroundColor: '#f8f9fa',
                    borderRadius: '8px'
                  }}>
                    <p>No active medications found.</p>
                    <button
                      onClick={() => setShowAddForm(true)}
                      style={{
                        padding: '10px 20px',
                        border: 'none',
                        borderRadius: '6px',
                        backgroundColor: '#007bff',
                        color: '#fff',
                        cursor: 'pointer',
                        fontWeight: '500',
                        fontSize: '14px',
                        marginTop: '10px'
                      }}
                    >
                      Add your first medication
                    </button>
                  </div>
                ) : (
                  activeMedications.map(renderMedicationCard)
                )
              ) : (
                inactiveMedications.length === 0 ? (
                  <div style={{
                    textAlign: 'center',
                    padding: '40px',
                    color: '#666',
                    backgroundColor: '#f8f9fa',
                    borderRadius: '8px'
                  }}>
                    <p>No inactive medications found.</p>
                  </div>
                ) : (
                  inactiveMedications.map(renderMedicationCard)
                )
              )}
            </div>
          )}
        </div>
      </div>
    </ModalBase>
  );
};

export default MedicationModal;
