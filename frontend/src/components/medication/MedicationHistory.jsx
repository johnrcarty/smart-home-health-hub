import React, { useState, useEffect } from 'react';
import config from '../../config';

const MedicationHistory = ({ onBack }) => {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({
    medication_name: '',
    start_date: '',
    end_date: '',
    status_filter: '',
    limit: 25
  });

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const queryParams = new URLSearchParams();
      
      Object.entries(filters).forEach(([key, value]) => {
        if (value && value !== '') {
          queryParams.append(key, value);
        }
      });

      const response = await fetch(`${config.apiUrl}/api/medications/history?${queryParams}`);
      if (response.ok) {
        const data = await response.json();
        setHistory(data.history || []);
      } else {
        console.error('Failed to fetch medication history');
      }
    } catch (error) {
      console.error('Error fetching medication history:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const handleApplyFilters = () => {
    fetchHistory();
  };

  const handleClearFilters = () => {
    setFilters({
      medication_name: '',
      start_date: '',
      end_date: '',
      status_filter: '',
      limit: 25
    });
    // Fetch will be triggered by useEffect when filters change
    setTimeout(fetchHistory, 100);
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'on-time':
        return '#28a745';
      case 'late':
        return '#dc3545';
      case 'early':
        return '#ffc107';
      case 'as-needed':
        return '#17a2b8';
      default:
        return '#6c757d';
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'on-time':
        return 'On Time';
      case 'late':
        return 'Late';
      case 'early':
        return 'Early';
      case 'as-needed':
        return 'As Needed';
      default:
        return 'Unknown';
    }
  };

  const formatDateTime = (dateTimeString) => {
    const date = new Date(dateTimeString);
    return date.toLocaleString();
  };

  return (
    <div style={{ background: '#fff', borderRadius: 8, padding: 24, boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}>
      <h3 style={{ margin: '0 0 24px 0', color: '#333' }}>Medication Administration History</h3>
      
      {/* Filters Section */}
      <div style={{ 
        background: '#f8f9fa', 
        borderRadius: 8, 
        padding: 16, 
        marginBottom: 24,
        border: '1px solid #dee2e6'
      }}>
        <h4 style={{ margin: '0 0 16px 0', color: '#333', fontSize: 16 }}>Filters</h4>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 16 }}>
          <div>
            <label style={{ display: 'block', marginBottom: 4, fontWeight: 600, color: '#333', fontSize: 14 }}>
              Medication Name
            </label>
            <input
              type="text"
              value={filters.medication_name}
              onChange={(e) => handleFilterChange('medication_name', e.target.value)}
              placeholder="Search by name..."
              style={{
                width: '100%',
                padding: '8px 12px',
                border: '1px solid #ddd',
                borderRadius: 4,
                fontSize: 14,
                boxSizing: 'border-box'
              }}
            />
          </div>
          
          <div>
            <label style={{ display: 'block', marginBottom: 4, fontWeight: 600, color: '#333', fontSize: 14 }}>
              Start Date
            </label>
            <input
              type="date"
              value={filters.start_date}
              onChange={(e) => handleFilterChange('start_date', e.target.value)}
              style={{
                width: '100%',
                padding: '8px 12px',
                border: '1px solid #ddd',
                borderRadius: 4,
                fontSize: 14,
                boxSizing: 'border-box'
              }}
            />
          </div>
          
          <div>
            <label style={{ display: 'block', marginBottom: 4, fontWeight: 600, color: '#333', fontSize: 14 }}>
              End Date
            </label>
            <input
              type="date"
              value={filters.end_date}
              onChange={(e) => handleFilterChange('end_date', e.target.value)}
              style={{
                width: '100%',
                padding: '8px 12px',
                border: '1px solid #ddd',
                borderRadius: 4,
                fontSize: 14,
                boxSizing: 'border-box'
              }}
            />
          </div>
          
          <div>
            <label style={{ display: 'block', marginBottom: 4, fontWeight: 600, color: '#333', fontSize: 14 }}>
              Status
            </label>
            <select
              value={filters.status_filter}
              onChange={(e) => handleFilterChange('status_filter', e.target.value)}
              style={{
                width: '100%',
                padding: '8px 12px',
                border: '1px solid #ddd',
                borderRadius: 4,
                fontSize: 14,
                boxSizing: 'border-box'
              }}
            >
              <option value="">All Statuses</option>
              <option value="on-time">On Time</option>
              <option value="late">Late</option>
              <option value="early">Early</option>
              <option value="as-needed">As Needed</option>
            </select>
          </div>
          
          <div>
            <label style={{ display: 'block', marginBottom: 4, fontWeight: 600, color: '#333', fontSize: 14 }}>
              Limit
            </label>
            <select
              value={filters.limit}
              onChange={(e) => handleFilterChange('limit', parseInt(e.target.value))}
              style={{
                width: '100%',
                padding: '8px 12px',
                border: '1px solid #ddd',
                borderRadius: 4,
                fontSize: 14,
                boxSizing: 'border-box'
              }}
            >
              <option value={10}>10 records</option>
              <option value={25}>25 records</option>
              <option value={50}>50 records</option>
              <option value={100}>100 records</option>
            </select>
          </div>
        </div>
        
        <div style={{ display: 'flex', gap: 12 }}>
          <button
            onClick={handleApplyFilters}
            disabled={loading}
            style={{
              padding: '8px 16px',
              border: 'none',
              borderRadius: 4,
              background: '#007bff',
              color: '#fff',
              fontSize: 14,
              fontWeight: 500,
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.6 : 1
            }}
          >
            {loading ? 'Loading...' : 'Apply Filters'}
          </button>
          
          <button
            onClick={handleClearFilters}
            disabled={loading}
            style={{
              padding: '8px 16px',
              border: '1px solid #6c757d',
              borderRadius: 4,
              background: '#fff',
              color: '#6c757d',
              fontSize: 14,
              fontWeight: 500,
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.6 : 1
            }}
          >
            Clear Filters
          </button>
        </div>
      </div>

      {/* Results Section */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#666' }}>
          Loading history...
        </div>
      ) : history.length === 0 ? (
        <div style={{
          textAlign: 'center',
          padding: 40,
          color: '#666',
          background: '#f8f9fa',
          borderRadius: 8,
          border: '1px solid #dee2e6'
        }}>
          <p style={{ margin: '0 0 10px 0', fontSize: 18, fontWeight: 500 }}>No administration history found</p>
          <p style={{ margin: 0 }}>Try adjusting your filters or check back later.</p>
        </div>
      ) : (
        <div>
          <div style={{ marginBottom: 16, color: '#666', fontSize: 14 }}>
            Showing {history.length} record{history.length !== 1 ? 's' : ''}
          </div>
          
          <div style={{ background: '#fff', borderRadius: 8, border: '1px solid #dee2e6', overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: '#f8f9fa' }}>
                  <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: 14, fontWeight: 600, color: '#333', borderBottom: '1px solid #dee2e6' }}>
                    Medication
                  </th>
                  <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: 14, fontWeight: 600, color: '#333', borderBottom: '1px solid #dee2e6' }}>
                    Dose
                  </th>
                  <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: 14, fontWeight: 600, color: '#333', borderBottom: '1px solid #dee2e6' }}>
                    Administered
                  </th>
                  <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: 14, fontWeight: 600, color: '#333', borderBottom: '1px solid #dee2e6' }}>
                    Scheduled
                  </th>
                  <th style={{ padding: '12px 16px', textAlign: 'center', fontSize: 14, fontWeight: 600, color: '#333', borderBottom: '1px solid #dee2e6' }}>
                    Status
                  </th>
                  <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: 14, fontWeight: 600, color: '#333', borderBottom: '1px solid #dee2e6' }}>
                    Notes
                  </th>
                </tr>
              </thead>
              <tbody>
                {history.map((record, index) => (
                  <tr key={record.id} style={{ borderBottom: index < history.length - 1 ? '1px solid #f1f3f4' : 'none' }}>
                    <td style={{ padding: '12px 16px', fontSize: 14, color: '#333' }}>
                      <div style={{ fontWeight: 600 }}>{record.medication_name}</div>
                    </td>
                    <td style={{ padding: '12px 16px', fontSize: 14, color: '#333' }}>
                      {record.dose_amount} {record.dose_unit}
                    </td>
                    <td style={{ padding: '12px 16px', fontSize: 14, color: '#333' }}>
                      {formatDateTime(record.administered_at)}
                    </td>
                    <td style={{ padding: '12px 16px', fontSize: 14, color: '#333' }}>
                      {record.scheduled_time ? formatDateTime(record.scheduled_time) : 'N/A'}
                      {record.time_difference && (
                        <div style={{ fontSize: 12, color: '#666', marginTop: 2 }}>
                          ({record.time_difference})
                        </div>
                      )}
                    </td>
                    <td style={{ padding: '12px 16px', textAlign: 'center' }}>
                      <span style={{
                        display: 'inline-block',
                        padding: '4px 8px',
                        borderRadius: 12,
                        fontSize: 12,
                        fontWeight: 600,
                        color: '#fff',
                        background: getStatusColor(record.status)
                      }}>
                        {getStatusText(record.status)}
                      </span>
                    </td>
                    <td style={{ padding: '12px 16px', fontSize: 14, color: '#333' }}>
                      {record.notes || '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Back Button */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 24 }}>
        <button
          onClick={onBack}
          style={{
            padding: '10px 24px',
            border: '2px solid #6c757d',
            borderRadius: 6,
            background: '#fff',
            color: '#6c757d',
            fontWeight: 500,
            fontSize: 14,
            cursor: 'pointer'
          }}
        >
          Back
        </button>
      </div>
    </div>
  );
};

export default MedicationHistory;
