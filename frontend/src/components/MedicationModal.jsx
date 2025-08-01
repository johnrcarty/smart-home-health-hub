import React, { useState, useEffect } from 'react';
import ModalBase from './ModalBase';
import config from '../config';

const MedicationModal = ({ onClose }) => {
  const [tab, setTab] = useState('active');
  const [activeMedications, setActiveMedications] = useState([]);
  const [inactiveMedications, setInactiveMedications] = useState([]);
  const [scheduledMedications, setScheduledMedications] = useState({ scheduled_medications: [] });
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingMed, setEditingMed] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showScheduleFor, setShowScheduleFor] = useState(null); // med id or null
  const [scheduleMode, setScheduleMode] = useState('weekly'); // 'weekly' or 'monthly'
  const [selectedDays, setSelectedDays] = useState([]); // for weekly
  const [selectedDayOfMonth, setSelectedDayOfMonth] = useState(1); // for monthly
  const [time, setTime] = useState('08:00');
  const [doseAmount, setDoseAmount] = useState('1.000');
  const [newCron, setNewCron] = useState(''); // not used directly now

  const daysOfWeek = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

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

  // Load medications from API on component mount
  useEffect(() => {
    fetchMedications();
    if (tab === 'scheduled') {
      fetchScheduledMedications();
    }
  }, [tab]);

  const fetchMedications = async () => {
    setLoading(true);
    try {
      const [activeRes, inactiveRes] = await Promise.all([
        fetch(`${config.apiUrl}/api/medications/active`),
        fetch(`${config.apiUrl}/api/medications/inactive`)
      ]);
      
      if (activeRes.ok && inactiveRes.ok) {
        const active = await activeRes.json();
        const inactive = await inactiveRes.json();
        
        // Fetch schedules for each medication and attach them
        const activeMedsWithSchedules = await Promise.all(
          active.map(async (med) => {
            const schedules = await fetchMedicationSchedules(med.id);
            return { ...med, schedules };
          })
        );
        
        const inactiveMedsWithSchedules = await Promise.all(
          inactive.map(async (med) => {
            const schedules = await fetchMedicationSchedules(med.id);
            return { ...med, schedules };
          })
        );
        
        setActiveMedications(activeMedsWithSchedules);
        setInactiveMedications(inactiveMedsWithSchedules);
      }
    } catch (error) {
      console.error('Error fetching medications:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchScheduledMedications = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${config.apiUrl}/api/schedules/daily`);
      if (response.ok) {
        const data = await response.json();
        setScheduledMedications(data);
      }
    } catch (error) {
      console.error('Error fetching scheduled medications:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchMedicationSchedules = async (medicationId) => {
    try {
      const response = await fetch(`${config.apiUrl}/api/medications/${medicationId}/schedules`);
      if (response.ok) {
        const data = await response.json();
        return data.schedules || [];
      }
      return [];
    } catch (error) {
      console.error('Error fetching schedules for medication:', medicationId, error);
      return [];
    }
  };

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
    // Don't automatically hide the form - let the caller decide
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      if (editingMed) {
        // Update existing medication
        const response = await fetch(`${config.apiUrl}/api/medications/${editingMed.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formData)
        });
        
        if (!response.ok) {
          throw new Error('Failed to update medication');
        }
      } else {
        // Add new medication
        const response = await fetch(`${config.apiUrl}/api/add/medication`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: formData.name,
            concentration: formData.concentration,
            quantity: formData.quantity,
            quantity_unit: formData.quantityUnit,
            instructions: formData.instructions,
            start_date: formData.startDate,
            as_needed: formData.asNeeded,
            notes: formData.notes
          })
        });
        
        if (!response.ok) {
          throw new Error('Failed to add medication');
        }
      }
      
      // Refresh medications list
      await fetchMedications();
      resetForm();
      setShowAddForm(false);
      setShowScheduleFor(null);
    } catch (error) {
      console.error('Error saving medication:', error);
      alert('Error saving medication. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (med) => {
    setFormData({
      name: med.name,
      concentration: med.concentration || '',
      quantity: med.quantity || '',
      quantityUnit: med.quantity_unit || 'tablets',
      instructions: med.instructions || '',
      startDate: med.start_date || '',
      asNeeded: med.as_needed || false,
      notes: med.notes || ''
    });
    setEditingMed(med);
    setShowAddForm(true);
    setShowScheduleFor(null);
  };

  const handleDelete = async (id) => {
    if (confirm('Are you sure you want to delete this medication?')) {
      setLoading(true);
      try {
        const response = await fetch(`${config.apiUrl}/api/medications/${id}`, {
          method: 'DELETE'
        });
        
        if (!response.ok) {
          throw new Error('Failed to delete medication');
        }
        
        await fetchMedications();
      } catch (error) {
        console.error('Error deleting medication:', error);
        alert('Error deleting medication. Please try again.');
      } finally {
        setLoading(false);
      }
    }
  };

  const toggleActive = async (id) => {
    setLoading(true);
    try {
      const response = await fetch(`${config.apiUrl}/api/medications/${id}/toggle-active`, {
        method: 'POST'
      });
      
      if (!response.ok) {
        throw new Error('Failed to toggle medication status');
      }
      
      await fetchMedications();
    } catch (error) {
      console.error('Error toggling medication status:', error);
      alert('Error updating medication status. Please try again.');
    } finally {
      setLoading(false);
    }
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

  const formatTime = (timeString) => {
    try {
      const date = new Date(timeString);
      return date.toLocaleTimeString('en-US', { 
        hour: 'numeric', 
        minute: '2-digit',
        hour12: true 
      });
    } catch (error) {
      return timeString;
    }
  };

  const formatDate = (dateString) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', { 
        weekday: 'short',
        month: 'short', 
        day: 'numeric' 
      });
    } catch (error) {
      return dateString;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed_on_time':
        return { bg: '#e8f5e8', border: '#28a745', text: '#155724' };
      case 'completed_warning':
        return { bg: '#fff3cd', border: '#ffc107', text: '#856404' };
      case 'completed_late':
        return { bg: '#f8d7da', border: '#dc3545', text: '#721c24' };
      case 'due_on_time':
        return { bg: '#d4edda', border: '#28a745', text: '#155724' };
      case 'due_warning':
        return { bg: '#fff3cd', border: '#ffc107', text: '#856404' };
      case 'due_late':
        return { bg: '#f8d7da', border: '#dc3545', text: '#721c24' };
      case 'missed':
        return { bg: '#f8d7da', border: '#dc3545', text: '#721c24' };
      case 'pending':
        return { bg: '#d1ecf1', border: '#17a2b8', text: '#0c5460' };
      default:
        return { bg: '#f8f9fa', border: '#6c757d', text: '#495057' };
    }
  };

  const getStatusText = (item) => {
    const status = item.status;
    const isToday = new Date(item.scheduled_time).toDateString() === new Date().toDateString();
    
    switch (status) {
      case 'completed_on_time':
        return isToday ? 'Completed' : 'Completed on time';
      case 'completed_warning':
        return isToday ? 'Completed (timing off)' : 'Completed with timing variance';
      case 'completed_late':
        return isToday ? 'Completed (very late/early)' : 'Completed with significant timing variance';
      case 'due_on_time':
        return 'Ready to take';
      case 'due_warning':
        return 'Late (1-2 hours)';
      case 'due_late':
        return 'Very late (>2 hours)';
      case 'missed':
        return 'Missed';
      case 'pending':
        return 'Upcoming';
      default:
        return 'Unknown';
    }
  };

  // Helper function to parse cron expression
  const parseCronExpression = (cronExpression) => {
    const parts = cronExpression.split(' ');
    if (parts.length !== 5) return null;
    
    const [minute, hour, dayOfMonth, month, dayOfWeek] = parts;
    
    // Format time
    const timeStr = `${hour.padStart(2, '0')}:${minute.padStart(2, '0')}`;
    
    // Check if it's weekly (dayOfWeek is not *)
    if (dayOfWeek !== '*') {
      const daysMap = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
      const days = dayOfWeek.split(',').map(d => daysMap[parseInt(d)]).join(', ');
      return { type: 'weekly', time: timeStr, days };
    }
    
    // Check if it's monthly (dayOfMonth is not *)
    if (dayOfMonth !== '*') {
      return { type: 'monthly', time: timeStr, dayOfMonth: parseInt(dayOfMonth) };
    }
    
    return null;
  };

  // Helper function to separate schedules by type
  const separateSchedules = (schedules) => {
    const weekly = [];
    const monthly = [];
    
    schedules.forEach((schedule) => {
      const cronExpression = schedule.cron_expression;
      const doseAmount = schedule.dose_amount;
      const isActive = schedule.active;
      const scheduleId = schedule.id;
      
      const parsed = parseCronExpression(cronExpression);
      if (parsed) {
        const scheduleData = {
          ...schedule,
          id: scheduleId,
          cronExpression,
          doseAmount,
          isActive,
          parsed
        };
        
        if (parsed.type === 'weekly') {
          weekly.push(scheduleData);
        } else if (parsed.type === 'monthly') {
          monthly.push(scheduleData);
        }
      }
    });
    
    return { weekly, monthly };
  };

  const handleAddSchedule = async (medId) => {
    let cron = '';
    let description = '';
    let [hour, minute] = time.split(':').map(Number);
    if (scheduleMode === 'weekly') {
      if (selectedDays.length === 0) return;
      const dow = selectedDays.sort().join(',');
      cron = `${minute} ${hour} * * ${dow}`;
      
      // Generate human-readable description for weekly schedule
      const daysMap = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
      const dayNames = selectedDays.map(d => daysMap[parseInt(d)]).join(', ');
      description = `${dayNames} at ${time}`;
    } else {
      cron = `${minute} ${hour} ${selectedDayOfMonth} * *`;
      
      // Generate human-readable description for monthly schedule
      description = `Day ${selectedDayOfMonth} of each month at ${time}`;
    }
    
    try {
      setLoading(true);
      const response = await fetch(`${config.apiUrl}/api/add/schedule/${medId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: 'med',
          cron_expression: cron,
          description: description,
          dose_amount: parseFloat(doseAmount) || 1.0,
          active: true,
          notes: ''
        })
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to add schedule');
      }
      
      // Refresh the medication data to get updated schedules
      await fetchMedications();
      
      // Reset form
      setSelectedDays([]);
      setSelectedDayOfMonth(1);
      setTime('08:00');
      setDoseAmount('1.000');
      setScheduleMode('weekly');
    } catch (error) {
      console.error('Error adding schedule:', error);
      alert(`Error adding schedule: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteSchedule = async (medId, scheduleId) => {
    if (!confirm('Are you sure you want to delete this schedule?')) return;
    
    try {
      setLoading(true);
      const response = await fetch(`${config.apiUrl}/api/schedules/${scheduleId}`, {
        method: 'DELETE'
      });
      
      if (!response.ok) {
        throw new Error('Failed to delete schedule');
      }
      
      // Refresh the medication data to get updated schedules
      await fetchMedications();
    } catch (error) {
      console.error('Error deleting schedule:', error);
      alert('Error deleting schedule. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleSchedule = async (scheduleId) => {
    try {
      setLoading(true);
      const response = await fetch(`${config.apiUrl}/api/schedules/${scheduleId}/toggle-active`, {
        method: 'POST'
      });
      
      if (!response.ok) {
        throw new Error('Failed to toggle schedule');
      }
      
      // Refresh the medication data to get updated schedules
      await fetchMedications();
    } catch (error) {
      console.error('Error toggling schedule:', error);
      alert('Error updating schedule status. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const renderScheduleView = (med) => (
    <div style={{ background: '#fff', borderRadius: 8, padding: 24, boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}>
      <h3 style={{ margin: '0 0 16px 0', color: '#333' }}>Manage Schedules for <span style={{ color: '#007bff' }}>{med.name}</span></h3>
      <div style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
          <button
            type="button"
            onClick={() => setScheduleMode('weekly')}
            style={{ padding: '8px 18px', border: 'none', borderRadius: 6, background: scheduleMode === 'weekly' ? '#007bff' : '#f8f9fa', color: scheduleMode === 'weekly' ? '#fff' : '#333', fontWeight: 500, fontSize: 14 }}
          >Weekly</button>
          <button
            type="button"
            onClick={() => setScheduleMode('monthly')}
            style={{ padding: '8px 18px', border: 'none', borderRadius: 6, background: scheduleMode === 'monthly' ? '#007bff' : '#f8f9fa', color: scheduleMode === 'monthly' ? '#fff' : '#333', fontWeight: 500, fontSize: 14 }}
          >Monthly</button>
        </div>
        {scheduleMode === 'weekly' ? (
          <div style={{ marginBottom: 12 }}>
            <label style={{ fontWeight: 600, color: '#333', marginBottom: 8, display: 'block' }}>Select Days</label>
            <div style={{ display: 'flex', gap: 8 }}>
              {daysOfWeek.map((d, i) => (
                <label key={d} style={{ display: 'flex', alignItems: 'center', gap: 4, background: selectedDays.includes(i.toString()) ? '#007bff' : '#f1f3f4', color: selectedDays.includes(i.toString()) ? '#fff' : '#333', borderRadius: 4, padding: '4px 10px', cursor: 'pointer', fontWeight: 500 }}>
                  <input
                    type="checkbox"
                    checked={selectedDays.includes(i.toString())}
                    onChange={() => {
                      setSelectedDays(prev => prev.includes(i.toString()) ? prev.filter(x => x !== i.toString()) : [...prev, i.toString()]);
                    }}
                    style={{ accentColor: '#007bff' }}
                  />
                  {d}
                </label>
              ))}
            </div>
          </div>
        ) : (
          <div style={{ marginBottom: 12 }}>
            <label style={{ fontWeight: 600, color: '#333', marginBottom: 8, display: 'block' }}>Day of Month</label>
            <select
              value={selectedDayOfMonth}
              onChange={e => setSelectedDayOfMonth(Number(e.target.value))}
              style={{ padding: '8px 16px', border: '2px solid #ddd', borderRadius: 6, fontSize: 14, background: '#f8f9fa', color: '#333' }}
            >
              {[...Array(28)].map((_, i) => (
                <option key={i+1} value={i+1}>{i+1}</option>
              ))}
            </select>
          </div>
        )}
        <div style={{ marginBottom: 12 }}>
          <label style={{ fontWeight: 600, color: '#333', marginBottom: 8, display: 'block' }}>Time</label>
          <input
            type="time"
            value={time}
            onChange={e => setTime(e.target.value)}
            style={{ padding: '8px 12px', border: '2px solid #ddd', borderRadius: 6, fontSize: 14, background: '#f8f9fa', color: '#333', width: 120 }}
          />
        </div>
        <div style={{ marginBottom: 12 }}>
          <label style={{ fontWeight: 600, color: '#333', marginBottom: 8, display: 'block' }}>
            Dose Amount ({med.quantity_unit || 'units'})
          </label>
          <input
            type="number"
            step="0.001"
            min="0"
            value={doseAmount}
            onChange={e => setDoseAmount(e.target.value)}
            style={{ 
              padding: '8px 12px', 
              border: '2px solid #ddd', 
              borderRadius: 6, 
              fontSize: 14, 
              background: '#f8f9fa', 
              color: '#333', 
              width: 120 
            }}
            placeholder="1.000"
          />
        </div>
        <button
          type="button"
          onClick={() => handleAddSchedule(med.id)}
          style={{ padding: '12px 20px', border: 'none', borderRadius: 6, background: '#28a745', color: '#fff', fontWeight: 500, fontSize: 14, marginTop: 8 }}
          disabled={loading || (scheduleMode === 'weekly' ? selectedDays.length === 0 : false)}
        >
          {loading ? 'Adding...' : 'Add Schedule'}
        </button>
      </div>
      <div style={{ marginBottom: 16 }}>
        {med.schedules && med.schedules.length > 0 ? (() => {
          const { weekly, monthly } = separateSchedules(med.schedules);
          
          return (
            <>
              {weekly.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                  <h4 style={{ margin: '0 0 8px 0', color: '#333', fontSize: 16, fontWeight: 600 }}>Weekly Schedules</h4>
                  <table style={{ width: '100%', borderCollapse: 'collapse', backgroundColor: '#fff', borderRadius: 6, overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
                    <thead>
                      <tr style={{ backgroundColor: '#f8f9fa' }}>
                        <th style={{ padding: '8px 12px', textAlign: 'left', fontSize: 13, fontWeight: 600, color: '#333', borderBottom: '1px solid #dee2e6' }}>Amount</th>
                        <th style={{ padding: '8px 12px', textAlign: 'left', fontSize: 13, fontWeight: 600, color: '#333', borderBottom: '1px solid #dee2e6' }}>Time</th>
                        <th style={{ padding: '8px 12px', textAlign: 'left', fontSize: 13, fontWeight: 600, color: '#333', borderBottom: '1px solid #dee2e6' }}>Days</th>
                        <th style={{ padding: '8px 12px', textAlign: 'center', fontSize: 13, fontWeight: 600, color: '#333', borderBottom: '1px solid #dee2e6' }}>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {weekly.map((schedule) => (
                        <tr key={schedule.id} style={{ opacity: schedule.isActive ? 1 : 0.5, borderBottom: '1px solid #f1f3f4' }}>
                          <td style={{ padding: '8px 12px', fontSize: 13, color: '#333' }}>
                            {schedule.doseAmount || '1'} {med.quantity_unit || 'units'}
                          </td>
                          <td style={{ padding: '8px 12px', fontSize: 13, color: '#333' }}>
                            {schedule.parsed.time}
                          </td>
                          <td style={{ padding: '8px 12px', fontSize: 13, color: '#333' }}>
                            {schedule.parsed.days}
                          </td>
                          <td style={{ padding: '8px 12px', textAlign: 'center' }}>
                            <div style={{ display: 'flex', gap: 4, justifyContent: 'center' }}>
                              <button
                                type="button"
                                onClick={() => handleToggleSchedule(schedule.id)}
                                style={{
                                  background: schedule.isActive ? '#ffc107' : '#28a745',
                                  color: '#fff',
                                  border: 'none',
                                  borderRadius: 3,
                                  padding: '4px 6px',
                                  fontSize: 11,
                                  cursor: 'pointer'
                                }}
                                disabled={loading}
                              >
                                {schedule.isActive ? 'Pause' : 'Resume'}
                              </button>
                              <button
                                type="button"
                                onClick={() => handleDeleteSchedule(med.id, schedule.id)}
                                style={{ background: '#dc3545', color: '#fff', border: 'none', borderRadius: 3, padding: '4px 6px', fontSize: 11, cursor: 'pointer' }}
                                disabled={loading}
                              >Delete</button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              
              {monthly.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                  <h4 style={{ margin: '0 0 8px 0', color: '#333', fontSize: 16, fontWeight: 600 }}>Monthly Schedules</h4>
                  <table style={{ width: '100%', borderCollapse: 'collapse', backgroundColor: '#fff', borderRadius: 6, overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
                    <thead>
                      <tr style={{ backgroundColor: '#f8f9fa' }}>
                        <th style={{ padding: '8px 12px', textAlign: 'left', fontSize: 13, fontWeight: 600, color: '#333', borderBottom: '1px solid #dee2e6' }}>Amount</th>
                        <th style={{ padding: '8px 12px', textAlign: 'left', fontSize: 13, fontWeight: 600, color: '#333', borderBottom: '1px solid #dee2e6' }}>Time</th>
                        <th style={{ padding: '8px 12px', textAlign: 'left', fontSize: 13, fontWeight: 600, color: '#333', borderBottom: '1px solid #dee2e6' }}>Day of Month</th>
                        <th style={{ padding: '8px 12px', textAlign: 'center', fontSize: 13, fontWeight: 600, color: '#333', borderBottom: '1px solid #dee2e6' }}>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {monthly.map((schedule) => (
                        <tr key={schedule.id} style={{ opacity: schedule.isActive ? 1 : 0.5, borderBottom: '1px solid #f1f3f4' }}>
                          <td style={{ padding: '8px 12px', fontSize: 13, color: '#333' }}>
                            {schedule.doseAmount || '1'} {med.quantity_unit || 'units'}
                          </td>
                          <td style={{ padding: '8px 12px', fontSize: 13, color: '#333' }}>
                            {schedule.parsed.time}
                          </td>
                          <td style={{ padding: '8px 12px', fontSize: 13, color: '#333' }}>
                            {schedule.parsed.dayOfMonth}
                          </td>
                          <td style={{ padding: '8px 12px', textAlign: 'center' }}>
                            <div style={{ display: 'flex', gap: 4, justifyContent: 'center' }}>
                              <button
                                type="button"
                                onClick={() => handleToggleSchedule(schedule.id)}
                                style={{
                                  background: schedule.isActive ? '#ffc107' : '#28a745',
                                  color: '#fff',
                                  border: 'none',
                                  borderRadius: 3,
                                  padding: '4px 6px',
                                  fontSize: 11,
                                  cursor: 'pointer'
                                }}
                                disabled={loading}
                              >
                                {schedule.isActive ? 'Pause' : 'Resume'}
                              </button>
                              <button
                                type="button"
                                onClick={() => handleDeleteSchedule(med.id, schedule.id)}
                                style={{ background: '#dc3545', color: '#fff', border: 'none', borderRadius: 3, padding: '4px 6px', fontSize: 11, cursor: 'pointer' }}
                                disabled={loading}
                              >Delete</button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          );
        })() : (
          <div style={{ color: '#888', fontStyle: 'italic', textAlign: 'center', padding: 20 }}>No schedules created yet.</div>
        )}
      </div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12 }}>
        <button
          type="button"
          onClick={() => setShowScheduleFor(null)}
          style={{ padding: '10px 24px', border: '2px solid #6c757d', borderRadius: 6, background: '#fff', color: '#6c757d', fontWeight: 500, fontSize: 14 }}
        >Back</button>
      </div>
    </div>
  );

  const allMedications = [...activeMedications, ...inactiveMedications];

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
            onClick={() => {
              resetForm();
              setShowAddForm(false);
              setShowScheduleFor(null);
            }}
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
            disabled={loading}
          >
            {loading ? 'Saving...' : (editingMed ? 'Update Medication' : 'Add Medication')}
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
            onClick={() => { 
              if (showAddForm) {
                // Cancel: hide form and reset
                setShowAddForm(false);
                setShowScheduleFor(null);
                resetForm();
              } else {
                // Show form: reset and show
                resetForm();
                setShowScheduleFor(null);
                setShowAddForm(true);
              }
            }}
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
            disabled={loading}
          >
            {showAddForm ? 'Cancel' : 'Add Medication'}
          </button>
        </div>

        <div style={{ flex: 1, overflow: 'auto' }}>
          {loading && (
            <div style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
              Loading...
            </div>
          )}
          {!loading && showScheduleFor ? (
            renderScheduleView(allMedications.find(m => m.id === showScheduleFor) || {schedules: []})
          ) : !loading && showAddForm ? (
            renderForm()
          ) : !loading ? (
            <div>
              {tab === 'scheduled' ? (
                <div>
                  {/* All Scheduled Medications in Chronological Order */}
                  {scheduledMedications.scheduled_medications && scheduledMedications.scheduled_medications.length > 0 ? (
                    <div>
                      <h3 style={{ margin: '0 0 16px 0', color: '#333', fontSize: '18px', fontWeight: '600' }}>
                        Medication Schedule
                      </h3>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        {scheduledMedications.scheduled_medications.map((item, idx) => {
                          const colors = getStatusColor(item.status);
                          const isCompleted = item.is_completed;
                          const isToday = new Date(item.scheduled_time).toDateString() === new Date().toDateString();
                          
                          return (
                            <div 
                              key={`scheduled-${idx}`} 
                              style={{
                                backgroundColor: colors.bg,
                                borderRadius: '8px',
                                padding: '16px',
                                boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                                border: `2px solid ${colors.border}`,
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                opacity: isCompleted && isToday ? 0.7 : 1,
                                order: isCompleted && isToday ? 1 : 0
                              }}
                            >
                              <div style={{ flex: 1 }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '4px' }}>
                                  <h4 style={{ margin: 0, color: colors.text, fontSize: '16px', fontWeight: '600' }}>
                                    {item.medication_name}
                                  </h4>
                                  <span 
                                    style={{ 
                                      backgroundColor: colors.border, 
                                      color: '#fff', 
                                      padding: '2px 8px', 
                                      borderRadius: '12px', 
                                      fontSize: '12px',
                                      fontWeight: '500'
                                    }}
                                  >
                                    {getStatusText(item)}
                                  </span>
                                </div>
                                
                                <div style={{ color: colors.text, fontSize: '14px', marginBottom: '2px' }}>
                                  <span style={{ fontWeight: '500' }}>Scheduled: </span>
                                  {formatDate(item.scheduled_time)} at {formatTime(item.scheduled_time)}
                                </div>
                                
                                <div style={{ color: colors.text, fontSize: '14px', marginBottom: '2px' }}>
                                  <span style={{ fontWeight: '500' }}>Dose: </span>
                                  {item.dose_amount} {item.dose_unit}
                                </div>
                                
                                {item.description && (
                                  <div style={{ color: colors.text, fontSize: '14px', marginBottom: '2px' }}>
                                    <span style={{ fontWeight: '500' }}>Schedule: </span>
                                    {item.description}
                                  </div>
                                )}
                                
                                {isCompleted && item.administered_at && (
                                  <div style={{ color: colors.text, fontSize: '14px' }}>
                                    <span style={{ fontWeight: '500' }}>Taken: </span>
                                    {formatDate(item.administered_at)} at {formatTime(item.administered_at)}
                                    {item.actual_dose && item.actual_dose !== item.dose_amount && (
                                      <span> ({item.actual_dose} {item.dose_unit})</span>
                                    )}
                                  </div>
                                )}
                              </div>
                              
                              <div style={{ display: 'flex', gap: '8px' }}>
                                {!isCompleted && (
                                  <>
                                    <button
                                      style={{
                                        padding: '8px 16px',
                                        border: 'none',
                                        borderRadius: '4px',
                                        backgroundColor: '#28a745',
                                        color: '#fff',
                                        cursor: 'pointer',
                                        fontSize: '14px',
                                        fontWeight: '500'
                                      }}
                                      onClick={() => {
                                        // TODO: Implement marking as taken
                                        alert('Mark as taken functionality coming soon');
                                      }}
                                    >
                                      {item.status === 'missed' ? 'Take Now' : 'Mark Taken'}
                                    </button>
                                    
                                    {item.status === 'missed' && (
                                      <button
                                        style={{
                                          padding: '8px 16px',
                                          border: '2px solid #6c757d',
                                          borderRadius: '4px',
                                          backgroundColor: '#fff',
                                          color: '#6c757d',
                                          cursor: 'pointer',
                                          fontSize: '14px',
                                          fontWeight: '500'
                                        }}
                                        onClick={() => {
                                          // TODO: Implement skipping missed dose
                                          alert('Skip dose functionality coming soon');
                                        }}
                                      >
                                        Skip
                                      </button>
                                    )}
                                  </>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                      
                      {/* Legend */}
                      <div style={{ marginTop: '24px', padding: '16px', backgroundColor: '#f8f9fa', borderRadius: '8px' }}>
                        <h4 style={{ margin: '0 0 12px 0', color: '#333', fontSize: '14px', fontWeight: '600' }}>Status Legend:</h4>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '16px', fontSize: '12px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <div style={{ width: 12, height: 12, backgroundColor: '#28a745', borderRadius: '50%' }}></div>
                            <span>On time (±1 hour)</span>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <div style={{ width: 12, height: 12, backgroundColor: '#ffc107', borderRadius: '50%' }}></div>
                            <span>Warning (1-2 hours off)</span>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <div style={{ width: 12, height: 12, backgroundColor: '#dc3545', borderRadius: '50%' }}></div>
                            <span>Late/Early ({'>'}2 hours off)</span>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <div style={{ width: 12, height: 12, backgroundColor: '#17a2b8', borderRadius: '50%' }}></div>
                            <span>Upcoming</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div style={{
                      textAlign: 'center',
                      padding: '40px',
                      color: '#666',
                      backgroundColor: '#f8f9fa',
                      borderRadius: '8px'
                    }}>
                      <p style={{ margin: '0 0 10px 0', fontSize: '18px', fontWeight: '500' }}>No scheduled medications</p>
                      <p style={{ margin: 0 }}>No medications scheduled for today and yesterday.</p>
                    </div>
                  )}
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
          ) : null}
        </div>
      </div>
    </ModalBase>
  );
};

export default MedicationModal;
