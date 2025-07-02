import { useEffect, useRef } from "react";
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

// Human-readable time labels for X Axis
class TimeFormatterLabelProvider extends TextLabelProvider {
  formatLabel(dataValue) {
    const date = new Date(dataValue);
    const hours = String(date.getHours()).padStart(2, "0");
    const minutes = String(date.getMinutes()).padStart(2, "0");
    const seconds = String(date.getSeconds()).padStart(2, "0");
    return `${hours}:${minutes}:${seconds}`;
  }
  formatCursorLabel(dataValue) {
    return this.formatLabel(dataValue);
  }
}

export default function ChartBlock({
  title,
  yLabel,
  color,
  dataset,
  showXaxis = true,
  showYaxis = true,
  yMin = 0,
  yMax = 100
}) {
  const dataSeries = useRef(null);
  const chartRef = useRef(null);
  const xAxisRef = useRef(null);

  const initSciChart = (rootElement) =>
    new Promise(async (resolve) => {
      try {
        const { sciChartSurface, wasmContext } = await SciChartSurface.create(rootElement, {
          theme: new SciChartJsNavyTheme(),
          backgroundColor: "#1a2b42"
        });

        chartRef.current = sciChartSurface;

        // Create X axis
        const xAxis = new NumericAxis(wasmContext, {
          axisTitle: "",
          autoRange: EAutoRange.Never,
          labelProvider: new TimeFormatterLabelProvider(wasmContext),
          isVisible: showXaxis
        });

        sciChartSurface.xAxes.add(xAxis);
        xAxisRef.current = xAxis;

        // Create Y axis
        const yAxis = new NumericAxis(wasmContext, {
          axisTitle: yLabel,
          axisAlignment: EAxisAlignment.Left,
          axisTitleStyle: { color: "rgba(255, 255, 255, 0.5)" },
          isVisible: showYaxis,
          autoRange: EAutoRange.Always
        });

        sciChartSurface.yAxes.add(yAxis);

        // Create data series with initial dummy point to prevent crashes
        const seriesObj = new XyDataSeries(wasmContext, {
          dataSeriesName: yLabel,
          containsDateTime: true
        });

        // Add an initial point to prevent empty series issues
        const now = Date.now();
        seriesObj.append(now, yMin + (yMax - yMin) / 2); // Add a midpoint value

        dataSeries.current = seriesObj;

        // Create the line series
        const lineSeries = new FastLineRenderableSeries(wasmContext, {
          stroke: color,
          strokeThickness: 3,
          dataSeries: seriesObj
        });

        sciChartSurface.renderableSeries.add(lineSeries);

        // Set initial axis range
        xAxis.visibleRange = new NumberRange(now - 2 * 60 * 1000, now);

        resolve({ sciChartSurface });
      } catch (error) {
        console.error("Failed to initialize chart:", error);
        resolve({ error });
      }
    });

  useEffect(() => {
    if (dataSeries.current && dataset && dataset.length) {
      // Filter out any data points with null/undefined y values
      const validData = dataset.filter(pt => pt.y !== null && pt.y !== undefined);
      
      if (validData.length === 0) {
        // If no valid data, don't try to update the chart
        return;
      }
      
      const xs = validData.map(pt => pt.x);
      const ys = validData.map(pt => pt.y);
      
      dataSeries.current.clear();
      dataSeries.current.appendRange(xs, ys);

      const now = Date.now();
      const twoMinAgo = now - 2 * 60 * 1000;

      if (xAxisRef.current) {
        xAxisRef.current.visibleRange = new NumberRange(twoMinAgo, now);
      }
    }
  }, [dataset]);

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
        <SciChartReact
          initChart={initSciChart}
          style={{ width: "100%", height: "100%" }}
        />
      )}
    </div>
  );
}
