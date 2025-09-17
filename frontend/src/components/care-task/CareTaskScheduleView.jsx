import React, { useState, useEffect } from 'react';
import config from '../../config';

const CareTaskScheduleView = ({ taskId, taskName, onClose }) => {
  const [schedules, setSchedules] = useState([]);
  const [scheduleMode, setScheduleMode] = useState('weekly'); // 'weekly' or 'monthly'
  const [selectedDays, setSelectedDays] = useState([]); // for weekly
  const [selectedDayOfMonth, setSelectedDayOfMonth] = useState(1); // for monthly
  const [time, setTime] = useState('08:00');
  const [loading, setLoading] = useState(false);

  const daysOfWeek = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  useEffect(() => {
    fetchSchedules();
  }, [taskId]);

  const fetchSchedules = async () => {
    try {
      const response = await fetch(`${config.apiUrl}/api/care-tasks/${taskId}/schedules`);
      if (response.ok) {
        const data = await response.json();
        setSchedules(data);
      }
    } catch (error) {
      console.error('Error fetching schedules:', error);
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
      const isActive = schedule.active;
      const scheduleId = schedule.id;
      const description = schedule.description;
      
      const parsed = parseCronExpression(cronExpression);
      if (parsed) {
        const scheduleObj = {
          id: scheduleId,
          isActive,
          parsed,
          description
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

  const handleAddSchedule = async () => {
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
      const response = await fetch(`${config.apiUrl}/api/add/care-task-schedule/${taskId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          cron_expression: cron,
          description: description,
          active: true
        })
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to add schedule');
      }
      
      // Refresh schedules
      await fetchSchedules();
      
      // Reset form
      setSelectedDays([]);
      setSelectedDayOfMonth(1);
      setTime('08:00');
      setScheduleMode('weekly');
    } catch (error) {
      console.error('Error adding schedule:', error);
      alert(`Error adding schedule: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteSchedule = async (scheduleId) => {
    if (!confirm('Are you sure you want to delete this schedule?')) return;
    
    try {
      setLoading(true);
      const response = await fetch(`${config.apiUrl}/api/care-task-schedules/${scheduleId}`, {
        method: 'DELETE'
      });
      
      if (!response.ok) {
        throw new Error('Failed to delete schedule');
      }
      
      // Refresh schedules
      await fetchSchedules();
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
      const response = await fetch(`${config.apiUrl}/api/care-task-schedules/${scheduleId}/toggle-active`, {
        method: 'POST'
      });
      
      if (!response.ok) {
        throw new Error('Failed to toggle schedule');
      }
      
      // Refresh schedules
      await fetchSchedules();
    } catch (error) {
      console.error('Error toggling schedule:', error);
      alert('Error updating schedule status. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: 24 }}>
      {/* Add New Schedule Form */}
      <div style={{ marginBottom: 24, padding: 20, backgroundColor: '#f8f9fa', borderRadius: 8, border: '1px solid #dee2e6' }}>
        <h4 style={{ margin: '0 0 16px 0', color: '#333', fontSize: 16, fontWeight: 600 }}>Add New Schedule</h4>
        
        <div style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
          <button
            type="button"
            onClick={() => setScheduleMode('weekly')}
            style={{ 
              padding: '8px 18px', 
              border: 'none', 
              borderRadius: 6, 
              background: scheduleMode === 'weekly' ? '#007bff' : '#f8f9fa', 
              color: scheduleMode === 'weekly' ? '#fff' : '#333', 
              fontWeight: 500, 
              fontSize: 14,
              cursor: 'pointer',
              transition: 'all 0.2s'
            }}
          >
            Weekly
          </button>
          <button
            type="button"
            onClick={() => setScheduleMode('monthly')}
            style={{ 
              padding: '8px 18px', 
              border: 'none', 
              borderRadius: 6, 
              background: scheduleMode === 'monthly' ? '#007bff' : '#f8f9fa', 
              color: scheduleMode === 'monthly' ? '#fff' : '#333', 
              fontWeight: 500, 
              fontSize: 14,
              cursor: 'pointer',
              transition: 'all 0.2s'
            }}
          >
            Monthly
          </button>
        </div>

        {scheduleMode === 'weekly' ? (
          <div style={{ marginBottom: 12 }}>
            <label style={{ fontWeight: 600, color: '#333', marginBottom: 8, display: 'block' }}>Select Days</label>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {daysOfWeek.map((d, i) => (
                <label 
                  key={d} 
                  style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: 4, 
                    background: selectedDays.includes(i.toString()) ? '#007bff' : '#fff', 
                    color: selectedDays.includes(i.toString()) ? '#fff' : '#333', 
                    borderRadius: 4, 
                    padding: '6px 12px', 
                    cursor: 'pointer', 
                    fontWeight: 500,
                    border: '1px solid #ddd',
                    transition: 'all 0.2s'
                  }}
                >
                  <input
                    type="checkbox"
                    checked={selectedDays.includes(i.toString())}
                    onChange={() => {
                      setSelectedDays(prev => 
                        prev.includes(i.toString()) 
                          ? prev.filter(x => x !== i.toString()) 
                          : [...prev, i.toString()]
                      );
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
              style={{ 
                padding: '8px 16px', 
                border: '2px solid #ddd', 
                borderRadius: 6, 
                fontSize: 14, 
                background: '#fff', 
                color: '#333',
                minWidth: 100
              }}
            >
              {[...Array(28)].map((_, i) => (
                <option key={i+1} value={i+1}>{i+1}</option>
              ))}
            </select>
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: 16, alignItems: 'end', marginBottom: 16 }}>
          <div>
            <label style={{ fontWeight: 600, color: '#333', marginBottom: 8, display: 'block' }}>Time</label>
            <input
              type="time"
              value={time}
              onChange={e => setTime(e.target.value)}
              style={{ 
                padding: '8px 12px', 
                border: '2px solid #ddd', 
                borderRadius: 6, 
                fontSize: 14, 
                background: '#fff', 
                color: '#333', 
                width: 120 
              }}
            />
          </div>

          <div>
            <button
              type="button"
              onClick={handleAddSchedule}
              style={{ 
                padding: '10px 20px', 
                border: 'none', 
                borderRadius: 6, 
                background: '#28a745', 
                color: '#fff', 
                fontWeight: 500, 
                fontSize: 14,
                cursor: 'pointer',
                transition: 'background-color 0.2s'
              }}
              disabled={loading || (scheduleMode === 'weekly' ? selectedDays.length === 0 : false)}
              onMouseOver={(e) => {
                if (!loading && !(scheduleMode === 'weekly' && selectedDays.length === 0)) {
                  e.target.style.background = '#1e7e34';
                }
              }}
              onMouseOut={(e) => {
                if (!loading && !(scheduleMode === 'weekly' && selectedDays.length === 0)) {
                  e.target.style.background = '#28a745';
                }
              }}
            >
              {loading ? 'Adding...' : 'Add Schedule'}
            </button>
          </div>
        </div>
      </div>

      {/* Existing Schedules */}
      <div style={{ marginBottom: 16 }}>
        <h4 style={{ margin: '0 0 16px 0', color: '#333', fontSize: 16, fontWeight: 600 }}>Current Schedules</h4>
        
        {schedules && schedules.length > 0 ? (() => {
          const { weekly, monthly } = separateSchedules(schedules);
          
          return (
            <>
              {weekly.length > 0 && (
                <div style={{ marginBottom: 24 }}>
                  <h5 style={{ margin: '0 0 12px 0', color: '#495057', fontSize: 14, fontWeight: 600 }}>Weekly Schedules</h5>
                  <div style={{ backgroundColor: '#fff', borderRadius: 8, border: '1px solid #dee2e6', overflow: 'hidden' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                      <thead>
                        <tr style={{ backgroundColor: '#f8f9fa' }}>
                          <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: 13, fontWeight: 600, color: '#495057', borderBottom: '1px solid #dee2e6' }}>
                            Time
                          </th>
                          <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: 13, fontWeight: 600, color: '#495057', borderBottom: '1px solid #dee2e6' }}>
                            Days
                          </th>
                          <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: 13, fontWeight: 600, color: '#495057', borderBottom: '1px solid #dee2e6' }}>
                            Description
                          </th>
                          <th style={{ padding: '12px 16px', textAlign: 'center', fontSize: 13, fontWeight: 600, color: '#495057', borderBottom: '1px solid #dee2e6' }}>
                            Status
                          </th>
                          <th style={{ padding: '12px 16px', textAlign: 'center', fontSize: 13, fontWeight: 600, color: '#495057', borderBottom: '1px solid #dee2e6' }}>
                            Actions
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {weekly.map((schedule, index) => (
                          <tr key={schedule.id} style={{ borderBottom: index < weekly.length - 1 ? '1px solid #f1f3f4' : 'none' }}>
                            <td style={{ padding: '12px 16px', fontSize: 14, color: '#333' }}>
                              {schedule.parsed.time}
                            </td>
                            <td style={{ padding: '12px 16px', fontSize: 14, color: '#333' }}>
                              {schedule.parsed.days}
                            </td>
                            <td style={{ padding: '12px 16px', fontSize: 14, color: '#666' }}>
                              {schedule.description || 'No description'}
                            </td>
                            <td style={{ padding: '12px 16px', textAlign: 'center' }}>
                              <span style={{ 
                                padding: '4px 8px', 
                                borderRadius: 4, 
                                fontSize: 12, 
                                fontWeight: 600,
                                background: schedule.isActive ? '#d4edda' : '#f8d7da',
                                color: schedule.isActive ? '#155724' : '#721c24'
                              }}>
                                {schedule.isActive ? 'Active' : 'Inactive'}
                              </span>
                            </td>
                            <td style={{ padding: '12px 16px', textAlign: 'center' }}>
                              <div style={{ display: 'flex', gap: 8, justifyContent: 'center' }}>
                                <button
                                  onClick={() => handleToggleSchedule(schedule.id)}
                                  style={{
                                    padding: '4px 8px',
                                    border: 'none',
                                    borderRadius: 4,
                                    background: schedule.isActive ? '#6c757d' : '#28a745',
                                    color: '#fff',
                                    fontSize: 12,
                                    fontWeight: 500,
                                    cursor: 'pointer'
                                  }}
                                >
                                  {schedule.isActive ? 'Pause' : 'Resume'}
                                </button>
                                <button
                                  onClick={() => handleDeleteSchedule(schedule.id)}
                                  style={{
                                    padding: '4px 8px',
                                    border: 'none',
                                    borderRadius: 4,
                                    background: '#dc3545',
                                    color: '#fff',
                                    fontSize: 12,
                                    fontWeight: 500,
                                    cursor: 'pointer'
                                  }}
                                >
                                  Delete
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {monthly.length > 0 && (
                <div style={{ marginBottom: 24 }}>
                  <h5 style={{ margin: '0 0 12px 0', color: '#495057', fontSize: 14, fontWeight: 600 }}>Monthly Schedules</h5>
                  <div style={{ backgroundColor: '#fff', borderRadius: 8, border: '1px solid #dee2e6', overflow: 'hidden' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                      <thead>
                        <tr style={{ backgroundColor: '#f8f9fa' }}>
                          <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: 13, fontWeight: 600, color: '#495057', borderBottom: '1px solid #dee2e6' }}>
                            Time
                          </th>
                          <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: 13, fontWeight: 600, color: '#495057', borderBottom: '1px solid #dee2e6' }}>
                            Day
                          </th>
                          <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: 13, fontWeight: 600, color: '#495057', borderBottom: '1px solid #dee2e6' }}>
                            Description
                          </th>
                          <th style={{ padding: '12px 16px', textAlign: 'center', fontSize: 13, fontWeight: 600, color: '#495057', borderBottom: '1px solid #dee2e6' }}>
                            Status
                          </th>
                          <th style={{ padding: '12px 16px', textAlign: 'center', fontSize: 13, fontWeight: 600, color: '#495057', borderBottom: '1px solid #dee2e6' }}>
                            Actions
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {monthly.map((schedule, index) => (
                          <tr key={schedule.id} style={{ borderBottom: index < monthly.length - 1 ? '1px solid #f1f3f4' : 'none' }}>
                            <td style={{ padding: '12px 16px', fontSize: 14, color: '#333' }}>
                              {schedule.parsed.time}
                            </td>
                            <td style={{ padding: '12px 16px', fontSize: 14, color: '#333' }}>
                              Day {schedule.parsed.dayOfMonth}
                            </td>
                            <td style={{ padding: '12px 16px', fontSize: 14, color: '#666' }}>
                              {schedule.description || 'No description'}
                            </td>
                            <td style={{ padding: '12px 16px', textAlign: 'center' }}>
                              <span style={{ 
                                padding: '4px 8px', 
                                borderRadius: 4, 
                                fontSize: 12, 
                                fontWeight: 600,
                                background: schedule.isActive ? '#d4edda' : '#f8d7da',
                                color: schedule.isActive ? '#155724' : '#721c24'
                              }}>
                                {schedule.isActive ? 'Active' : 'Inactive'}
                              </span>
                            </td>
                            <td style={{ padding: '12px 16px', textAlign: 'center' }}>
                              <div style={{ display: 'flex', gap: 8, justifyContent: 'center' }}>
                                <button
                                  onClick={() => handleToggleSchedule(schedule.id)}
                                  style={{
                                    padding: '4px 8px',
                                    border: 'none',
                                    borderRadius: 4,
                                    background: schedule.isActive ? '#6c757d' : '#28a745',
                                    color: '#fff',
                                    fontSize: 12,
                                    fontWeight: 500,
                                    cursor: 'pointer'
                                  }}
                                >
                                  {schedule.isActive ? 'Pause' : 'Resume'}
                                </button>
                                <button
                                  onClick={() => handleDeleteSchedule(schedule.id)}
                                  style={{
                                    padding: '4px 8px',
                                    border: 'none',
                                    borderRadius: 4,
                                    background: '#dc3545',
                                    color: '#fff',
                                    fontSize: 12,
                                    fontWeight: 500,
                                    cursor: 'pointer'
                                  }}
                                >
                                  Delete
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          );
        })() : (
          <div style={{
            textAlign: 'center',
            padding: '40px',
            color: '#666',
            backgroundColor: '#f8f9fa',
            borderRadius: '8px',
            border: '1px solid #dee2e6'
          }}>
            <p style={{ margin: 0, fontSize: 16 }}>No schedules found for this care task.</p>
            <p style={{ margin: '8px 0 0 0', fontSize: 14, color: '#888' }}>
              Add a schedule above to get started.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default CareTaskScheduleView;
