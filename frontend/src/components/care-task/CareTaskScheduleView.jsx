import React, { useState, useEffect } from 'react';

const CareTaskScheduleView = ({ taskId, taskName, onClose }) => {
  const [schedules, setSchedules] = useState([]);
  const [showAddForm, setShowAddForm] = useState(false);
  const [formData, setFormData] = useState({
    cron_expression: '',
    description: '',
    active: true
  });
  const [editingSchedule, setEditingSchedule] = useState(null);

  useEffect(() => {
    fetchSchedules();
  }, [taskId]);

  const fetchSchedules = async () => {
    try {
      const response = await fetch(`/api/care-task-schedules/${taskId}`);
      if (response.ok) {
        const data = await response.json();
        setSchedules(data);
      }
    } catch (error) {
      console.error('Error fetching schedules:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      const url = editingSchedule 
        ? `/api/care-task-schedule/${editingSchedule.id}`
        : '/api/add/care-task-schedule';
      
      const method = editingSchedule ? 'PUT' : 'POST';
      
      const payload = {
        ...formData,
        care_task_id: taskId
      };

      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        setFormData({
          cron_expression: '',
          description: '',
          active: true
        });
        setShowAddForm(false);
        setEditingSchedule(null);
        fetchSchedules();
      } else {
        console.error('Failed to save schedule');
      }
    } catch (error) {
      console.error('Error saving schedule:', error);
    }
  };

  const handleEdit = (schedule) => {
    setEditingSchedule(schedule);
    setFormData({
      cron_expression: schedule.cron_expression,
      description: schedule.description || '',
      active: schedule.active
    });
    setShowAddForm(true);
  };

  const handleDelete = async (scheduleId) => {
    if (!confirm('Are you sure you want to delete this schedule?')) return;
    
    try {
      const response = await fetch(`/api/care-task-schedule/${scheduleId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        fetchSchedules();
      } else {
        console.error('Failed to delete schedule');
      }
    } catch (error) {
      console.error('Error deleting schedule:', error);
    }
  };

  const toggleScheduleActive = async (scheduleId, currentActive) => {
    try {
      const response = await fetch(`/api/care-task-schedule/${scheduleId}/toggle`, {
        method: 'POST',
      });

      if (response.ok) {
        fetchSchedules();
      } else {
        console.error('Failed to toggle schedule');
      }
    } catch (error) {
      console.error('Error toggling schedule:', error);
    }
  };

  const cancelEdit = () => {
    setEditingSchedule(null);
    setFormData({
      cron_expression: '',
      description: '',
      active: true
    });
    setShowAddForm(false);
  };

  const formatCronDescription = (cronExpression) => {
    // Basic cron description mapping
    const cronDescriptions = {
      '0 8 * * *': 'Daily at 8:00 AM',
      '0 20 * * *': 'Daily at 8:00 PM',
      '0 8 * * 1-5': 'Weekdays at 8:00 AM',
      '0 9,17 * * *': 'Daily at 9:00 AM and 5:00 PM',
      '0 8 * * 0': 'Sundays at 8:00 AM',
      '0 8 1 * *': 'Monthly on 1st at 8:00 AM',
      '0 */4 * * *': 'Every 4 hours',
      '0 */8 * * *': 'Every 8 hours',
      '0 */12 * * *': 'Every 12 hours'
    };
    
    return cronDescriptions[cronExpression] || cronExpression;
  };

  const commonCronExpressions = [
    { value: '0 8 * * *', label: 'Daily at 8:00 AM' },
    { value: '0 20 * * *', label: 'Daily at 8:00 PM' },
    { value: '0 8 * * 1-5', label: 'Weekdays at 8:00 AM' },
    { value: '0 9,17 * * *', label: 'Daily at 9:00 AM and 5:00 PM' },
    { value: '0 8 * * 0', label: 'Sundays at 8:00 AM' },
    { value: '0 8 1 * *', label: 'Monthly on 1st at 8:00 AM' },
    { value: '0 */4 * * *', label: 'Every 4 hours' },
    { value: '0 */8 * * *', label: 'Every 8 hours' },
    { value: '0 */12 * * *', label: 'Every 12 hours' }
  ];

  return (
    <div style={{ padding: '20px' }}>
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        marginBottom: '20px',
        borderBottom: '2px solid #e9ecef',
        paddingBottom: '15px'
      }}>
        <h3 style={{ margin: 0, color: '#333' }}>
          Schedule for: {taskName}
        </h3>
        <button
          onClick={onClose}
          style={{
            padding: '8px 16px',
            border: 'none',
            borderRadius: '4px',
            backgroundColor: '#6c757d',
            color: '#fff',
            cursor: 'pointer'
          }}
        >
          Back to Tasks
        </button>
      </div>

      {!showAddForm ? (
        <button
          onClick={() => setShowAddForm(true)}
          style={{
            padding: '10px 20px',
            border: 'none',
            borderRadius: '6px',
            backgroundColor: '#28a745',
            color: '#fff',
            cursor: 'pointer',
            fontWeight: '500',
            marginBottom: '20px'
          }}
        >
          Add Schedule
        </button>
      ) : (
        <div style={{
          backgroundColor: '#f8f9fa',
          padding: '20px',
          borderRadius: '8px',
          marginBottom: '20px'
        }}>
          <h4 style={{ marginTop: 0, color: '#333' }}>
            {editingSchedule ? 'Edit Schedule' : 'Add New Schedule'}
          </h4>
          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: '15px' }}>
              <label style={{ display: 'block', marginBottom: '5px', fontWeight: '500' }}>
                Schedule Pattern:
              </label>
              <select
                value={formData.cron_expression}
                onChange={(e) => setFormData({ ...formData, cron_expression: e.target.value })}
                style={{
                  width: '100%',
                  padding: '8px',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  fontSize: '14px'
                }}
                required
              >
                <option value="">Select a schedule pattern</option>
                {commonCronExpressions.map((expr) => (
                  <option key={expr.value} value={expr.value}>
                    {expr.label}
                  </option>
                ))}
              </select>
            </div>

            <div style={{ marginBottom: '15px' }}>
              <label style={{ display: 'block', marginBottom: '5px', fontWeight: '500' }}>
                Custom Cron Expression (optional):
              </label>
              <input
                type="text"
                value={formData.cron_expression}
                onChange={(e) => setFormData({ ...formData, cron_expression: e.target.value })}
                placeholder="e.g., 0 8 * * * (8:00 AM daily)"
                style={{
                  width: '100%',
                  padding: '8px',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  fontSize: '14px'
                }}
              />
              <small style={{ color: '#666', fontSize: '12px' }}>
                Format: minute hour day month weekday (0=Sunday)
              </small>
            </div>

            <div style={{ marginBottom: '15px' }}>
              <label style={{ display: 'block', marginBottom: '5px', fontWeight: '500' }}>
                Description (optional):
              </label>
              <input
                type="text"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Brief description of this schedule"
                style={{
                  width: '100%',
                  padding: '8px',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  fontSize: '14px'
                }}
              />
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input
                  type="checkbox"
                  checked={formData.active}
                  onChange={(e) => setFormData({ ...formData, active: e.target.checked })}
                />
                <span style={{ fontWeight: '500' }}>Active</span>
              </label>
            </div>

            <div style={{ display: 'flex', gap: '10px' }}>
              <button
                type="submit"
                style={{
                  padding: '10px 20px',
                  border: 'none',
                  borderRadius: '6px',
                  backgroundColor: '#007bff',
                  color: '#fff',
                  cursor: 'pointer',
                  fontWeight: '500'
                }}
              >
                {editingSchedule ? 'Update Schedule' : 'Add Schedule'}
              </button>
              <button
                type="button"
                onClick={cancelEdit}
                style={{
                  padding: '10px 20px',
                  border: '1px solid #ddd',
                  borderRadius: '6px',
                  backgroundColor: '#fff',
                  color: '#333',
                  cursor: 'pointer'
                }}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div>
        <h4 style={{ color: '#333', marginBottom: '15px' }}>Current Schedules</h4>
        {schedules.length === 0 ? (
          <div style={{
            textAlign: 'center',
            padding: '40px',
            color: '#666',
            backgroundColor: '#f8f9fa',
            borderRadius: '8px'
          }}>
            <p>No schedules found for this care task.</p>
          </div>
        ) : (
          schedules.map((schedule) => (
            <div
              key={schedule.id}
              style={{
                backgroundColor: '#fff',
                border: `2px solid ${schedule.active ? '#28a745' : '#6c757d'}`,
                borderRadius: '8px',
                padding: '16px',
                marginBottom: '12px',
                boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ marginBottom: '8px' }}>
                    <span style={{ fontWeight: '600', color: '#333', fontSize: '16px' }}>
                      {formatCronDescription(schedule.cron_expression)}
                    </span>
                    <span style={{
                      marginLeft: '10px',
                      padding: '2px 8px',
                      borderRadius: '12px',
                      fontSize: '12px',
                      fontWeight: '500',
                      backgroundColor: schedule.active ? '#d4edda' : '#f8d7da',
                      color: schedule.active ? '#155724' : '#721c24'
                    }}>
                      {schedule.active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                  <div style={{ fontSize: '14px', color: '#666', marginBottom: '4px' }}>
                    Cron: {schedule.cron_expression}
                  </div>
                  {schedule.description && (
                    <div style={{ fontSize: '14px', color: '#666' }}>
                      {schedule.description}
                    </div>
                  )}
                </div>
                <div style={{ display: 'flex', gap: '8px', marginLeft: '16px' }}>
                  <button
                    onClick={() => handleEdit(schedule)}
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
                    onClick={() => toggleScheduleActive(schedule.id, schedule.active)}
                    style={{
                      padding: '6px 12px',
                      border: 'none',
                      borderRadius: '4px',
                      backgroundColor: schedule.active ? '#6c757d' : '#28a745',
                      color: '#fff',
                      cursor: 'pointer',
                      fontSize: '12px'
                    }}
                  >
                    {schedule.active ? 'Pause' : 'Resume'}
                  </button>
                  <button
                    onClick={() => handleDelete(schedule.id)}
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
          ))
        )}
      </div>
    </div>
  );
};

export default CareTaskScheduleView;
