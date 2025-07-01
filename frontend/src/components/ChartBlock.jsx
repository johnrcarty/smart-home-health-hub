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
  showYaxis = true
}) {
  const dataSeries = useRef(null);
  const chartRef = useRef(null);
  const xAxisRef = useRef(null);

  const initSciChart = (rootElement) =>
    new Promise(async (resolve) => {
      const { sciChartSurface, wasmContext } = await SciChartSurface.create(rootElement, {
        theme: new SciChartJsNavyTheme(),
        backgroundColor: "#1a2b42"
      });

      chartRef.current = sciChartSurface;

      // X Axis fixed to last 2 mins
      const xAxis = new NumericAxis(wasmContext, {
        axisTitle: "",
        autoRange: EAutoRange.Never,
        labelProvider: new TimeFormatterLabelProvider(wasmContext),
        isVisible: showXaxis
      });
      sciChartSurface.xAxes.add(xAxis);
      xAxisRef.current = xAxis;

      // Y Axis auto-scales
      const yAxis = new NumericAxis(wasmContext, {
        axisTitle: yLabel,
        axisAlignment: EAxisAlignment.Left,
        axisTitleStyle: { color: "rgba(255, 255, 255, 0.5)" },
        isVisible: showYaxis,
        autoRange: EAutoRange.Always
      });
      sciChartSurface.yAxes.add(yAxis);

      const seriesObj = new XyDataSeries(wasmContext, {
        dataSeriesName: yLabel,
        containsDateTime: true
      });
      dataSeries.current = seriesObj;

      const lineSeries = new FastLineRenderableSeries(wasmContext, {
        stroke: color,
        strokeThickness: 3,
        dataSeries: seriesObj
      });
      sciChartSurface.renderableSeries.add(lineSeries);

      resolve({ sciChartSurface });
    });

  useEffect(() => {
    if (dataSeries.current && dataset.length) {
      const xs = dataset.map(pt => pt.x);
      const ys = dataset.map(pt => pt.y);
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

      <SciChartReact
        initChart={initSciChart}
        style={{ width: "100%", height: "100%" }}
      />
    </div>
  );
}
