import { useState, useEffect, useRef } from "react";
import "./App.css";
import ChartBlock from "./components/ChartBlock";
import ClockCard from "./components/ClockCard";
import BloodPressureCard from "./components/BloodPressureCard";

export default function App() {
  const [sensorValues, setSensorValues] = useState({
    spo2: null,
    bpm: null,
    perfusion: null,
    skin_temp: null,
    body_temp: null
  });

  const [datasets, setDatasets] = useState({
    spo2: [],
    bpm: [],
    perfusion: []
  });

  const [bpHistory, setBpHistory] = useState([]);
  const [tempHistory, setTempHistory] = useState([]);

  // Move this useRef outside the useEffect hook
  const initialDataReceived = useRef(false);

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/ws/sensors");

    ws.onopen = () => console.log("WebSocket connected");

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === "sensor_update" && msg.state) {
        const now = Date.now();

        // Set regular sensor values
        setSensorValues({
          spo2: msg.state.spo2,
          bpm: msg.state.bpm,
          perfusion: msg.state.perfusion,
          skin_temp: msg.state.skin_temp,
          body_temp: msg.state.body_temp
        });

        // Handle blood pressure history with filtering of all-zero values
        if (msg.state.bp) {
          // Format BP data for charts with null/zero checks
          const bpData = msg.state.bp
            .filter(reading => 
              (reading.systolic_bp !== null && reading.systolic_bp !== 0) || 
              (reading.diastolic_bp !== null && reading.diastolic_bp !== 0) || 
              (reading.map_bp !== null && reading.map_bp !== 0)
            )
            .map(reading => ({
              datetime: reading.datetime || Date.now().toString(),
              systolic: reading.systolic_bp,
              diastolic: reading.diastolic_bp,
              map: reading.map_bp
            }));
          
          setBpHistory(bpData);
        }

        // Handle temperature history with filtering of all-zero values
        if (msg.state.temp) {
          // Format temperature data for charts with null/zero checks
          const tempData = msg.state.temp
            .filter(reading => 
              (reading.skin_temp !== null && reading.skin_temp !== 0) || 
              (reading.body_temp !== null && reading.body_temp !== 0)
            )
            .map(reading => ({
              datetime: reading.datetime || Date.now().toString(),
              skin: reading.skin_temp,
              body: reading.body_temp
            }));
          
          setTempHistory(tempData);
        }

        // Update regular charts data with null checks
        setDatasets(prev => {
          // Only update data points if the values are not null
          const newState = { ...prev };
          
          // Track if this is the first meaningful update
          let hasValidUpdate = false;
          
          // Update SpO2 if value exists
          if (msg.state.spo2 !== null && msg.state.spo2 !== undefined) {
            newState.spo2 = [...prev.spo2, { x: now, y: msg.state.spo2 }].slice(-1800);
            hasValidUpdate = true;
          }
          
          // Update BPM if value exists
          if (msg.state.bpm !== null && msg.state.bpm !== undefined) {
            newState.bpm = [...prev.bpm, { x: now, y: msg.state.bpm }].slice(-1800);
            hasValidUpdate = true;
          }
          
          // Update perfusion if value exists
          if (msg.state.perfusion !== null && msg.state.perfusion !== undefined) {
            newState.perfusion = [...prev.perfusion, { x: now, y: msg.state.perfusion }].slice(-1800);
            hasValidUpdate = true;
          }
          
          // If this is our first valid data update, reset BP graph
          if (hasValidUpdate && !initialDataReceived.current) {
            initialDataReceived.current = true;
            // Reset BP chart when we first get data
            setBpHistory(prev => [...prev]); // Trigger re-render
            setTempHistory(prev => [...prev]); // Trigger re-render
          }
          
          return newState;
        });
      }
    };

    ws.onclose = () => console.log("WebSocket disconnected");

    return () => ws.close();
  }, []);

  const calculateAvg = (data) => {
    if (data.length === 0) return 0;
    return data.reduce((sum, item) => sum + item.y, 0) / data.length;
  };

  const calculateMin = (data) => {
    if (data.length === 0) return 0;
    return Math.min(...data.map(item => item.y));
  };

  const calculateMax = (data) => {
    if (data.length === 0) return 0;
    return Math.max(...data.map(item => item.y));
  };

  return (
    <div className="dashboard-container">
      <div className="values-column">
        <div className="value-display spo2">
          <h3 className="value-title">SpO₂</h3>
          <div className="value-content">
            <div className="value">{sensorValues.spo2 ?? "--"}</div>
            <div className="unit">%</div>
          </div>
          <div className="value-stats">
            {datasets.spo2.length > 0 ? (
              <>
                <span>
                  Avg: {calculateAvg(datasets.spo2.filter(item => item.y !== 0)).toFixed(1)}%
                </span>
                <span>
                  Min: {calculateMin(datasets.spo2.filter(item => item.y !== 0)).toFixed(0)}%
                </span>
                <span>
                  Max: {calculateMax(datasets.spo2.filter(item => item.y !== 0)).toFixed(0)}%
                </span>
              </>
            ) : (
              <span>No data available</span>
            )}
          </div>
        </div>
        
        <div className="value-display bpm">
          <h3 className="value-title">Heart Rate</h3>
          <div className="value-content">
            <div className="value">{sensorValues.bpm ?? "--"}</div>
            <div className="unit">BPM</div>
          </div>
          <div className="value-stats">
            {datasets.bpm.length > 0 ? (
              <>
                <span>
                  Avg: {calculateAvg(datasets.bpm.filter(item => item.y !== 0)).toFixed(0)}
                </span>
                <span>
                  Min: {calculateMin(datasets.bpm.filter(item => item.y !== 0)).toFixed(0)}
                </span>
                <span>
                  Max: {calculateMax(datasets.bpm.filter(item => item.y !== 0)).toFixed(0)}
                </span>
              </>
            ) : (
              <span>No data available</span>
            )}
          </div>
        </div>
        
        <div className="value-display perfusion">
          <h3 className="value-title">Perfusion</h3>
          <div className="value-content">
            <div className="value">{sensorValues.perfusion ?? "--"}</div>
            <div className="unit">%</div>
          </div>
          <div className="value-stats">
            {datasets.perfusion.length > 0 ? (
              <>
                <span>
                  Avg: {calculateAvg(datasets.perfusion.filter(item => item.y !== 0)).toFixed(1)}
                </span>
                <span>
                  Min: {calculateMin(datasets.perfusion.filter(item => item.y !== 0)).toFixed(1)}
                </span>
                <span>
                  Max: {calculateMax(datasets.perfusion.filter(item => item.y !== 0)).toFixed(1)}
                </span>
              </>
            ) : (
              <span>No data available</span>
            )}
          </div>
        </div>
      </div>

      <div className="charts-column">
        <div className="chart-block">
          <div className="chart-inner">
            <ChartBlock
              title="SpO₂ Monitor"
              yLabel="SpO2"
              yMin={40}
              yMax={100}
              color="blue"
              dataset={datasets.spo2}
              showXaxis={false}
              showYaxis={true}
            />
          </div>
        </div>

        <div className="chart-block">
          <div className="chart-inner">
            <ChartBlock
              title="BPM"
              yLabel="BPM"
              yMin={40}
              yMax={160}
              color="green"
              dataset={datasets.bpm}
              showXaxis={false}
              showYaxis={true}
            />
          </div>
        </div>

        <div className="chart-block">
          <div className="chart-inner">
            <ChartBlock
              title="Perfusion Monitor"
              yLabel="PAI (%)"
              yMin={40}
              yMax={160}
              color="orange"
              dataset={datasets.perfusion}
              showXaxis={true}
              showYaxis={true}
            />
          </div>
        </div>
      </div>

      <div className="right-column">
        <div style={{ height: "10%", marginBottom: "10px" }}>
          <ClockCard />
        </div>
        
        <div style={{ height: "30%", marginBottom: "10px" }}>
          <BloodPressureCard bpHistory={bpHistory} />
        </div>

        <div style={{ height: "60%", backgroundColor: "#1a2b42", borderRadius: "8px" }}>
          <div style={{
            width: "100%", 
            height: "100%",
            color: "#ccc",
            display: "flex",
            justifyContent: "center",
            alignItems: "center"
          }}>
            Future Placeholder
          </div>
        </div>
      </div>
    </div>
  );
}
