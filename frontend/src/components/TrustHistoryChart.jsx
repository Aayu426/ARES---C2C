import { memo } from "react";

/**
 * Trust History Sparkline / Area Chart
 * Renders an animated SVG line and gradient area showing overall trust trajectory over time.
 * Makes rapid trust collapses vividly noticeable.
 */
function TrustHistoryChart({ history = [], width = "100%", height = 65 }) {
  if (!history || history.length < 2) {
    return (
      <div className="trust-chart-empty">
        <span>Accumulating trust telemetry...</span>
      </div>
    );
  }

  const viewBoxWidth = 240;
  const viewBoxHeight = 55;
  const padding = 5;

  const points = history.slice(-20); // Last 20 points
  const minVal = 0;
  const maxVal = 100;

  const getX = (index) => {
    return padding + (index / (points.length - 1)) * (viewBoxWidth - 2 * padding);
  };

  const getY = (val) => {
    const clamped = Math.max(minVal, Math.min(maxVal, val ?? 100));
    return viewBoxHeight - padding - (clamped / 100) * (viewBoxHeight - 2 * padding);
  };

  const pathD = points.reduce((acc, pt, i) => {
    const x = getX(i).toFixed(1);
    const y = getY(pt.overall).toFixed(1);
    return i === 0 ? `M ${x} ${y}` : `${acc} L ${x} ${y}`;
  }, "");

  const areaD = `${pathD} L ${getX(points.length - 1).toFixed(1)} ${viewBoxHeight} L ${getX(0).toFixed(1)} ${viewBoxHeight} Z`;

  const latestVal = points[points.length - 1]?.overall ?? 100;
  const strokeColor =
    latestVal >= 70 ? "#67b58a" : latestVal >= 40 ? "#c7a96b" : "#e06c75";
  const gradientId = `trust-grad-${latestVal >= 70 ? "green" : latestVal >= 40 ? "amber" : "red"}`;

  return (
    <div className="trust-history-chart-wrapper">
      <div className="chart-header">
        <span>TRUST TRAJECTORY</span>
        <span style={{ color: strokeColor }}>{latestVal}%</span>
      </div>
      <svg
        viewBox={`0 0 ${viewBoxWidth} ${viewBoxHeight}`}
        style={{ width, height, display: "block", overflow: "visible" }}
      >
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={strokeColor} stopOpacity="0.35" />
            <stop offset="100%" stopColor={strokeColor} stopOpacity="0.0" />
          </linearGradient>
        </defs>

        {/* 70% threshold guideline */}
        <line
          x1={padding}
          y1={getY(70)}
          x2={viewBoxWidth - padding}
          y2={getY(70)}
          stroke="#263342"
          strokeDasharray="2 2"
          strokeWidth="1"
        />

        {/* 40% shadow guideline */}
        <line
          x1={padding}
          y1={getY(40)}
          x2={viewBoxWidth - padding}
          y2={getY(40)}
          stroke="#3d2222"
          strokeDasharray="2 2"
          strokeWidth="1"
        />

        {/* Gradient fill */}
        <path d={areaD} fill={`url(#${gradientId})`} />

        {/* Trajectory line */}
        <path
          d={pathD}
          fill="none"
          stroke={strokeColor}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Current point pulse */}
        {points.length > 0 && (
          <circle
            cx={getX(points.length - 1)}
            cy={getY(latestVal)}
            r="3.5"
            fill={strokeColor}
            stroke="#0d1117"
            strokeWidth="1.5"
          />
        )}
      </svg>
    </div>
  );
}

export default memo(TrustHistoryChart);
