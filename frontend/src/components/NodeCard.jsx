import { memo } from "react";
import {
  ShieldCheck,
  ShieldAlert,
  Thermometer,
  Droplets,
  Activity,
  Cpu,
  Radio,
  EyeOff,
  RotateCcw,
  AlertOctagon,
} from "lucide-react";
import TrustVectorPanel from "./TrustVectorPanel";
import TrustHistoryChart from "./TrustHistoryChart";

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

function NodeCard({ sensorType, node }) {
  if (!node) return null;

  const stateClass = getStateClass(node.state);
  const isShadow = node.state === "SHADOW";
  const isRecovering = node.state === "RECOVERING";
  const isSuspicious = node.state === "SUSPICIOUS";
  const isUnknown = node.state === "UNKNOWN";

  // Configure sensor card metadata and metrics based on type
  let title = `NODE ${node.node_id}`;
  let subtitle = node.hardware || "ESP32 SENSOR NODE";
  let PrimaryIcon = Activity;
  let readings = [];

  switch (sensorType) {
    case "camera": {
      title = "CAMERA WITNESS";
      subtitle = node.hardware || `NODE ${node.node_id}`;
      PrimaryIcon = Activity;
      const motionVal = node.last?.motion;
      const waterVal = node.last?.water;
      const isMotion = motionVal === 1 || motionVal === true;
      const isWater = waterVal === 1 || waterVal === true;
      readings = [
        {
          icon: <Activity size={15} />,
          label: "PERSON (MOTION)",
          value: isMotion ? "DETECTED" : "CLEAR",
          highlight: isMotion ? "text-amber" : "text-green",
        },
        {
          icon: <Droplets size={15} />,
          label: "WATER (VISION)",
          value: isWater ? "DETECTED" : "CLEAR",
          highlight: isWater ? "text-blue" : "text-green",
        },
        {
          icon: <Cpu size={15} />,
          label: "WITNESS ROLE",
          value: "YOLO VISION",
        },
      ];
      break;
    }

    case "sensor": {
      title = "SENSOR NODE (PIR + WATER)";
      subtitle = `NODE ${node.node_id} · ${node.hardware || "ESP32"}`;
      PrimaryIcon = Activity;
      const motionVal = node.last?.motion;
      const waterVal = node.last?.water;
      const isMotion = motionVal === 1 || motionVal === true;
      const isWater = waterVal === 1 || waterVal === true;
      readings = [
        {
          icon: <Activity size={15} />,
          label: "MOTION (PIR)",
          value: isMotion ? "DETECTED" : "CLEAR",
          highlight: isMotion ? "text-amber" : "text-green",
        },
        {
          icon: <Droplets size={15} />,
          label: "WATER",
          value: isWater ? "DETECTED" : "DRY",
          highlight: isWater ? "text-blue" : "text-green",
        },
        {
          icon: <Cpu size={15} />,
          label: "WITNESS ROLE",
          value: "MOTION + WATER",
        },
      ];
      break;
    }

    case "pir":
    case "motion": {
      title = "PIR / MOTION SENSOR";
      subtitle = `NODE ${node.node_id} · ESP32 #1`;
      PrimaryIcon = Activity;
      const motionVal = node.last?.motion;
      const isMotion = motionVal === 1 || motionVal === true;
      readings = [
        {
          icon: <Activity size={15} />,
          label: "MOTION",
          value: isMotion ? "DETECTED" : "CLEAR",
          highlight: isMotion ? "text-amber" : "text-green",
        },
        {
          icon: <Radio size={15} />,
          label: "RAW SIGNAL",
          value: motionVal !== undefined ? `RAW: ${motionVal}` : "--",
        },
        {
          icon: <Cpu size={15} />,
          label: "WITNESS ROLE",
          value: "WALKWAY",
        },
      ];
      break;
    }

    case "water": {
      title = "WATER SENSOR";
      subtitle = `NODE ${node.node_id} · ESP32 #2`;
      PrimaryIcon = Droplets;
      const waterVal = node.last?.water;
      const isWater = waterVal === 1 || waterVal === true;
      readings = [
        {
          icon: <Droplets size={15} />,
          label: "WATER LEVEL",
          value: isWater ? "DETECTED" : "DRY",
          highlight: isWater ? "text-blue" : "text-green",
        },
        {
          icon: <Radio size={15} />,
          label: "RAW SIGNAL",
          value: waterVal !== undefined ? `RAW: ${waterVal}` : "--",
        },
        {
          icon: <Cpu size={15} />,
          label: "WITNESS ROLE",
          value: "TRAY MONITOR",
        },
      ];
      break;
    }

    case "temperature": {
      title = "TEMPERATURE SENSOR";
      subtitle = `NODE ${node.node_id} · ESP32 #1`;
      PrimaryIcon = Thermometer;
      const tempVal = node.last?.temp;
      const isOutOfBounds = tempVal > 60 || tempVal < 5;
      readings = [
        {
          icon: <Thermometer size={15} />,
          label: "TEMPERATURE",
          value: tempVal != null ? `${Number(tempVal).toFixed(1)}°C` : "--",
          highlight: isOutOfBounds ? "text-red" : "text-green",
        },
        {
          icon: <Radio size={15} />,
          label: "PHYSICS BOUNDS",
          value: "5°C – 60°C",
        },
        {
          icon: <Cpu size={15} />,
          label: "WITNESS ROLE",
          value: "PHYSICS ONLY",
        },
      ];
      break;
    }

    default: {
      PrimaryIcon = Activity;
      readings = [
        {
          icon: <Activity size={15} />,
          label: "STATUS",
          value: node.state || "ONLINE",
        },
      ];
      break;
    }
  }

  return (
    <article
      className={`node-card ${stateClass} ${isShadow ? "node-shadowed-card" : ""}`}
    >
      {/* Shadow State Overlay Header */}
      {isShadow && (
        <div className="shadow-state-banner">
          <EyeOff size={13} />
          <span>REPORTS KEPT · VOTE REMOVED (SHADOW MODE)</span>
        </div>
      )}

      {/* Recovering State Overlay Header */}
      {isRecovering && (
        <div className="recovering-state-banner">
          <RotateCcw size={13} />
          <span>RECOVERY ACTIVE: {node.recovery || "IN PROGRESS"}</span>
        </div>
      )}

      <div className="node-card-header">
        <div className="node-identity">
          <div className="node-icon">
            <PrimaryIcon size={18} />
          </div>

          <div>
            <h4>{title}</h4>
            <span>{subtitle}</span>
          </div>
        </div>

        <div className="node-badge-group">
          <span className="hw-type-badge">HARDWARE</span>
          <span className={`state-badge ${stateClass}`}>
            {node.state || "TRUSTED"}
          </span>
        </div>
      </div>

      {/* Rejected forged reading (spoof / MQTT): the value the attacker TRIED to push */}
      {node.rejected && node.rejected.values && (
        <div className="node-rejected-banner">
          <EyeOff size={13} />
          <span className="rejected-label">
            FORGED{node.rejected.source && node.rejected.source.includes("mqtt") ? " · NETWORK" : ""} — REFUSED
          </span>
          <span className="rejected-values">
            {Object.entries(node.rejected.values).map(([k, v]) => (
              <s key={k}>{k}={String(v)}</s>
            ))}
          </span>
        </div>
      )}

      {/* Causal Explanation reason banner */}
      {node.lastReason && (
        <div className="node-reason-banner">
          <small>DIAGNOSTIC REASON:</small>
          <p>{node.lastReason}</p>
        </div>
      )}

      <div className="node-divider" />

      {/* Sensor Readings */}
      <div className="readings">
        {readings.map((r, i) => (
          <div className="reading" key={i}>
            {r.icon}
            <div>
              <span>{r.label}</span>
              <strong className={r.highlight || ""}>{r.value}</strong>
            </div>
          </div>
        ))}
      </div>

      {/* Trust Vector Decomposition Panel */}
      <TrustVectorPanel node={node} />

      {/* Trust Trajectory Over Time Sparkline */}
      <TrustHistoryChart history={node.trustHistory} />

      <div className="node-footer">
        <span>
          {node.recovery
            ? `RECOVERY: ${node.recovery}`
            : `ID: ${node.node_id} · REAL ESP32`}
        </span>
        <span>
          {isShadow
            ? "● SHADOW ISOLATION"
            : isRecovering
            ? "● RECOVERING (NO VOTE)"
            : "● ACTIVE VOTE"}
        </span>
      </div>
    </article>
  );
}

export default memo(NodeCard);