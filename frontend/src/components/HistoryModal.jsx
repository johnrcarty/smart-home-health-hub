import React, { useEffect, useState } from "react";
import config from '../config';

const HistoryModal = ({ onClose }) => {
  const [vitalTypes, setVitalTypes] = useState([]);
  const [selectedType, setSelectedType] = useState(null);
  const [records, setRecords] = useState([]);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch(`${config.apiUrl}/api/vitals/types`)
      .then((res) => res.json())
      .then((data) => setVitalTypes(data))
      .catch(() => setVitalTypes([]));
  }, []);

  useEffect(() => {
    if (selectedType) {
      setLoading(true);
      fetch(`${config.apiUrl}/api/vitals/history?vital_type=${selectedType}&page=${page}&page_size=${pageSize}`)
        .then((res) => res.json())
        .then((data) => {
          setRecords(data.records || []);
          setTotalPages(data.total_pages || 1);
          setLoading(false);
        })
        .catch(() => {
          setRecords([]);
          setTotalPages(1);
          setLoading(false);
        });
    }
  }, [selectedType, page, pageSize]);

  const handleTypeSelect = (type) => {
    setSelectedType(type);
    setPage(1);
  };

  const handlePrev = () => {
    if (page > 1) setPage(page - 1);
  };
  const handleNext = () => {
    if (page < totalPages) setPage(page + 1);
  };

  // Bathroom size mapping for display
  const getBathroomSizeDisplay = (value, vitalGroup) => {
    if (vitalGroup === 'bathroom' && value !== null && value !== undefined) {
      const sizeMap = {
        0: 'Smear',
        1: 'Small',
        2: 'Medium', 
        3: 'Large',
        4: 'Extra Large'
      };
      return sizeMap[value] || value;
    }
    return value;
  };

  // Group display formatting
  const getGroupDisplay = (vitalGroup) => {
    if (!vitalGroup) return '-';
    return vitalGroup.charAt(0).toUpperCase() + vitalGroup.slice(1);
  };

  return (
    <div className="history-modal">
      <div className="modal-body">
        <div className="vital-type-buttons" style={{ 
          display: 'flex', 
          gap: '10px', 
          marginBottom: '20px',
          flexWrap: 'wrap'
        }}>
          {vitalTypes.map((type) => (
            <button
              key={type}
              className={type === selectedType ? "active" : ""}
              onClick={() => handleTypeSelect(type)}
              style={{
                padding: '8px 16px',
                border: '1px solid #ccc',
                borderRadius: '4px',
                backgroundColor: type === selectedType ? '#007bff' : '#f8f9fa',
                color: type === selectedType ? '#fff' : '#333',
                cursor: 'pointer',
                textTransform: 'capitalize'
              }}
            >
              {type}
            </button>
          ))}
        </div>
        {selectedType && (
          <>
            <div className="chart-placeholder" style={{ 
              height: 200, 
              background: "#f0f0f0", 
              margin: "20px 0",
              border: "2px dashed #ccc",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              borderRadius: "4px"
            }}>
              <p style={{ textAlign: "center", color: "#666", margin: 0 }}>
                Chart for <b>{selectedType}</b> (coming soon)
              </p>
            </div>
            <div className="history-table">
              {loading ? (
                <div style={{ 
                  textAlign: 'center', 
                  padding: '40px',
                  color: '#007bff' 
                }}>
                  <div style={{ fontSize: '16px' }}>Loading...</div>
                </div>
              ) : (
                <div style={{
                  backgroundColor: '#fff',
                  borderRadius: '8px',
                  overflow: 'hidden',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
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
                          Timestamp
                        </th>
                        <th style={{ 
                          padding: '16px', 
                          color: '#fff', 
                          textAlign: 'left',
                          fontWeight: '600',
                          fontSize: '14px'
                        }}>
                          Value
                        </th>
                        <th style={{ 
                          padding: '16px', 
                          color: '#fff', 
                          textAlign: 'left',
                          fontWeight: '600',
                          fontSize: '14px'
                        }}>
                          Group
                        </th>
                        <th style={{ 
                          padding: '16px', 
                          color: '#fff', 
                          textAlign: 'left',
                          fontWeight: '600',
                          fontSize: '14px'
                        }}>
                          Notes
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {records.length === 0 ? (
                        <tr>
                          <td colSpan={4} style={{ 
                            textAlign: "center", 
                            padding: '40px',
                            color: '#666',
                            backgroundColor: '#f8f9fa',
                            fontStyle: 'italic'
                          }}>
                            No data available for {selectedType}
                          </td>
                        </tr>
                      ) : (
                        records.map((rec, idx) => (
                          <tr 
                            key={idx} 
                            style={{ 
                              backgroundColor: idx % 2 === 0 ? '#fff' : '#f8f9fa',
                              borderBottom: '1px solid #e9ecef'
                            }}
                          >
                            <td style={{ 
                              padding: '12px 16px', 
                              color: '#333',
                              fontSize: '14px'
                            }}>
                              {new Date(rec.datetime).toLocaleString()}
                            </td>
                            <td style={{ 
                              padding: '12px 16px', 
                              color: '#333',
                              fontSize: '14px',
                              fontWeight: '500'
                            }}>
                              {getBathroomSizeDisplay(rec.value, rec.vital_group)}
                            </td>
                            <td style={{ 
                              padding: '12px 16px', 
                              color: '#666',
                              fontSize: '14px'
                            }}>
                              {getGroupDisplay(rec.vital_group)}
                            </td>
                            <td style={{ 
                              padding: '12px 16px', 
                              color: '#666',
                              fontSize: '14px',
                              fontStyle: rec.notes ? 'normal' : 'italic'
                            }}>
                              {rec.notes || "No notes"}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              )}
              <div className="pagination-controls" style={{ 
                marginTop: 20,
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                gap: '12px',
                padding: '16px',
                backgroundColor: '#fff',
                borderRadius: '8px',
                boxShadow: '0 1px 4px rgba(0,0,0,0.1)'
              }}>
                <button 
                  onClick={handlePrev} 
                  disabled={page === 1}
                  style={{
                    padding: '8px 16px',
                    border: 'none',
                    borderRadius: '6px',
                    backgroundColor: page === 1 ? '#e9ecef' : '#007bff',
                    color: page === 1 ? '#6c757d' : '#fff',
                    cursor: page === 1 ? 'not-allowed' : 'pointer',
                    fontWeight: '500',
                    fontSize: '14px',
                    transition: 'all 0.2s ease'
                  }}
                >
                  ← Previous
                </button>
                <span style={{ 
                  margin: "0 16px", 
                  fontWeight: '600',
                  color: '#333',
                  fontSize: '14px'
                }}>
                  Page {page} of {totalPages}
                </span>
                <button 
                  onClick={handleNext} 
                  disabled={page === totalPages}
                  style={{
                    padding: '8px 16px',
                    border: 'none',
                    borderRadius: '6px',
                    backgroundColor: page === totalPages ? '#e9ecef' : '#007bff',
                    color: page === totalPages ? '#6c757d' : '#fff',
                    cursor: page === totalPages ? 'not-allowed' : 'pointer',
                    fontWeight: '500',
                    fontSize: '14px',
                    transition: 'all 0.2s ease'
                  }}
                >
                  Next →
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default HistoryModal;
