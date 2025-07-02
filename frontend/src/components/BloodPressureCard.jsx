import { useEffect, useRef, useState } from "react";
import {
  SciChartSurface,
  NumericAxis,
  FastLineRenderableSeries,
  XyDataSeries,
  SciChartJsNavyTheme,
  CategoryAxis,
  EAutoRange
} from "scichart";

const BloodPressureCard = ({ bpHistory = [] }) => {
  const chartRef = useRef(null);
  const chartSurfaceRef = useRef(null);
  const [chartsInitialized, setChartsInitialized] = useState(false);
  
  // Initialize the BP chart
  useEffect(() => {
    // Skip rendering if no data or chart already exists
    if (!bpHistory.length) return;
    
    // If we have valid data to display
    const validBpData = bpHistory.filter(bp => bp.map !== null && bp.map !== undefined);
    if (!validBpData.length) return;
    
    const initChart = async () => {
      try {
        // Clear any existing chart
        if (chartRef.current) {
          if (chartSurfaceRef.current) {
            chartSurfaceRef.current.delete();
            chartSurfaceRef.current = null;
          }
          chartRef.current.innerHTML = '';
        }
        
        // Create the chart surface
        const { sciChartSurface, wasmContext } = await SciChartSurface.create(chartRef.current, {
          theme: new SciChartJsNavyTheme(),
          backgroundColor: "#1a2b42"
        });
        
        chartSurfaceRef.current = sciChartSurface;
        
        // Create X axis (index based - not time dependent)
        const xAxis = new NumericAxis(wasmContext, {
          labelStyle: { color: "#FFFFFF", fontSize: 10 },
          drawLabels: false,
          drawMajorGridLines: false,
          drawMinorGridLines: false,
          drawMajorTickLines: false,
          drawMinorTickLines: false,
          visibleRange: { min: -0.5, max: 4.5 } // For 5 data points (0-4) with some padding
        });
        
        sciChartSurface.xAxes.add(xAxis);
        
        // Create Y axis for BP values
        const yAxis = new NumericAxis(wasmContext, {
          axisTitle: "MAP",
          axisTitleStyle: { color: "#FFFFFF", fontSize: 10 },
          labelStyle: { color: "#FFFFFF", fontSize: 10 },
          autoRange: EAutoRange.Always,
          drawMajorGridLines: false,
          drawMinorGridLines: false,
          growBy: { min: 0.1, max: 0.1 } // Add 10% padding top and bottom
        });
        
        sciChartSurface.yAxes.add(yAxis);
        
        // Create data series for MAP values
        const mapSeries = new XyDataSeries(wasmContext, { dataSeriesName: "MAP" });
        
        // Add the data points in reverse order (oldest first, newest last)
        // This makes the line go from left to right with newest values on the right
        validBpData
          .slice(0, 5)
          .reverse()
          .forEach((bp, index) => {
            mapSeries.append(index, bp.map);
          });
        
        // Create line series for MAP with purple color
        const lineSeries = new FastLineRenderableSeries(wasmContext, {
          stroke: "#9c56b8", // Purple color
          strokeThickness: 3,
          dataSeries: mapSeries,
          pointMarker: {
            type: "Ellipse",
            fill: "#9c56b8",
            size: 5
          }
        });
        
        sciChartSurface.renderableSeries.add(lineSeries);
        
        // Resize chart to fit container
        sciChartSurface.zoomExtents();
        
        return sciChartSurface;
      } catch (err) {
        console.error("Failed to create BP chart:", err);
        return null;
      }
    };
    
    initChart();
    setChartsInitialized(true);
    
  }, [bpHistory]);
  
  // Sort BP history with most recent readings first
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
  
  // Format the date/time for display
  const formatDateTime = (dateTimeStr) => {
    if (!dateTimeStr) return "Unknown";
    
    try {
      const date = new Date(dateTimeStr);
      return date.toLocaleTimeString([], { 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: true 
      });
    } catch (e) {
      return "Invalid Date";
    }
  };

  return (
    <div className="bp-card">
      <h3 className="bp-title">Blood Pressure History</h3>
      
      {/* Chart section */}
      <div 
        ref={chartRef} 
        className="bp-chart"
        style={{ height: "90px", width: "100%" }}
      >
        {!chartsInitialized && bpHistory.length === 0 && (
          <div className="no-data">
            No BP data available
          </div>
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
                      : '--/--'
                    }
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