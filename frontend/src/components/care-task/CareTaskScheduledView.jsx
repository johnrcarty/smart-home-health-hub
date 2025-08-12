import React from 'react';

const CareTaskScheduledView = ({ 
  scheduledTasks, 
  getStatusColor, 
  getStatusText, 
  handleMarkCompleted,
  handleSkipTask,
  statusFilters,
  setStatusFilters,
  showFilters,
  setShowFilters
}) => {
  const allScheduledTasks = scheduledTasks.scheduled_care_tasks || [];

  // Filter tasks based on status filters
  const filteredTasks = allScheduledTasks.filter(task => {
    const taskStatus = getStatusText(task);
    return statusFilters[taskStatus] !== false;
  });

  const handleFilterChange = (status) => {
    setStatusFilters(prev => ({
      ...prev,
      [status]: !prev[status]
    }));
  };

  const renderStatusFilters = () => {
    if (!showFilters) return null;

    const filterOptions = [
      { key: 'ready_to_take', label: 'Ready to Complete', color: '#28a745' },
      { key: 'upcoming', label: 'Upcoming', color: '#17a2b8' },
      { key: 'warning', label: 'Warning', color: '#ffc107' },
      { key: 'missed', label: 'Missed', color: '#dc3545' },
      { key: 'on_time', label: 'On Time', color: '#28a745' },
      { key: 'late_early', label: 'Late/Early', color: '#fd7e14' },
      { key: 'skipped', label: 'Skipped', color: '#6c757d' }
    ];

    return (
      <div style={{
        marginBottom: '20px',
        padding: '16px',
        backgroundColor: '#2d3748',
        borderRadius: '8px',
        border: '1px solid #4a5568'
      }}>
        <h4 style={{ 
          margin: '0 0 12px 0', 
          color: '#ffffff', 
          fontSize: '14px', 
          fontWeight: '600' 
        }}>
          Filter by Status:
        </h4>
        <div style={{ 
          display: 'flex', 
          flexWrap: 'wrap', 
          gap: '12px' 
        }}>
          {filterOptions.map(option => (
            <label 
              key={option.key}
              style={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: '6px',
                cursor: 'pointer',
                color: '#e2e8f0',
                fontSize: '12px'
              }}
            >
              <input
                type="checkbox"
                checked={statusFilters[option.key] || false}
                onChange={() => handleFilterChange(option.key)}
                style={{ cursor: 'pointer' }}
              />
              <div style={{
                width: '12px',
                height: '12px',
                backgroundColor: option.color,
                borderRadius: '50%',
                marginRight: '4px'
              }}></div>
              {option.label}
            </label>
          ))}
        </div>
      </div>
    );
  };

  const renderScheduledTasks = () => {
    // Group by day (YYYY-MM-DD) and time
    const groupByDay = {};
    filteredTasks.forEach(item => {
      const dateObj = new Date(item.scheduled_time);
      const dayKey = dateObj.toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
      const timeStr = dateObj.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit', hour12: true });
      if (!groupByDay[dayKey]) groupByDay[dayKey] = {};
      if (!groupByDay[dayKey][timeStr]) groupByDay[dayKey][timeStr] = [];
      groupByDay[dayKey][timeStr].push(item);
    });
    
    // Sort days chronologically
    const sortedDays = Object.keys(groupByDay).sort((a, b) => {
      // Parse to Date for sorting
      const parse = d => new Date(d);
      return parse(a) - parse(b);
    });
    
    return (
      <div>
        {sortedDays.map(dayKey => (
          <div key={dayKey} style={{ marginBottom: 36 }}>
            <div style={{ fontWeight: 800, fontSize: 22, color: '#fff', marginBottom: 8, letterSpacing: 0.5, textShadow: '0 1px 2px #222' }}>{dayKey}</div>
            <div style={{ borderBottom: '2px solid #e2e8f0', marginBottom: 16 }} />
            {Object.keys(groupByDay[dayKey]).sort((a, b) => {
              // Convert to 24h for sorting
              const parse = t => {
                const [h, m, ampm] = t.match(/(\d+):(\d+)\s*(AM|PM)/i).slice(1);
                let hour = parseInt(h, 10);
                if (/pm/i.test(ampm) && hour !== 12) hour += 12;
                if (/am/i.test(ampm) && hour === 12) hour = 0;
                return hour * 60 + parseInt(m, 10);
              };
              return parse(a) - parse(b);
            }).map(timeStr => (
              <div key={timeStr} style={{
                marginBottom: 32,
                background: '#181f2a',
                borderRadius: 18,
                boxShadow: '0 2px 8px rgba(0,0,0,0.10)',
                padding: '18px 24px',
                display: 'flex',
                flexDirection: 'column',
                position: 'relative',
                border: '1.5px solid #2d3748',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
                  <div style={{ fontWeight: 700, fontSize: 20, color: '#00bfff', letterSpacing: 0.2, textShadow: '0 1px 2px #222' }}>{timeStr}</div>
                  <button style={{
                    background: '#007bff',
                    color: '#fff',
                    border: 'none',
                    borderRadius: 12,
                    padding: '8px 18px',
                    fontWeight: 600,
                    fontSize: 14,
                    boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
                    cursor: 'pointer',
                    transition: 'background 0.2s',
                  }}
                  onClick={() => {
                    // Mark all tasks for this time slot as completed
                    groupByDay[dayKey][timeStr].forEach(task => {
                      if (!task.is_completed) {
                        handleMarkCompleted(task);
                      }
                    });
                  }}
                  >
                    Mark All
                  </button>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                  {groupByDay[dayKey][timeStr].map((item, idx) => {
                    const statusColors = getStatusColor(item.status);
                    const isCompleted = item.is_completed;
                    const isToday = new Date(item.scheduled_time).toDateString() === new Date().toDateString();
                    
                    // Get category color if available
                    const categoryColor = item.care_task_category_color || '#6f42c1';
                    
                    return (
                      <div
                        key={`scheduled-${dayKey}-${timeStr}-${idx}`}
                        style={{
                          backgroundColor: statusColors.bg,
                          borderRadius: 12,
                          padding: '14px 18px',
                          boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
                          border: `1.5px solid ${statusColors.border}`,
                          borderLeft: `6px solid ${categoryColor}`, // Category color on left border
                          display: 'flex',
                          alignItems: 'center',
                          gap: '12px',
                          marginBottom: 0,
                          opacity: isCompleted && isToday ? 0.7 : 1,
                          order: isCompleted && isToday ? 1 : 0,
                          position: 'relative'
                        }}
                      >
                        {/* Category color indicator */}
                        <div style={{
                          position: 'absolute',
                          top: 8,
                          right: 8,
                          width: 12,
                          height: 12,
                          borderRadius: '50%',
                          backgroundColor: categoryColor,
                          border: '2px solid #fff',
                          boxShadow: '0 1px 3px rgba(0,0,0,0.2)'
                        }}></div>
                        
                        <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 10 }}>
                          <span style={{ color: statusColors.text, fontSize: '16px', fontWeight: '600' }}>
                            {item.care_task_name}
                          </span>
                          {item.care_task_description && (
                            <span style={{ color: statusColors.text, fontSize: '14px', fontWeight: 400, opacity: 0.8 }}>
                              - {item.care_task_description}
                            </span>
                          )}
                          {item.care_task_category_name && (
                            <span style={{ 
                              backgroundColor: categoryColor, 
                              color: '#fff', 
                              padding: '2px 8px', 
                              borderRadius: '12px', 
                              fontSize: '11px',
                              fontWeight: '600',
                              marginLeft: 8
                            }}>
                              {item.care_task_category_name}
                            </span>
                          )}
                          <span 
                            style={{ 
                              backgroundColor: statusColors.border, 
                              color: '#fff', 
                              padding: '2px 8px', 
                              borderRadius: '12px', 
                              fontSize: '12px',
                              fontWeight: '500',
                              marginLeft: 8
                            }}
                          >
                            {getStatusText(item)}
                          </span>
                        </div>
                        <div style={{ display: 'flex', gap: '8px' }}>
                          {!isCompleted && (
                            <>
                              <button
                                style={{
                                  padding: '6px 14px',
                                  border: 'none',
                                  borderRadius: '8px',
                                  backgroundColor: '#28a745',
                                  color: '#fff',
                                  cursor: 'pointer',
                                  fontSize: '13px',
                                  fontWeight: '500',
                                  boxShadow: '0 1px 2px rgba(0,0,0,0.07)'
                                }}
                                onClick={() => handleMarkCompleted(item)}
                              >
                                {item.status === 'missed' ? 'Complete Now' : 'Mark Completed'}
                              </button>
                              {item.status === 'missed' && (
                                <button
                                  style={{
                                    padding: '6px 14px',
                                    border: '2px solid #6c757d',
                                    borderRadius: '8px',
                                    backgroundColor: '#fff',
                                    color: '#6c757d',
                                    cursor: 'pointer',
                                    fontSize: '13px',
                                    fontWeight: '500',
                                    boxShadow: '0 1px 2px rgba(0,0,0,0.07)'
                                  }}
                                  onClick={() => handleSkipTask(item)}
                                >
                                  Skip
                                </button>
                              )}
                            </>
                          )}
                          {isCompleted && (
                            <div style={{
                              padding: '6px 14px',
                              backgroundColor: '#e8f5e8',
                              color: '#28a745',
                              borderRadius: '8px',
                              fontSize: '13px',
                              fontWeight: '600',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '4px'
                            }}>
                              ✓ Completed
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>
    );
  };

  return (
    <div>
      {scheduledTasks.scheduled_care_tasks && scheduledTasks.scheduled_care_tasks.length > 0 ? (
        <div>
          {/* Filter Toggle Button */}
          <div style={{ marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ margin: 0, color: '#ffffff', fontSize: '18px', fontWeight: '600' }}>
              Today's Scheduled Care Tasks
            </h3>
            <button
              onClick={() => setShowFilters(!showFilters)}
              style={{
                padding: '8px 16px',
                backgroundColor: showFilters ? '#007bff' : '#6c757d',
                color: '#fff',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '12px',
                fontWeight: '500',
                transition: 'background-color 0.2s'
              }}
            >
              {showFilters ? 'Hide Filters' : 'Show Filters'}
            </button>
          </div>
          
          {/* Status Filters */}
          {renderStatusFilters()}
          
          {/* Task Count */}
          {filteredTasks.length !== allScheduledTasks.length && (
            <div style={{
              marginBottom: '16px',
              padding: '8px 12px',
              backgroundColor: '#374151',
              borderRadius: '6px',
              color: '#e2e8f0',
              fontSize: '12px'
            }}>
              Showing {filteredTasks.length} of {allScheduledTasks.length} tasks
            </div>
          )}
          
          {filteredTasks.length > 0 ? renderScheduledTasks() : (
            <div style={{
              textAlign: 'center',
              padding: '40px',
              color: '#a0aec0',
              backgroundColor: '#2d3748',
              borderRadius: '8px',
              border: '1px solid #4a5568'
            }}>
              <p style={{ margin: '0 0 10px 0', fontSize: '18px', fontWeight: '500', color: '#ffffff' }}>
                No tasks match current filters
              </p>
              <p style={{ margin: 0, color: '#a0aec0' }}>
                Adjust your status filters to see more tasks.
              </p>
            </div>
          )}
          
          {/* Legend */}
          <div style={{ marginTop: '24px', padding: '16px', backgroundColor: '#2d3748', borderRadius: '8px', border: '1px solid #4a5568' }}>
            <h4 style={{ margin: '0 0 12px 0', color: '#ffffff', fontSize: '14px', fontWeight: '600' }}>Status Legend:</h4>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '16px', fontSize: '12px', color: '#e2e8f0', marginBottom: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <div style={{ width: 12, height: 12, backgroundColor: '#28a745', borderRadius: '50%' }}></div>
                <span>Ready to complete</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <div style={{ width: 12, height: 12, backgroundColor: '#ffc107', borderRadius: '50%' }}></div>
                <span>Warning (running late)</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <div style={{ width: 12, height: 12, backgroundColor: '#dc3545', borderRadius: '50%' }}></div>
                <span>Missed/Overdue</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <div style={{ width: 12, height: 12, backgroundColor: '#17a2b8', borderRadius: '50%' }}></div>
                <span>Upcoming</span>
              </div>
            </div>
            <div style={{ fontSize: '12px', color: '#e2e8f0', marginTop: 8, paddingTop: 8, borderTop: '1px solid #4a5568' }}>
              <span style={{ fontWeight: '600' }}>Category Colors:</span> Left border and small dot indicate task category
            </div>
          </div>
        </div>
      ) : (
        <div style={{
          textAlign: 'center',
          padding: '40px',
          color: '#a0aec0',
          backgroundColor: '#2d3748',
          borderRadius: '8px',
          border: '1px solid #4a5568'
        }}>
          <p style={{ margin: '0 0 10px 0', fontSize: '18px', fontWeight: '500', color: '#ffffff' }}>No scheduled care tasks</p>
          <p style={{ margin: 0, color: '#a0aec0' }}>No care tasks scheduled for today and yesterday.</p>
        </div>
      )}
    </div>
  );
};

export default CareTaskScheduledView;
