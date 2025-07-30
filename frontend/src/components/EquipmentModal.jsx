import { useState, useEffect } from 'react';
import config from '../config';
import ModalBase from './ModalBase';

export default function EquipmentModal({ isOpen, onClose, noModal, equipmentDueCount }) {
  const [tab, setTab] = useState('list');
  const [equipment, setEquipment] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [selectedEquip, setSelectedEquip] = useState(null);
  const [addForm, setAddForm] = useState({ 
    name: '', 
    quantity: 1, 
    scheduled_replacement: true, 
    last_changed: '', 
    useful_days: '' 
  });
  const [addLoading, setAddLoading] = useState(false);

  useEffect(() => {
    if (isOpen) fetchEquipment();
  }, [isOpen]);

  const fetchEquipment = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${config.apiUrl}/api/equipment`);
      const data = await res.json();
      setEquipment(data);
    } catch (err) {
      setEquipment([]);
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = async (e) => {
    e.preventDefault();
    setAddLoading(true);
    try {
      const payload = {
        name: addForm.name,
        quantity: parseInt(addForm.quantity),
        scheduled_replacement: addForm.scheduled_replacement
      };
      
      if (addForm.scheduled_replacement) {
        payload.last_changed = addForm.last_changed;
        payload.useful_days = parseInt(addForm.useful_days);
      }
      
      await fetch(`${config.apiUrl}/api/equipment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      setAddForm({ 
        name: '', 
        quantity: 1, 
        scheduled_replacement: true, 
        last_changed: '', 
        useful_days: '' 
      });
      fetchEquipment();
      setTab('list');
    } finally {
      setAddLoading(false);
    }
  };

  const handleChangeClick = (equip) => {
    setSelectedEquip(equip);
    setShowConfirm(true);
  };

  const handleConfirmChange = async () => {
    setShowConfirm(false);
    if (!selectedEquip) return;
    await fetch(`${config.apiUrl}/api/equipment/${selectedEquip.id}/change`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ changed_at: new Date().toISOString() })
    });
    setSelectedEquip(null);
    fetchEquipment();
  };

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString();
  };

  const isDue = (item) => {
    if (!item.scheduled_replacement || !item.due_date) return false;
    return new Date(item.due_date) <= new Date();
  };

  const renderContent = () => (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ 
        display: 'flex', 
        gap: '10px', 
        marginBottom: '20px',
        borderBottom: '1px solid #e9ecef',
        paddingBottom: '10px'
      }}>
        <button
          onClick={() => setTab('list')}
          style={{
            padding: '10px 20px',
            border: 'none',
            borderRadius: '6px',
            backgroundColor: tab === 'list' ? '#007bff' : '#f8f9fa',
            color: tab === 'list' ? '#fff' : '#333',
            cursor: 'pointer',
            fontWeight: '500',
            fontSize: '14px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          Equipment List
          {equipmentDueCount > 0 && (
            <span style={{
              backgroundColor: '#dc3545',
              color: '#fff',
              borderRadius: '12px',
              padding: '2px 8px',
              fontSize: '12px',
              fontWeight: 'bold'
            }}>
              {equipmentDueCount}
            </span>
          )}
        </button>
        <button
          onClick={() => setTab('add')}
          style={{
            padding: '10px 20px',
            border: 'none',
            borderRadius: '6px',
            backgroundColor: tab === 'add' ? '#007bff' : '#f8f9fa',
            color: tab === 'add' ? '#fff' : '#333',
            cursor: 'pointer',
            fontWeight: '500',
            fontSize: '14px'
          }}
        >
          Add Equipment
        </button>
      </div>

      <div style={{ flex: 1, overflow: 'hidden' }}>
        {tab === 'add' ? (
          <div style={{
            backgroundColor: '#fff',
            borderRadius: '8px',
            padding: '24px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
          }}>
            <form onSubmit={handleAdd} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div>
                <label style={{ 
                  display: 'block', 
                  marginBottom: '8px', 
                  fontWeight: '600',
                  color: '#333',
                  fontSize: '14px'
                }}>
                  Name *
                </label>
                <input
                  required
                  value={addForm.name}
                  onChange={e => setAddForm(f => ({ ...f, name: e.target.value }))}
                  style={{
                    width: '100%',
                    padding: '12px',
                    border: '2px solid #ddd',
                    borderRadius: '6px',
                    fontSize: '14px',
                    boxSizing: 'border-box',
                    backgroundColor: '#fff',
                    color: '#333',
                    transition: 'border-color 0.2s ease'
                  }}
                  onFocus={(e) => e.target.style.borderColor = '#007bff'}
                  onBlur={(e) => e.target.style.borderColor = '#ddd'}
                  placeholder="Enter equipment name"
                />
              </div>

              <div>
                <label style={{ 
                  display: 'block', 
                  marginBottom: '8px', 
                  fontWeight: '600',
                  color: '#333',
                  fontSize: '14px'
                }}>
                  Quantity *
                </label>
                <input
                  required
                  type="number"
                  min={1}
                  value={addForm.quantity}
                  onChange={e => setAddForm(f => ({ ...f, quantity: e.target.value }))}
                  style={{
                    width: '100%',
                    padding: '12px',
                    border: '2px solid #ddd',
                    borderRadius: '6px',
                    fontSize: '14px',
                    boxSizing: 'border-box',
                    backgroundColor: '#fff',
                    color: '#333',
                    transition: 'border-color 0.2s ease'
                  }}
                  onFocus={(e) => e.target.style.borderColor = '#007bff'}
                  onBlur={(e) => e.target.style.borderColor = '#ddd'}
                  placeholder="Enter quantity"
                />
              </div>

              <div style={{
                padding: '16px',
                backgroundColor: '#f8f9fa',
                borderRadius: '6px',
                border: '1px solid #e9ecef'
              }}>
                <label style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontWeight: '600',
                  color: '#333'
                }}>
                  <input
                    type="checkbox"
                    checked={addForm.scheduled_replacement}
                    onChange={e => setAddForm(f => ({ ...f, scheduled_replacement: e.target.checked }))}
                    style={{ 
                      transform: 'scale(1.3)',
                      accentColor: '#007bff'
                    }}
                  />
                  Has Scheduled Replacement
                  <span style={{
                    fontSize: '12px',
                    fontWeight: 'normal',
                    color: '#666',
                    fontStyle: 'italic'
                  }}>
                    (Check if this equipment needs regular replacement tracking)
                  </span>
                </label>
              </div>

              {addForm.scheduled_replacement && (
                <>
                  <div>
                    <label style={{ 
                      display: 'block', 
                      marginBottom: '8px', 
                      fontWeight: '600',
                      color: '#333',
                      fontSize: '14px'
                    }}>
                      Date Last Changed *
                    </label>
                    <input
                      required={addForm.scheduled_replacement}
                      type="date"
                      value={addForm.last_changed}
                      onChange={e => setAddForm(f => ({ ...f, last_changed: e.target.value }))}
                      style={{
                        width: '100%',
                        padding: '12px',
                        border: '2px solid #ddd',
                        borderRadius: '6px',
                        fontSize: '14px',
                        boxSizing: 'border-box',
                        backgroundColor: '#fff',
                        color: '#333',
                        transition: 'border-color 0.2s ease'
                      }}
                      onFocus={(e) => e.target.style.borderColor = '#007bff'}
                      onBlur={(e) => e.target.style.borderColor = '#ddd'}
                    />
                  </div>

                  <div>
                    <label style={{ 
                      display: 'block', 
                      marginBottom: '8px', 
                      fontWeight: '600',
                      color: '#333',
                      fontSize: '14px'
                    }}>
                      Useful Days *
                    </label>
                    <input
                      required={addForm.scheduled_replacement}
                      type="number"
                      min={1}
                      value={addForm.useful_days}
                      onChange={e => setAddForm(f => ({ ...f, useful_days: e.target.value }))}
                      style={{
                        width: '100%',
                        padding: '12px',
                        border: '2px solid #ddd',
                        borderRadius: '6px',
                        fontSize: '14px',
                        boxSizing: 'border-box',
                        backgroundColor: '#fff',
                        color: '#333',
                        transition: 'border-color 0.2s ease'
                      }}
                      onFocus={(e) => e.target.style.borderColor = '#007bff'}
                      onBlur={(e) => e.target.style.borderColor = '#ddd'}
                      placeholder="Enter number of days"
                    />
                  </div>
                </>
              )}

              <button
                type="submit"
                disabled={addLoading}
                style={{
                  padding: '12px 24px',
                  border: 'none',
                  borderRadius: '6px',
                  backgroundColor: addLoading ? '#6c757d' : '#007bff',
                  color: '#fff',
                  cursor: addLoading ? 'not-allowed' : 'pointer',
                  fontWeight: '600',
                  fontSize: '14px',
                  marginTop: '10px'
                }}
              >
                {addLoading ? 'Adding...' : 'Add Equipment'}
              </button>
            </form>
          </div>
        ) : (
          loading ? (
            <div style={{ 
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              height: '200px',
              color: '#007bff',
              fontSize: '16px'
            }}>
              Loading...
            </div>
          ) : (
            <div style={{
              backgroundColor: '#fff',
              borderRadius: '8px',
              overflow: 'hidden',
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
              height: '100%'
            }}>
              <table style={{ 
                width: '100%', 
                borderCollapse: 'collapse',
                backgroundColor: '#fff'
              }}>
                <thead>
                  <tr style={{ backgroundColor: '#007bff' }}>
                    <th style={{ 
                      padding: '16px', 
                      color: '#fff', 
                      textAlign: 'left',
                      fontWeight: '600',
                      fontSize: '14px'
                    }}>
                      Name
                    </th>
                    <th style={{ 
                      padding: '16px', 
                      color: '#fff', 
                      textAlign: 'left',
                      fontWeight: '600',
                      fontSize: '14px'
                    }}>
                      Quantity
                    </th>
                    <th style={{ 
                      padding: '16px', 
                      color: '#fff', 
                      textAlign: 'left',
                      fontWeight: '600',
                      fontSize: '14px'
                    }}>
                      Last Changed
                    </th>
                    <th style={{ 
                      padding: '16px', 
                      color: '#fff', 
                      textAlign: 'left',
                      fontWeight: '600',
                      fontSize: '14px'
                    }}>
                      Useful Days
                    </th>
                    <th style={{ 
                      padding: '16px', 
                      color: '#fff', 
                      textAlign: 'left',
                      fontWeight: '600',
                      fontSize: '14px'
                    }}>
                      Due Next
                    </th>
                    <th style={{ 
                      padding: '16px', 
                      color: '#fff', 
                      textAlign: 'center',
                      fontWeight: '600',
                      fontSize: '14px'
                    }}>
                      Action
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {equipment.length === 0 ? (
                    <tr>
                      <td colSpan={6} style={{ 
                        textAlign: "center", 
                        padding: '40px',
                        color: '#666',
                        backgroundColor: '#f8f9fa',
                        fontStyle: 'italic'
                      }}>
                        No equipment found
                      </td>
                    </tr>
                  ) : (
                    equipment.map((equip, idx) => (
                      <tr 
                        key={equip.id}
                        style={{ 
                          backgroundColor: idx % 2 === 0 ? '#fff' : '#f8f9fa',
                          borderBottom: '1px solid #e9ecef',
                          ...(isDue(equip) && { backgroundColor: '#fff2cc', borderLeft: '4px solid #ffc107' })
                        }}
                      >
                        <td style={{ 
                          padding: '12px 16px', 
                          color: '#333',
                          fontSize: '14px',
                          fontWeight: '500'
                        }}>
                          {equip.name}
                        </td>
                        <td style={{ 
                          padding: '12px 16px', 
                          color: '#666',
                          fontSize: '14px'
                        }}>
                          {equip.quantity}
                        </td>
                        <td style={{ 
                          padding: '12px 16px', 
                          color: '#666',
                          fontSize: '14px'
                        }}>
                          {equip.scheduled_replacement ? formatDate(equip.last_changed) : '-'}
                        </td>
                        <td style={{ 
                          padding: '12px 16px', 
                          color: '#666',
                          fontSize: '14px'
                        }}>
                          {equip.scheduled_replacement ? equip.useful_days || '-' : '-'}
                        </td>
                        <td style={{ 
                          padding: '12px 16px', 
                          color: isDue(equip) ? '#dc3545' : '#666',
                          fontSize: '14px',
                          fontWeight: isDue(equip) ? '600' : 'normal'
                        }}>
                          {equip.scheduled_replacement ? formatDate(equip.due_date) : '-'}
                        </td>
                        <td style={{ 
                          padding: '12px 16px', 
                          textAlign: 'center'
                        }}>
                          {equip.scheduled_replacement ? (
                            <button
                              onClick={() => handleChangeClick(equip)}
                              style={{
                                padding: '6px 12px',
                                border: 'none',
                                borderRadius: '4px',
                                backgroundColor: '#007bff',
                                color: '#fff',
                                cursor: 'pointer',
                                fontSize: '12px',
                                fontWeight: '500'
                              }}
                            >
                              Change
                            </button>
                          ) : (
                            <span style={{ color: '#6c757d', fontSize: '12px', fontStyle: 'italic' }}>
                              N/A
                            </span>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )
        )}
      </div>

      {showConfirm && (
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
            backgroundColor: '#fff',
            borderRadius: '8px',
            padding: '24px',
            maxWidth: '400px',
            width: '90%',
            boxShadow: '0 4px 16px rgba(0,0,0,0.2)'
          }}>
            <h3 style={{ margin: '0 0 16px 0', color: '#333' }}>Confirm Change</h3>
            <p style={{ margin: '0 0 24px 0', color: '#666' }}>
              Mark <strong>{selectedEquip?.name}</strong> as changed?
            </p>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setShowConfirm(false)}
                style={{
                  padding: '8px 16px',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  backgroundColor: '#fff',
                  color: '#333',
                  cursor: 'pointer',
                  fontSize: '14px'
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmChange}
                style={{
                  padding: '8px 16px',
                  border: 'none',
                  borderRadius: '4px',
                  backgroundColor: '#007bff',
                  color: '#fff',
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontWeight: '500'
                }}
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  // If noModal, render only the inner tracker UI
  if (noModal) {
    return (
      <div className="equipment-tracker-inner" style={{ height: '100%', width: '100%' }}>
        {renderContent()}
      </div>
    );
  }

  return (
    <ModalBase isOpen={isOpen} onClose={onClose} title="Equipment Tracker">
      {renderContent()}
    </ModalBase>
  );
}
