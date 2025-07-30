import { useState, useEffect } from 'react';
import config from '../config';
import ModalBase from './ModalBase';

export default function EquipmentModal({ isOpen, onClose, noModal, equipmentDueCount }) {
  const [tab, setTab] = useState('list');
  const [equipment, setEquipment] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [selectedEquip, setSelectedEquip] = useState(null);
  const [addForm, setAddForm] = useState({ name: '', last_changed: '', useful_days: '' });
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
      await fetch(`${config.apiUrl}/api/equipment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(addForm)
      });
      setAddForm({ name: '', last_changed: '', useful_days: '' });
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

  // If noModal, render only the inner tracker UI
  if (noModal) {
    return (
      <div className="equipment-tracker-inner" style={{ height: '100%', width: '100%' }}>
        <div className="modal-tabs">
          <button onClick={() => setTab('list')} className={tab === 'list' ? 'active' : ''}>
            Due List
            {equipmentDueCount > 0 && (
              <span className="equipment-badge">{equipmentDueCount}</span>
            )}
          </button>
          <button onClick={() => setTab('add')} className={tab === 'add' ? 'active' : ''}>Add Equipment</button>
        </div>
        <div className="modal-body" style={{ height: 'calc(100% - 40px)' }}>
          {tab === 'add' ? (
            <form onSubmit={handleAdd} className="equipment-form">
              <label>
                Name:
                <input required value={addForm.name} onChange={e => setAddForm(f => ({ ...f, name: e.target.value }))} />
              </label>
              <label>
                Date Last Changed:
                <input required type="date" value={addForm.last_changed} onChange={e => setAddForm(f => ({ ...f, last_changed: e.target.value }))} />
              </label>
              <label>
                Useful Days:
                <input required type="number" min={1} value={addForm.useful_days} onChange={e => setAddForm(f => ({ ...f, useful_days: e.target.value }))} />
              </label>
              <button className="primary-button" type="submit" disabled={addLoading}>{addLoading ? 'Adding...' : 'Add Equipment'}</button>
            </form>
          ) : (
            loading ? <div className="loading">Loading...</div> : (
              <table className="equipment-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: 'left', padding: '8px', fontWeight: 'bold' }}>Name</th>
                    <th style={{ textAlign: 'left', padding: '8px', fontWeight: 'bold' }}>Last Changed</th>
                    <th style={{ textAlign: 'left', padding: '8px', fontWeight: 'bold' }}>Useful Days</th>
                    <th style={{ textAlign: 'left', padding: '8px', fontWeight: 'bold' }}>Due Next</th>
                    <th style={{ textAlign: 'left', padding: '8px', fontWeight: 'bold' }}></th>
                  </tr>
                </thead>
                <tbody>
                  {equipment.length === 0 ? (
                    <tr><td colSpan={5} style={{ padding: '8px' }}>No equipment found.</td></tr>
                  ) : equipment.map(equip => (
                    <tr key={equip.id}>
                      <td style={{ textAlign: 'left', padding: '8px' }}><strong>{equip.name}</strong></td>
                      <td style={{ textAlign: 'left', padding: '8px' }}>{new Date(equip.last_changed).toLocaleDateString()}</td>
                      <td style={{ textAlign: 'left', padding: '8px' }}>{equip.useful_days}</td>
                      <td style={{ textAlign: 'left', padding: '8px' }}>{new Date(equip.due_date).toLocaleDateString()}</td>
                      <td style={{ textAlign: 'left', padding: '8px' }}><button className="primary-button" onClick={() => handleChangeClick(equip)}>Change</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )
          )}
        </div>
        {showConfirm && (
          <div className="confirm-modal">
            <div className="confirm-content">
              <h3>Confirm Change</h3>
              <p>Mark <strong>{selectedEquip?.name}</strong> as changed?</p>
              <button className="primary-button" onClick={handleConfirmChange}>Confirm</button>
              <button className="secondary-button" onClick={() => setShowConfirm(false)}>Cancel</button>
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <ModalBase isOpen={isOpen} onClose={onClose} title="Equipment Tracker">
      <div className="modal-tabs">
        <button onClick={() => setTab('list')} className={tab === 'list' ? 'active' : ''}>
          Due List
          {equipmentDueCount > 0 && (
            <span className="equipment-badge">{equipmentDueCount}</span>
          )}
        </button>
        <button onClick={() => setTab('add')} className={tab === 'add' ? 'active' : ''}>Add Equipment</button>
      </div>
      <div className="modal-body">
        {tab === 'add' ? (
          <form onSubmit={handleAdd} className="equipment-form">
            <label>
              Name:
              <input required value={addForm.name} onChange={e => setAddForm(f => ({ ...f, name: e.target.value }))} />
            </label>
            <label>
              Date Last Changed:
              <input required type="date" value={addForm.last_changed} onChange={e => setAddForm(f => ({ ...f, last_changed: e.target.value }))} />
            </label>
            <label>
              Useful Days:
              <input required type="number" min={1} value={addForm.useful_days} onChange={e => setAddForm(f => ({ ...f, useful_days: e.target.value }))} />
            </label>
            <button className="primary-button" type="submit" disabled={addLoading}>{addLoading ? 'Adding...' : 'Add Equipment'}</button>
          </form>
        ) : (
          loading ? <div className="loading">Loading...</div> : (
            <div className="equipment-list">
              {equipment.length === 0 ? <div>No equipment found.</div> : equipment.map(equip => (
                <div key={equip.id} className="equipment-item">
                  <div><strong>{equip.name}</strong></div>
                  <div>Last Changed: {new Date(equip.last_changed).toLocaleDateString()}</div>
                  <div>Useful Days: {equip.useful_days}</div>
                  <div>Due Next: {new Date(equip.due_date).toLocaleDateString()}</div>
                  <button className="primary-button" onClick={() => handleChangeClick(equip)}>Change</button>
                </div>
              ))}
            </div>
          )
        )}
      </div>
      {showConfirm && (
        <div className="confirm-modal">
          <div className="confirm-content">
            <h3>Confirm Change</h3>
            <p>Mark <strong>{selectedEquip?.name}</strong> as changed?</p>
            <button className="primary-button" onClick={handleConfirmChange}>Confirm</button>
            <button className="secondary-button" onClick={() => setShowConfirm(false)}>Cancel</button>
          </div>
        </div>
      )}
    </ModalBase>
  );
}
