import React from 'react';

const MedicationListView = ({ 
  medications, 
  setShowAddForm, 
  handleEdit, 
  toggleActive, 
  handleDelete, 
  setShowScheduleFor,
  type = 'active' // 'active' or 'inactive'
}) => {
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
          {/* Schedule button with indicator */}
          <button
            onClick={() => setShowScheduleFor(med.id)}
            style={{
              padding: '6px 12px',
              border: 'none',
              borderRadius: '4px',
              backgroundColor: med.schedules && med.schedules.length > 0 ? '#ffc107' : '#17a2b8',
              color: '#fff',
              cursor: 'pointer',
              fontSize: '12px',
              position: 'relative'
            }}
          >
            Schedule
            {med.schedules && med.schedules.length > 0 && (
              <span style={{
                display: 'inline-block',
                marginLeft: 6,
                background: '#28a745',
                color: '#fff',
                borderRadius: '50%',
                width: 16,
                height: 16,
                fontSize: 11,
                lineHeight: '16px',
                textAlign: 'center',
                fontWeight: 700
              }}>{med.schedules.length}</span>
            )}
          </button>
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

  if (medications.length === 0) {
    return (
      <div style={{
        textAlign: 'center',
        padding: '40px',
        color: '#666',
        backgroundColor: '#f8f9fa',
        borderRadius: '8px'
      }}>
        <p>No {type} medications found.</p>
        {type === 'active' && (
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
        )}
      </div>
    );
  }

  return (
    <div>
      {medications.map(renderMedicationCard)}
    </div>
  );
};

export default MedicationListView;
