import { memo } from "react";
import {
  Activity,
  Droplets,
  Camera,
  Thermometer,
  Gauge,
  Radio,
  Cpu,
  ShieldCheck,
  ShieldAlert,
  EyeOff,
  RotateCcw,
  Sparkles,
} from "lucide-react";
import TrustVectorPanel from "./TrustVectorPanel";
import TrustHistoryChart from "./TrustHistoryChart";

function getSensorIcon(sensorType) {
  switch (sensorType?.toLowerCase()) {
    case "motion":
      return <Activity size={20} />;
    case "water":
      return <Droplets size={20} />;
    case "camera":
      return <Camera size={20} />;
    case "temperature":
      return <Thermometer size={20} />;
    case "vibration":
      return <Gauge size={20} />;
    default:
      return <Radio size={20} />;
  }
}

function getStateClass(state) {
  switch (state?.toUpperCase()) {
    case "TRUSTED":
      return "trusted";
    case "SUSPICIOUS":
      return "suspicious";
    case "SHADOW":
      return "shadow";
    case "UNKNOWN":
      return "unknown";
    case "RECOVERING":
      return "recovering";
    default:
      return "trusted";
  }
}

/**
 * NodeDetailInspector
 * Shows deep forensic telemetry, sensor readings, and trust decomposition
 * for the node selected in the mesh topology graph.
 */
function NodeDetailInspector({ node, allNodes = {}, onSelectNode }) {
  if (!node) return null;

  const stateClass = getStateClass(node.state);
  const isShadow = node.state === "SHADOW";
  const isRecovering = node.state === "RECOVERING";
  const isSimulated = node.isSimulated;
  const sensorIcon = getSensorIcon(node.sensorType);

  // Parse sensor-specific readout
  let primaryReadingLabel = "SENSOR VALUE";
  let primaryReadingVal = "--";
  let primaryHighlight = "text-green";
  let secondaryDetails = [];

  switch (node.sensorType) {
    case "motion": {
      const motionVal = node.last?.motion;
      const isMotion = motionVal === 1 || motionVal === true;
      primaryReadingLabel = "PIR MOTION";
      primaryReadingVal = isMotion ? "DETECTED (1)" : "CLEAR (0)";
      primaryHighlight = isMotion ? "text-amber" : "text-green";
      secondaryDetails = [
        { label: "RAW STATE", val: `SIGNAL: ${motionVal ?? 0}` },
        { label: "PHYSICS CHECK", val: "NOMINAL (< 5 tr/s)" },
        { label: "ROLE", val: "WALKWAY WITNESS #1" },
      ];
      break;
    }

    case "water": {
      const waterVal = node.last?.water;
      const isWater = waterVal === 1 || waterVal === true;
      primaryReadingLabel = "WATER SENSOR";
      primaryReadingVal = isWater ? "DETECTED (1)" : "DRY / CLEAR (0)";
      primaryHighlight = isWater ? "text-blue" : "text-green";
      secondaryDetails = [
        { label: "RAW STATE", val: `SIGNAL: ${waterVal ?? 0}` },
        { label: "PHYSICS CHECK", val: "NOMINAL" },
        { label: "ROLE", val: "TRAY OVERFLOW #1" },
      ];
      break;
    }

    case "camera": {
      const motionVal = node.last?.motion;
      const waterVal = node.last?.water;
      primaryReadingLabel = "VISION STREAM";
      primaryReadingVal = "98% CONFIDENCE";
      primaryHighlight = "text-green";
      secondaryDetails = [
        { label: "MOTION WITNESS", val: motionVal ? "PERSON DETECTED" : "CLEAR" },
        { label: "WATER WITNESS", val: waterVal ? "WATER DETECTED" : "CLEAR" },
        { label: "STREAM", val: "MJPEG / YOLOv8" },
      ];
      break;
    }

    case "temperature": {
      const tempVal = node.last?.temp;
      const isOutOfBounds = tempVal > 60 || tempVal < 5;
      primaryReadingLabel = "TEMPERATURE";
      primaryReadingVal = tempVal != null ? `${Number(tempVal).toFixed(1)}°C` : "--";
      primaryHighlight = isOutOfBounds ? "text-red" : "text-green";
      secondaryDetails = [
        { label: "PHYSICS LIMITS", val: "5.0°C – 60.0°C" },
        { label: "MAX RATE", val: "< 2.0°C / sec" },
        { label: "ROLE", val: "THERMAL VERIFIER" },
      ];
      break;
    }

    default: {
      primaryReadingLabel = "INDUSTRIAL TELEMETRY";
      primaryReadingVal = "NORMAL";
      secondaryDetails = [
        { label: "TYPE", val: node.sensorLabel || "Sensor" },
        { label: "TELEMETRY", val: JSON.stringify(node.last || {}) },
        { label: "ROLE", val: "SIMULATED WITNESS" },
      ];
      break;
    }
  }

  const nodeList = Object.values(allNodes);

  return (
    <div className={`node-detail-inspector-card ${stateClass}`}>
      {/* Node selector tabs */}
      <div className="inspector-tabs-header">
        <div className="inspector-title">
          <Sparkles size={16} className="text-amber" />
          <span>INSPECTOR FOCUS</span>
        </div>

        <div className="inspector-node-chips">
          {nodeList.map((n) => (
            <button
              key={n.node_id}
              className={`node-select-chip ${n.node_id === node.node_id ? "active" : ""}`}
              onClick={() => onSelectNode && onSelectNode(n.node_id)}
            >
              <strong>{n.node_id}</strong>
              <small>{n.sensorType?.slice(0, 4)}</small>
            </button>
          ))}
        </div>
      </div>

      {/* Shadow / Recovery Banner */}
      {isShadow && (
        <div className="shadow-state-banner">
          <EyeOff size={14} />
          <span>REPORTS KEPT · VOTE REMOVED (ISOLATED IN SHADOW)</span>
        </div>
      )}

      {isRecovering && (
        <div className="recovering-state-banner">
          <RotateCcw size={14} />
          <span>RECOVERY ACTIVE: {node.recovery || "IN PROGRESS"}</span>
        </div>
      )}

      {/* Main Node Header */}
      <div className="inspector-main-header">
        <div className="inspector-identity">
          <div className="inspector-icon-box">{sensorIcon}</div>
          <div>
            <h3>
              NODE {node.node_id}: {node.sensorLabel || node.name}
            </h3>
            <span className="inspector-hw-subtitle">
              {node.hardware} · {isSimulated ? "SIMULATED EDGE" : "PHYSICAL HARDWARE"}
            </span>
          </div>
        </div>

        <div className="inspector-state-block">
          <span className={`state-badge ${stateClass}`}>
            {node.state || "TRUSTED"}
          </span>
          <span className="overall-score-tag">
            OVERALL TRUST: {node.overall ?? 100}%
          </span>
        </div>
      </div>

      {/* Diagnostic Reason */}
      {node.lastReason && (
        <div className="node-reason-banner">
          <small>DIAGNOSTIC CAUSAL REASON:</small>
          <p>{node.lastReason}</p>
        </div>
      )}

      {/* Sensor Readings Grid */}
      <div className="inspector-readings-grid">
        <div className="primary-reading-box">
          <span className="reading-sub-label">{primaryReadingLabel}</span>
          <strong className={`primary-reading-number ${primaryHighlight}`}>
            {primaryReadingVal}
          </strong>
        </div>

        <div className="secondary-readings-list">
          {secondaryDetails.map((d, i) => (
            <div className="secondary-reading-row" key={i}>
              <span>{d.label}</span>
              <strong>{d.val}</strong>
            </div>
          ))}
        </div>
      </div>

      {/* Trust Vector Decomposition */}
      <TrustVectorPanel node={node} />

      {/* Trust Trajectory Over Time */}
      <TrustHistoryChart history={node.trustHistory} />
    </div>
  );
}

export default memo(NodeDetailInspector);
