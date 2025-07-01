import { useState, useEffect } from "react";
import "./App.css";
import ChartBlock from "./components/ChartBlock";

export default function App() {
  const [sensorValues, setSensorValues] = useState({
    spo2: null,
    bpm: null,
    perfusion: null
  });

  const [datasets, setDatasets] = useState({
    spo2: [],
    bpm: [],
    perfusion: []
  });

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/ws/sensors");

    ws.onopen = () => console.log("WebSocket connected");

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === "sensor_update" && msg.state) {
        const now = Date.now();

        setSensorValues({
          spo2: msg.state.spo2,
          bpm: msg.state.bpm,
          perfusion: msg.state.perfusion
        });

        setDatasets(prev => ({
          spo2: [...prev.spo2, { x: now, y: msg.state.spo2 }].slice(-1800),
          bpm: [...prev.bpm, { x: now, y: msg.state.bpm }].slice(-1800),
          perfusion: [...prev.perfusion, { x: now, y: msg.state.perfusion }].slice(-1800)
        }));
      }
    };

    ws.onclose = () => console.log("WebSocket disconnected");

    return () => ws.close();
  }, []);

  return (
    <div className="dashboard-container">
      <div className="values-column">
        <div className="value-display spo2">
          <h3>SpO₂</h3>
          <div className="value">{sensorValues.spo2 ?? "--"}</div>
          <div className="unit">%</div>
        </div>
        <div className="value-display bpm">
          <h3>Heart Rate</h3>
          <div className="value">{sensorValues.bpm ?? "--"}</div>
          <div className="unit">BPM</div>
        </div>
        <div className="value-display perfusion">
          <h3>Perfusion</h3>
          <div className="value">{sensorValues.perfusion ?? "--"}</div>
          <div className="unit">%</div>
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
              color="orange"
              dataset={datasets.bpm}
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
              color="green"
              dataset={datasets.perfusion}
            />
          </div>
        </div>
      </div>

      <div className="right-column">
        <div className="placeholder">Future Sensor Graph</div>
      </div>
    </div>
  );
}
