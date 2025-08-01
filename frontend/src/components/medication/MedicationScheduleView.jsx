import React, { useState } from 'react';
import config from '../../config';

const MedicationScheduleView = ({ 
  med, 
  onBack, 
  fetchMedications,
  loading,
  setLoading 
}) => {
  const [scheduleMode, setScheduleMode] = useState('weekly'); // 'weekly' or 'monthly'
  const [selectedDays, setSelectedDays] = useState([]); // for weekly
  const [selectedDayOfMonth, setSelectedDayOfMonth] = useState(1); // for monthly
  const [time, setTime] = useState('08:00');
  const [doseAmount, setDoseAmount] = useState('1.000');

  const daysOfWeek = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

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
        const scheduleObj = {
          id: scheduleId,
          doseAmount,
          isActive,
          parsed
        };
        
        if (parsed.type === 'weekly') {
          weekly.push(scheduleObj);
        } else if (parsed.type === 'monthly') {
          monthly.push(scheduleObj);
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
        const error = await response.json();
        throw new Error(error.detail || 'Failed to add schedule');
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

  return (
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
          onClick={onBack}
          style={{ padding: '10px 24px', border: '2px solid #6c757d', borderRadius: 6, background: '#fff', color: '#6c757d', fontWeight: 500, fontSize: 14 }}
        >Back</button>
      </div>
    </div>
  );
};

export default MedicationScheduleView;
