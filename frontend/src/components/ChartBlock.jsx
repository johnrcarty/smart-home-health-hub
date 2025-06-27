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
  EAxisAlignment,
  ZoomExtentsModifier,
  MouseWheelZoomModifier,
  ZoomPanModifier,
  RubberBandXyZoomModifier,
  LegendModifier
} from "scichart";
import { useEffect, useState, useRef, useContext } from "react";
import { SensorContext } from "../App";

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
  ignoreUpdates: false, // Flag to prevent circular updates
  
  // Add an axis to the sync group after it's fully initialized
  registerAxis(axis) {
    if (!axis) return;
    
    // Store the axis reference
    this.axes.push(axis);
    console.log(`Registered axis, total: ${this.axes.length}`);
    
    // Set the initial visible range
    axis.visibleRange = this.lastVisibleRange;
    
    // Set up bidirectional synchronization for this axis
    this.setupAxisSync(axis);
  },
  
  // Set up sync for a specific axis
  setupAxisSync(axis) {
    // Subscribe to changes on this axis
    axis.visibleRangeChanged.subscribe((args) => {
      // Skip if we're currently processing updates
      if (this.ignoreUpdates) return;
      
      // Set flag to prevent circular updates
      this.ignoreUpdates = true;
      
      try {
        // Update our shared range
        this.lastVisibleRange = args.visibleRange;
        
        // Update all other axes
        this.axes.forEach(otherAxis => {
          if (otherAxis !== axis) {
            try {
              otherAxis.visibleRange = this.lastVisibleRange;
            } catch (e) {
              console.error("Error syncing axis:", e);
            }
          }
        });
      } finally {
        // Clear the flag when done
        setTimeout(() => {
          this.ignoreUpdates = false;
        }, 0);
      }
    });
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
    if (!newRange || this.ignoreUpdates) return;
    
    this.ignoreUpdates = true;
    try {
      this.lastVisibleRange = newRange;
      
      // Update all registered axes
      this.axes.forEach(axis => {
        try {
          axis.visibleRange = newRange;
        } catch (e) {
          console.error("Error updating axis:", e);
        }
      });
    } finally {
      setTimeout(() => {
        this.ignoreUpdates = false;
      }, 0);
    }
  }
};

export default function ChartBlock({ 
  title, 
  topic, 
  yLabel, 
  yMin, 
  yMax, 
  color, 
  sensorKey,
  xDisplay = true // Default to true if not specified
}) {
  const [isLoading, setIsLoading] = useState(true);
  const [hasData, setHasData] = useState(false);
  const [chartError, setChartError] = useState(null);
  const [userHasScrolled, setUserHasScrolled] = useState(false);
  const dataSeries = useRef(null);
  const { updateSensorValue } = useContext(SensorContext);
  const chartRef = useRef(null);
  const scrollTimerRef = useRef(null);

  // Simplified chart initialization focused on reliability
  const initSciChart = (rootElement) =>
    new Promise(async (resolve) => {
      try {
        console.log(`Initializing chart for ${topic}`);
        
        // Create the chart surface with basic theme
        const { sciChartSurface, wasmContext } = await SciChartSurface.create(rootElement, {
          theme: new SciChartJsNavyTheme(),
          backgroundColor: "#1a2b42", 
          title: "",
          titleStyle: { fontSize: 0 }
        });
        
        chartRef.current = sciChartSurface;

        // Create X axis with custom time formatter and scrolling capability
        const xAxis = new NumericAxis(wasmContext, {
          axisTitle: "",
          autoRange: EAutoRange.Never,
          labelProvider: new TimeFormatterLabelProvider(wasmContext),
          drawMajorGridLines: true,
          drawMinorGridLines: false,
          majorTickLineStyle: { color: "#FFFFFF22" },
          axisTitleStyle: { color: "#FFFFFF" },
          labelStyle: { color: "#FFFFFF" },
          isScrollable: true,
          scrollBarHeight: xDisplay ? 15 : 0, // Only show scrollbar if xDisplay is true
          visibleRangeLimit: new NumberRange(
            Date.now() - 30 * 60 * 1000, // 30 minutes history
            Date.now() + 60 * 1000 // 1 minute future buffer
          ),
          isVisible: xDisplay,
          drawLabels: xDisplay,
          drawMajorTickLines: xDisplay,
          drawMinorTickLines: xDisplay
        });
        
        sciChartSurface.xAxes.add(xAxis);
        console.log(`X axis created for ${topic}, visible: ${xDisplay}`);
        
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
          autoRange: EAutoRange.Always,
          growBy: new NumberRange(0.1, 0.1)
        });
        
        sciChartSurface.yAxes.add(yAxis);

        // Add chart modifiers for interaction
        sciChartSurface.chartModifiers.add(new ZoomExtentsModifier());
        sciChartSurface.chartModifiers.add(new MouseWheelZoomModifier());
        sciChartSurface.chartModifiers.add(new ZoomPanModifier());
        sciChartSurface.chartModifiers.add(new RubberBandXyZoomModifier());
        
        // Optional legend
        const legendModifier = new LegendModifier({ showCheckboxes: false });
        sciChartSurface.chartModifiers.add(legendModifier);

        // Create data series with some initial points
        const seriesObj = new XyDataSeries(wasmContext, { 
          dataSeriesName: yLabel,
          containsDateTime: true  // Indicate this series contains time data
        });
        dataSeries.current = seriesObj;
        
        // Add some initial data points to ensure rendering starts
        const initialTime = Date.now();
        const midValue = yMin + (yMax - yMin) / 2;
        
        for (let i = 0; i < 5; i++) {
          seriesObj.append(initialTime - (5-i) * 1000, midValue);
        }
        
        // Create the line series
        const lineSeries = new FastLineRenderableSeries(wasmContext, {
          stroke: color,
          strokeThickness: 3,
          dataSeries: seriesObj
        });
        
        sciChartSurface.renderableSeries.add(lineSeries);

        // Set the initial visible range to show last 2 minutes
        const twoMinutesAgo = initialTime - 2 * 60 * 1000;
        xAxis.visibleRange = new NumberRange(twoMinutesAgo, initialTime);

        // Detect user scrolling/zooming - but don't handle sync here
        // (the chartSync object will handle it)
        xAxis.visibleRangeChanged.subscribe((args) => {
          if (!args.isAnimating && !chartSync.ignoreUpdates) { 
            setUserHasScrolled(true);
            
            // After inactivity, resume auto-scrolling
            clearTimeout(scrollTimerRef.current);
            scrollTimerRef.current = setTimeout(() => {
              setUserHasScrolled(false);
            }, 15000); // Resume after 15 seconds
          }
        });

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

        ws.onmessage = (evt) => {
          try {
            const msg = JSON.parse(evt.data);

            // Only handle unified updates
            if (msg.type !== "sensor_update" || !msg.state) return;

            // Grab the raw JSON payload for this sensor
            const raw = msg.state[sensorKey];
            if (raw == null) return; // no update yet

            // Parse the value
            const obj = JSON.parse(raw);
            const value = Object.values(obj)[0];
            
            // Update the context with the latest value
            updateSensorValue(sensorKey, value);

            // Append to your series
            const now = Date.now();
            dataSeries.current.append(now, value);

            // Keep 30 minutes of history (1800 points at 1 Hz)
            if (dataSeries.current.count() > 1800) {
              dataSeries.current.removeRange(0, dataSeries.current.count() - 1800);
            }

            // Update the visible range only if user is not scrolled
            if (!userHasScrolled) {
              const twoMinAgo = now - 2 * 60 * 1000;
              chartSync.updateVisibleRange(new NumberRange(twoMinAgo, now));
            }

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

  // Clean up timer on unmount
  useEffect(() => {
    return () => {
      clearTimeout(scrollTimerRef.current);
    };
  }, []);

  return (
    <div style={{ width: "100%", height: "100%", position: "relative" }}>
      {/* Chart title */}
      <div style={{ 
        position: "absolute", 
        top: 5, left: 10,
        fontSize: "14px",
        color: "#FFFFFF",
        zIndex: 1
      }}>
        {title}
      </div>
      
      {/* Loading indicator */}
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
      
      {/* Error display */}
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
      
      {/* Back to Live button - only shows when scrolled */}
      {userHasScrolled && (
        <button 
          style={{
            position: "absolute",
            top: 5,
            right: 10,
            background: "#3a5a8c",
            color: "white",
            border: "none",
            padding: "5px 10px",
            borderRadius: "4px",
            cursor: "pointer",
            fontSize: "12px",
            zIndex: 10
          }}
          onClick={() => {
            const now = Date.now();
            const twoMinAgo = now - 2 * 60 * 1000;
            chartSync.updateVisibleRange(new NumberRange(twoMinAgo, now));
            setUserHasScrolled(false);
          }}
        >
          Back to Live
        </button>
      )}
      
      {/* The chart itself */}
      <SciChartReact
        initChart={initSciChart}
        onDelete={({ sciChartSurface, websocket, xAxis }) => {
          if (websocket) websocket.close();
          if (xAxis) chartSync.unregisterAxis(xAxis);
          clearTimeout(scrollTimerRef.current);
        }}
        style={{ width: "100%", height: "100%" }}
      />
    </div>
  );
}
