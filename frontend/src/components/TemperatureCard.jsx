import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

const TemperatureCard = ({ tempHistory = [] }) => {
  // Format data for the chart
  const validTempData = [...(tempHistory || [])]
    .filter(temp => 
      (temp.skin !== null && temp.skin !== 0) || 
      (temp.body !== null && temp.body !== 0)
    )
    .slice(-5) // Only take last 5 entries
    .map((temp, index) => ({
      index,
      body: temp.body,
      skin: temp.skin
    }));

  const sortedTempHistory = [...(tempHistory || [])]
    .filter(temp =>
      (temp.skin !== null && temp.skin !== 0) ||
      (temp.body !== null && temp.body !== 0)
    )
    .sort((a, b) => {
      if (!a.datetime) return 1;
      if (!b.datetime) return -1;
      return new Date(a.datetime) - new Date(b.datetime); // Changed to oldest first
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

  const formatTemp = (temp) => {
    if (temp === null || temp === undefined) return "--";
    return temp.toFixed(1);
  };

  // Calculate Y domain based on actual temperature values
  const calculateYDomain = () => {
    if (validTempData.length === 0) return [90, 105]; // Default range for temps (°F)
    
    const allTemps = [];
    validTempData.forEach(d => {
      if (d.body !== null && d.body !== undefined) allTemps.push(d.body);
      if (d.skin !== null && d.skin !== undefined) allTemps.push(d.skin);
    });
    
    if (allTemps.length === 0) return [90, 105];
    
    let min = Math.min(...allTemps);
    let max = Math.max(...allTemps);
    
    // Add padding (5% for temperature since values are usually in narrow range)
    const padding = (max - min) * 0.05;
    min = Math.max(min - padding, 80); // Don't go below reasonable temp
    max = Math.min(max + padding, 110); // Don't go above reasonable temp
    
    return [min, max];
  };

  return (
    <div className="temp-card">
      <h3 className="temp-title">Temperature History</h3>

      <div className="temp-content">
        {/* Chart section - 40% height */}
        <div className="temp-chart-container">
          {validTempData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={validTempData} margin={{ top: 10, right: 5, bottom: 30, left: 5 }}>
                <XAxis 
                  dataKey="index" 
                  hide 
                />
                <YAxis 
                  domain={calculateYDomain()}
                  axisLine={false} 
                  tickLine={false}
                  tick={false}
                />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#161e2e', border: '1px solid #333', borderRadius: '4px' }}
                  itemStyle={{ color: '#fff' }}
                  formatter={(value, name) => [
                    `${value.toFixed(1)}°F`, 
                    name === 'body' ? 'Body Temp' : 'Skin Temp'
                  ]}
                />
                <Line 
                  type="monotone" 
                  dataKey="body" 
                  stroke="#9c56b8" // Purple for body temp
                  dot={{ fill: '#9c56b8', r: 4 }}
                  strokeWidth={2}
                  activeDot={{ fill: '#9c56b8', stroke: '#fff', strokeWidth: 2, r: 6 }}
                  isAnimationActive={false}
                  name="Body" // Set proper name for tooltip
                />
                <Line 
                  type="monotone" 
                  dataKey="skin" 
                  stroke="#ffd54f" // Yellow for skin temp
                  dot={{ fill: '#ffd54f', r: 4 }}
                  strokeWidth={2}
                  activeDot={{ fill: '#ffd54f', stroke: '#fff', strokeWidth: 2, r: 6 }}
                  isAnimationActive={false}
                  name="Skin" // Set proper name for tooltip
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="no-data">No temperature data available</div>
          )}
          
          {/* Updated legend styling for better positioning */}
          <div className="temp-legend">
            <div className="legend-item">
              <div className="legend-color" style={{ backgroundColor: "#9c56b8" }}></div>
              <div className="legend-label">Body</div>
            </div>
            <div className="legend-item">
              <div className="legend-color" style={{ backgroundColor: "#ffd54f" }}></div>
              <div className="legend-label">Skin</div>
            </div>
          </div>
        </div>

        {/* Table section - 60% height */}
        <div className="temp-table-container">
          <table className="temp-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Body °F</th>
                <th>Skin °F</th>
              </tr>
            </thead>
            <tbody>
              {sortedTempHistory.length > 0 ? (
                sortedTempHistory.map((temp, index) => (
                  <tr key={index}>
                    <td>{formatDateTime(temp.datetime)}</td>
                    <td className="body-temp">{formatTemp(temp.body)}</td>
                    <td className="skin-temp">{formatTemp(temp.skin)}</td>
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
    </div>
  );
};

export default TemperatureCard;