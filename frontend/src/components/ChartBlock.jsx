import { SciChartReact } from "scichart-react";
import {
  SciChartSurface,
  NumericAxis,
  FastLineRenderableSeries,
  XyDataSeries,
  SciChartJsNavyTheme,
  NumberRange,
  EAutoRange,
  TextLabelProvider,
  EAxisAlignment
} from "scichart";
import { useEffect, useState, useRef } from "react";

// Create custom time formatter for the X axis that uses local time
class TimeFormatterLabelProvider extends TextLabelProvider {
  constructor(wasmContext) {
    super(wasmContext);
  }

  formatLabel(dataValue) {
    const date = new Date(dataValue);
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    const seconds = date.getSeconds().toString().padStart(2, '0');
    return `${hours}:${minutes}:${seconds}`;
  }

  formatCursorLabel(dataValue) {
    return this.formatLabel(dataValue);
  }
}

// Create a shared management object for synchronizing charts
const chartSync = {
  axes: [],
  isInitializing: false,
  lastVisibleRange: new NumberRange(Date.now() - 2 * 60 * 1000, Date.now()),
  
  // Add an axis to the sync group after it's fully initialized
  registerAxis(axis) {
    if (!axis) return;
    
    // Store the axis reference
    this.axes.push(axis);
    console.log(`Registered axis, total: ${this.axes.length}`);
    
    // Set the initial visible range
    axis.visibleRange = this.lastVisibleRange;
    
    // Only attempt binding when we have multiple axes
    if (this.axes.length > 1 && !this.isInitializing) {
      this.synchronizeAxes();
    }
  },
  
  // Remove an axis from the sync group
  unregisterAxis(axis) {
    const index = this.axes.indexOf(axis);
    if (index > -1) {
      this.axes.splice(index, 1);
      console.log(`Unregistered axis, remaining: ${this.axes.length}`);
    }
  },
  
  // Update all axes with a new visible range
  updateVisibleRange(newRange) {
    if (!newRange) return;
    
    this.lastVisibleRange = newRange;
    console.log(`Updating visible range: ${newRange.min} - ${newRange.max}`);
    
    // Update all registered axes
    for (const axis of this.axes) {
      try {
        axis.visibleRange = newRange;
      } catch (e) {
        console.error("Error updating axis:", e);
      }
    }
  },
  
  // Set up mutual visibility binding between all axes
  synchronizeAxes() {
    if (this.axes.length <= 1) return;
    
    this.isInitializing = true;
    console.log("Setting up axis synchronization");
    
    try {
      // First, ensure all axes have the same visible range
      for (const axis of this.axes) {
        axis.visibleRange = this.lastVisibleRange;
      }
      
      // Then set up the scroll/zoom synchronization
      const mainAxis = this.axes[0];
      
      mainAxis.visibleRangeChanged.subscribe((args) => {
        this.lastVisibleRange = args.visibleRange;
        
        for (let i = 1; i < this.axes.length; i++) {
          try {
            this.axes[i].visibleRange = this.lastVisibleRange;
          } catch (e) {
            console.error("Error during sync:", e);
          }
        }
      });
    } catch (e) {
      console.error("Error during axis synchronization:", e);
    }
    
    this.isInitializing = false;
  }
};

export default function ChartBlock({ title, topic, yLabel, yMin, yMax, color }) {
  const [isLoading, setIsLoading] = useState(true);
  const [hasData, setHasData] = useState(false);
  const [chartError, setChartError] = useState(null);
  const dataSeries = useRef(null);
  // at top of component, compute once:
  const sensorKey = topic.split('/')[1]; // “spo2”, “bpm”, etc.

  
  // Add debug logging to track data
  const [dataStats, setDataStats] = useState({ min: null, max: null, count: 0 });

  // Simplified chart initialization focused on reliability
  const initSciChart = (rootElement) =>
    new Promise(async (resolve) => {
      try {
        console.log(`Initializing chart for ${topic}`);
        
        // Create the chart surface with basic theme
        const { sciChartSurface, wasmContext } = await SciChartSurface.create(rootElement, {
          theme: new SciChartJsNavyTheme(),
          title: "",  // We'll handle title outside the chart
          titleStyle: { fontSize: 0 }
        });

        // Create X axis with custom time formatter
        const xAxis = new NumericAxis(wasmContext, {
          axisTitle: "",  // Empty title as we want only time labels
          autoRange: EAutoRange.Never, // We'll control the range manually
          labelProvider: new TimeFormatterLabelProvider(wasmContext),
          drawMajorGridLines: true,
          drawMinorGridLines: false,
          majorTickLineStyle: { color: "#FFFFFF22" },
          axisTitleStyle: { color: "#FFFFFF" },
          labelStyle: { color: "#FFFFFF" }
        });
        
        sciChartSurface.xAxes.add(xAxis);
        console.log(`X axis created for ${topic}`);
        
        // Simple Y axis with minimal configuration
        const yAxis = new NumericAxis(wasmContext, {
          axisTitle: yLabel,
          axisAlignment: EAxisAlignment.Left,
          visibleRange: new NumberRange(yMin, yMax),
          drawMajorGridLines: true,
          drawMinorGridLines: false,
          majorTickLineStyle: { color: "#FFFFFF22" },
          axisTitleStyle: { color: "#FFFFFF" },
          labelStyle: { color: "#FFFFFF" },
          autoRange: EAutoRange.Always,       // <= auto-scale to your data
          growBy: new NumberRange(0.1, 0.1)   // optional padding
        });
        
        sciChartSurface.yAxes.add(yAxis);

        // Create data series with some initial points
        const seriesObj = new XyDataSeries(wasmContext, { dataSeriesName: yLabel });
        dataSeries.current = seriesObj;
        
        // Add some initial data points to ensure rendering starts
        const initialTime = Date.now();
        const midValue = yMin + (yMax - yMin) / 2;
        
        for (let i = 0; i < 5; i++) {
          seriesObj.append(initialTime - (5-i) * 1000, midValue);
        }
        console.log(`Added initial data points for ${topic}, time: ${initialTime}`);
        
        // Create the line series
        const lineSeries = new FastLineRenderableSeries(wasmContext, {
          stroke: color,
          strokeThickness: 3,
          dataSeries: seriesObj
        });
        
        sciChartSurface.renderableSeries.add(lineSeries);
        console.log(`Added line series for ${topic}`);

        // Set the initial visible range to show last 2 minutes
        const twoMinutesAgo = initialTime - 2 * 60 * 1000;
        xAxis.visibleRange = new NumberRange(twoMinutesAgo, initialTime);
        console.log(`Set initial visible range: ${twoMinutesAgo} - ${initialTime}`);

        // Force a redraw
        sciChartSurface.invalidateElement();
        
        // Register with the synchronized chart system
        chartSync.registerAxis(xAxis);
        
        // Set up WebSocket with minimal handling
        const ws = new WebSocket("ws://127.0.0.1:8000/ws/sensors");
        
        ws.onopen = () => {
          console.log(`WebSocket open for ${topic}`);
          setIsLoading(false);
        };
        
        ws.onerror = (e) => {
          console.error(`WebSocket error for ${topic}:`, e);
          setIsLoading(false);
        };
/*
        ws.onmessage = (msg) => {
          try {
            const data = JSON.parse(msg.data);
            if (data.topic === topic) {
              const payload = JSON.parse(data.payload);
              const value = Object.values(payload)[0];
              const currentTime = Date.now();
              
              console.log(`${topic}: Received value ${value} at time ${currentTime}`);
              
              // Add the data point to the series
              seriesObj.append(currentTime, value);
              setHasData(true);
              
              // Update debug stats
              setDataStats(prev => ({
                min: prev.min === null ? value : Math.min(prev.min, value),
                max: prev.max === null ? value : Math.max(prev.max, value),
                count: prev.count + 1
              }));
              
              // Keep only the latest 300 points (5 minutes at 1Hz)
              if (seriesObj.count() > 300) {
                seriesObj.removeRange(0, seriesObj.count() - 300);
              }
              
              // Get data range
              const dataMin = seriesObj.count() > 0 ? seriesObj.xValues.get(0) : currentTime - 2 * 60 * 1000;
              const dataMax = currentTime;
              
              // Update the visible range to include new data and show last 2 minutes
              const twoMinutesAgo = Math.min(currentTime - 2 * 60 * 1000, dataMin);
              const newRange = new NumberRange(twoMinutesAgo, currentTime);
              console.log(`${topic}: Updating range to ${twoMinutesAgo} - ${currentTime}`);
              
              // Update all synchronized charts with this range
              chartSync.updateVisibleRange(newRange);
            }
          } catch (error) {
            console.error(`Error processing message for ${topic}:`, error);
          }
        };
*/
        ws.onmessage = (evt) => {
          try {
            const msg = JSON.parse(evt.data);

            // 1️⃣ Only handle our unified updates
            if (msg.type !== "sensor_update" || !msg.state) return;

            // 2️⃣ Grab the raw JSON payload for *this* sensor
            const raw = msg.state[sensorKey];
            if (raw == null) return; // no update yet

            // 3️⃣ Parse the value
            const obj = JSON.parse(raw);             // → { "spo2": 99 }
            const value = Object.values(obj)[0];     // → 99

            // 4️⃣ Append to your series
            const now = Date.now();
            dataSeries.current.append(now, value);

            // 5️⃣ Trim history and advance the window
            if (dataSeries.current.count() > 300) {
              dataSeries.current.removeRange(0, dataSeries.current.count() - 300);
            }

            const twoMinAgo = now - 2 * 60 * 1000;
            chartSync.updateVisibleRange(new NumberRange(twoMinAgo, now));

          } catch (e) {
            console.error("WS message parse error:", e);
          }
        };
        // Fallback to show chart even if no data arrives
        setTimeout(() => {
          if (isLoading) {
            setIsLoading(false);
          }
        }, 2000);

        resolve({ sciChartSurface, websocket: ws, xAxis });
      } catch (error) {
        console.error(`Error creating chart for ${topic}:`, error);
        setChartError(error.message);
        setIsLoading(false);
        resolve({ error });
      }
    });

  return (
    <div style={{ width: "100%", height: "100%", position: "relative" }}>
      { /*}
      <div style={{ 
        position: "absolute", 
        top: 0, left: 0, right: 0, 
        padding: "5px", 
        textAlign: "center", 
        fontSize: "14px",
        color: "#FFFFFF",
        zIndex: 1
      }}>
        {title} {hasData && dataStats.count > 0 && `(${dataStats.count} pts, min: ${dataStats.min?.toFixed(1)}, max: ${dataStats.max?.toFixed(1)})`}
      </div>

      */ }
      
      {isLoading && (
        <div style={{ 
          position: "absolute", 
          top: 0, left: 0, right: 0, bottom: 0, 
          display: "flex", 
          justifyContent: "center", 
          alignItems: "center",
          backgroundColor: "rgba(0,0,0,0.5)",
          zIndex: 2
        }}>
          <p>Loading chart...</p>
        </div>
      )}
      
      {chartError && (
        <div style={{
          position: "absolute", 
          top: 0, left: 0, right: 0, bottom: 0,
          display: "flex", 
          justifyContent: "center", 
          alignItems: "center",
          backgroundColor: "rgba(0,0,0,0.5)",
          color: "red",
          zIndex: 2
        }}>
          <p>Error: {chartError}</p>
        </div>
      )}
      
      <SciChartReact
        initChart={initSciChart}
        onDelete={({ sciChartSurface, websocket, xAxis }) => {
          if (websocket) websocket.close();
          if (xAxis) chartSync.unregisterAxis(xAxis);
        }}
        style={{ width: "100%", height: "100%" }}
      />
    </div>
  );
}
