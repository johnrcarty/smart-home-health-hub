import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

const BloodPressureCard = ({ bpHistory = [] }) => {
  // Sort and filter valid MAP data for the chart
  const validBpData = [...(bpHistory || [])]
    .filter(bp => bp.map !== null && bp.map !== undefined && bp.map !== 0)
    .slice(-5) // Only take last 5 entries
    .map((bp, index) => ({
      index,
      map: bp.map
    }));

  const sortedBpHistory = [...(bpHistory || [])]
    .filter(bp =>
      (bp.systolic !== null && bp.systolic !== 0) ||
      (bp.diastolic !== null && bp.diastolic !== 0) ||
      (bp.map !== null && bp.map !== 0)
    )
    .sort((a, b) => {
      if (!a.datetime) return 1;
      if (!b.datetime) return -1;
      return new Date(b.datetime) - new Date(a.datetime);
    })
    .slice(0, 5);

  const formatDateTime = (dateTimeStr) => {
    if (!dateTimeStr) return "Unknown";
    try {
      const date = new Date(dateTimeStr);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: true });
    } catch {
      return "Invalid Date";
    }
  };

  return (
    <div className="bp-card">
      <h3 className="bp-title">Blood Pressure History</h3>

      {/* Chart section */}
      <div className="bp-chart" style={{ height: "90px", width: "100%" }}>
        {validBpData.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={validBpData}>
              <XAxis dataKey="index" hide />
              <YAxis domain={['auto', 'auto']} />
              <Tooltip />
              <Line type="monotone" dataKey="map" stroke="#9c56b8" dot />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="no-data">No BP data available</div>
        )}
      </div>

      {/* Table section */}
      <div className="bp-table-container">
        <table className="bp-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Sys/Dia</th>
              <th>MAP</th>
            </tr>
          </thead>
          <tbody>
            {sortedBpHistory.length > 0 ? (
              sortedBpHistory.map((bp, index) => (
                <tr key={index}>
                  <td>{formatDateTime(bp.datetime)}</td>
                  <td>
                    {bp.systolic !== null && bp.diastolic !== null
                      ? `${bp.systolic}/${bp.diastolic}`
                      : '--/--'}
                  </td>
                  <td>{bp.map !== null ? bp.map : '--'}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={3} className="no-data-row">No data available</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default BloodPressureCard;
