import { SciChartReact } from "scichart-react";
import {
  SciChartSurface,
  NumericAxis,
  FastLineRenderableSeries,
  XyDataSeries,
  SciChartDefaults,
  SciChartJsNavyTheme,
  NumberRange
} from "scichart";
import "./App.css";
import ChartBlock from "./components/ChartBlock";
import { useState, createContext } from "react";

// Create context to share latest values across components
export const SensorContext = createContext({});

SciChartDefaults.wasmUrl = "/scichart2d.wasm";
SciChartDefaults.dataUrl = "/scichart2d.data";
SciChartSurface.UseCommunityLicense();

export default function App() {
  // State to store latest sensor values
  const [sensorValues, setSensorValues] = useState({
    spo2: null,
    bpm: null,
    perfusion: null
  });

  // Function to update sensor values from chart components
  const updateSensorValue = (sensor, value) => {
    setSensorValues(prev => ({
      ...prev,
      [sensor]: value
    }));
  };

  return (
    <SensorContext.Provider value={{ sensorValues, updateSensorValue }}>
      <div className="dashboard-container">
        {/* Left column - Latest Values Display */}
        <div className="values-column">
          <div className="value-display spo2">
            <h3>SpO₂</h3>
            <div className="value">{sensorValues.spo2 !== null ? sensorValues.spo2 : "--"}</div>
            <div className="unit">%</div>
          </div>
          
          <div className="value-display bpm">
            <h3>Heart Rate</h3>
            <div className="value">{sensorValues.bpm !== null ? sensorValues.bpm : "--"}</div>
            <div className="unit">BPM</div>
          </div>
          
          <div className="value-display perfusion">
            <h3>Perfusion</h3>
            <div className="value">{sensorValues.perfusion !== null ? sensorValues.perfusion : "--"}</div>
            <div className="unit">%</div>
          </div>
        </div>

        {/* Center column - Charts */}
        <div className="charts-column">
          <div className="chart-block">
            <div className="chart-inner">
              <ChartBlock
                  title="SpO₂ Monitor"
                  topic="shh/spo2/state"
                  yLabel="SpO₂ (%)"
                  yMin={70}
                  yMax={100}
                  color="steelblue"
                  sensorKey="spo2"
                  xDisplay={false} // Hide x-axis on this chart
              />
            </div>
          </div>

          <div className="chart-block">
            <div className="chart-inner">
              <ChartBlock
                  title="BPM Monitor"
                  topic="shh/bpm/state"
                  yLabel="BPM"
                  yMin={40}
                  yMax={160}
                  color="orange"
                  sensorKey="bpm"
                  xDisplay={false} // Hide x-axis on this chart
              />
            </div>
          </div>

          <div className="chart-block">
            <div className="chart-inner">
              <ChartBlock
                  title="Perfusion Monitor"
                  topic="shh/perfusion/state"
                  yLabel="PAI (%)"
                  yMin={40}
                  yMax={160}
                  color="green"
                  sensorKey="perfusion"
                  xDisplay={true} // Show x-axis only on bottom chart
              />
            </div>
          </div>
        </div>

        {/* Right column - Future Sensor Graph */}
        <div className="right-column">
          <div className="placeholder">Future Sensor Graph</div>
        </div>
      </div>
    </SensorContext.Provider>
  );
}
