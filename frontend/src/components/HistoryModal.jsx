import React, { useEffect, useState } from "react";
import config from '../config';

const API_BASE = "/api/vitals";

const HistoryModal = ({ onClose }) => {
  const [vitalTypes, setVitalTypes] = useState([]);
  const [selectedType, setSelectedType] = useState(null);
  const [records, setRecords] = useState([]);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/types`)
      .then((res) => res.json())
      .then((data) => setVitalTypes(data))
      .catch(() => setVitalTypes([]));
  }, []);

  useEffect(() => {
    if (selectedType) {
      setLoading(true);
      fetch(`${API_BASE}/history?vital_type=${selectedType}&page=${page}&page_size=${pageSize}`)
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

  return (
    <div className="history-modal">
      <div className="modal-header">
        <h2>Vital History</h2>
        <button onClick={onClose}>Close</button>
      </div>
      <div className="modal-body">
        <div className="vital-type-buttons">
          {vitalTypes.map((type) => (
            <button
              key={type}
              className={type === selectedType ? "active" : ""}
              onClick={() => handleTypeSelect(type)}
            >
              {type}
            </button>
          ))}
        </div>
        {selectedType && (
          <>
            <div className="chart-placeholder" style={{ height: 200, background: "#f0f0f0", margin: "20px 0" }}>
              <p style={{ textAlign: "center", paddingTop: 80 }}>
                Chart for <b>{selectedType}</b> (coming soon)
              </p>
            </div>
            <div className="history-table">
              {loading ? (
                <p>Loading...</p>
              ) : (
                <table>
                  <thead>
                    <tr>
                      <th>Timestamp</th>
                      <th>Value</th>
                      <th>Notes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {records.length === 0 ? (
                      <tr>
                        <td colSpan={3} style={{ textAlign: "center" }}>No data</td>
                      </tr>
                    ) : (
                      records.map((rec, idx) => (
                        <tr key={idx}>
                          <td>{rec.datetime}</td>
                          <td>{rec.value}</td>
                          <td>{rec.notes || ""}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              )}
              <div className="pagination-controls" style={{ marginTop: 10 }}>
                <button onClick={handlePrev} disabled={page === 1}>Prev</button>
                <span style={{ margin: "0 10px" }}>Page {page} of {totalPages}</span>
                <button onClick={handleNext} disabled={page === totalPages}>Next</button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default HistoryModal;
