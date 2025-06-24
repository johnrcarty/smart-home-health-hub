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

SciChartDefaults.wasmUrl = "/scichart2d.wasm";
SciChartDefaults.dataUrl = "/scichart2d.data";
SciChartSurface.UseCommunityLicense();

export default function App() {
  return (
    <div className="dashboard-container">
      <div className="left-column">
              <div className="chart-block">
                <div className="chart-inner">
                  <ChartBlock
                      title="SpO₂ Monitor"
                      topic="shh/spo2/state"
                      yLabel="SpO₂ (%)"
                      yMin={70}
                      yMax={100}
                      color="steelblue"
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
