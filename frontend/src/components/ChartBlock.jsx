import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

export default function ChartBlock({ title, yLabel, color, dataset, showXaxis = true, showYaxis = true }) {
  return (
    <div style={{ width: "100%", height: "100%", position: "relative" }}>
      <div style={{
        position: "absolute",
        top: 5,
        left: 10,
        color: "#FFF",
        zIndex: 1
      }}>
        {title}
      </div>

      {dataset.length === 0 ? (
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100%',
          color: '#999'
        }}>
          Waiting for data...
        </div>
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={dataset}>
            {showXaxis && (
              <XAxis
                dataKey="x"
                type="number"
                domain={['dataMin', 'dataMax']}
                tickFormatter={(unixTime) => {
                  const d = new Date(unixTime);
                  return `${d.getHours()}:${d.getMinutes()}:${d.getSeconds()}`;
                }}
              />
            )}
            {showYaxis && <YAxis label={{ value: yLabel, angle: -90, position: 'insideLeft' }} />}
            <CartesianGrid strokeDasharray="3 3" />
            <Tooltip labelFormatter={(unixTime) => new Date(unixTime).toLocaleTimeString()} />
            <Line type="monotone" dataKey="y" stroke={color} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
