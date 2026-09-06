import { memo } from "react";
import {
  Activity,
  Droplets,
  Camera,
  Thermometer,
  Gauge,
  Radio,
  Server,
  ShieldCheck,
  ShieldAlert,
  EyeOff,
  RotateCcw,
} from "lucide-react";

/**
 * Returns an appropriate icon for the node's sensor modality
 */
function getSensorIcon(sensorType) {
  switch (sensorType?.toLowerCase()) {
    case "motion":
      return <Activity size={16} />;
    case "water":
      return <Droplets size={16} />;
    case "camera":
      return <Camera size={16} />;
    case "temperature":
      return <Thermometer size={16} />;
    case "vibration":
    case "pressure":
      return <Gauge size={16} />;
    default:
      return <Radio size={16} />;
  }
}

/**
 * Formats the live primary reading for the node glyph
 */
function getReadingText(node) {
  if (!node.last) return "NOMINAL";
  if (node.last.motion !== undefined) {
    return node.last.motion ? "MOTION (1)" : "CLEAR (0)";
  }
  if (node.last.water !== undefined) {
    return node.last.water ? "WET (1)" : "DRY (0)";
  }
  if (node.last.temp !== undefined) {
    return `${Number(node.last.temp).toFixed(1)}°C`;
  }
  if (node.last.vibration !== undefined) {
    return `${node.last.vibration} g`;
  }
  return "ACTIVE";
}

/**
 * MeshTopologyGraph
 * High-tech SVG graphical mesh topology representing edge nodes,
 * their sensor modalities, peer corroboration links, and gateway connections.
 */
function MeshTopologyGraph({ nodes = {}, selectedNodeId, onSelectNode }) {
  const nodeArray = Object.values(nodes);
  const totalNodes = nodeArray.length;

  const width = 860;
  const height = 440;
  const centerX = width / 2;
  const centerY = height / 2;
  const radius = 160;

  // Calculate coordinates in a circle around the central gateway
  const nodePositions = nodeArray.map((node, index) => {
    const angle = (index / totalNodes) * 2 * Math.PI - Math.PI / 2;
    const x = centerX + radius * Math.cos(angle);
    const y = centerY + radius * Math.sin(angle);
    return {
      ...node,
      x,
      y,
    };
  });

  return (
    <div className="mesh-topology-card">
      <div className="mesh-header">
        <div className="mesh-title">
          <Radio size={18} className="text-green pulse-icon" />
          <div>
            <h4>CYBER-PHYSICAL MESH TOPOLOGY</h4>
            <span>Interactive Zero-Trust Network Graph · Click Node to Inspect</span>
          </div>
        </div>

        <div className="mesh-legend">
          <div className="legend-item">
            <span className="legend-line line-trusted" />
            <span>Corroborated Link</span>
          </div>
          <div className="legend-item">
            <span className="legend-line line-suspicious" />
            <span>Under Challenge</span>
          </div>
          <div className="legend-item">
            <span className="legend-line line-shadow" />
            <span>Shadow (Vote Discarded)</span>
          </div>
        </div>
      </div>

      <div className="mesh-svg-wrapper">
        <svg viewBox={`0 0 ${width} ${height}`} className="mesh-svg">
          <defs>
            {/* Background mesh grid pattern */}
            <pattern id="grid-pattern" width="30" height="30" patternUnits="userSpaceOnUse">
              <path d="M 30 0 L 0 0 0 30" fill="none" stroke="#131b24" strokeWidth="0.8" />
            </pattern>

            {/* Radial glow for Gateway */}
            <radialGradient id="gateway-glow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#67b58a" stopOpacity="0.25" />
              <stop offset="100%" stopColor="#67b58a" stopOpacity="0" />
            </radialGradient>

            {/* Radial glow for selected node */}
            <radialGradient id="selected-glow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#8fb8dd" stopOpacity="0.4" />
              <stop offset="100%" stopColor="#8fb8dd" stopOpacity="0" />
            </radialGradient>
          </defs>

          {/* Grid Background */}
          <rect width={width} height={height} fill="url(#grid-pattern)" />

          {/* Peer-to-Peer Inter-Node Verification Links */}
          {nodePositions.map((n1, i) =>
            nodePositions.slice(i + 1).map((n2) => {
              const isEitherShadow = n1.state === "SHADOW" || n2.state === "SHADOW";
              const isEitherSuspicious =
                n1.state === "SUSPICIOUS" || n2.state === "SUSPICIOUS";

              let linkClass = "peer-link-trusted";
              if (isEitherShadow) linkClass = "peer-link-shadow";
              else if (isEitherSuspicious) linkClass = "peer-link-suspicious";

              return (
                <line
                  key={`peer-${n1.node_id}-${n2.node_id}`}
                  x1={n1.x}
                  y1={n1.y}
                  x2={n2.x}
                  y2={n2.y}
                  className={`peer-mesh-line ${linkClass}`}
                />
              );
            })
          )}

          {/* Gateway-to-Node Primary Ingestion Links */}
          {nodePositions.map((n) => {
            const isShadow = n.state === "SHADOW";
            const isSuspicious = n.state === "SUSPICIOUS";
            const isSelected = selectedNodeId === n.node_id;

            let hubLinkClass = "hub-link-trusted";
            if (isShadow) hubLinkClass = "hub-link-shadow";
            else if (isSuspicious) hubLinkClass = "hub-link-suspicious";

            return (
              <g key={`hub-link-${n.node_id}`}>
                <line
                  x1={centerX}
                  y1={centerY}
                  x2={n.x}
                  y2={n.y}
                  className={`hub-mesh-line ${hubLinkClass} ${isSelected ? "hub-link-selected" : ""}`}
                />
              </g>
            );
          })}

          {/* Center Hub: ARES Gateway */}
          <g className="gateway-hub-group">
            <circle cx={centerX} cy={centerY} r="54" fill="url(#gateway-glow)" />
            <circle cx={centerX} cy={centerY} r="38" className="gateway-outer-circle" />
            <circle cx={centerX} cy={centerY} r="30" className="gateway-inner-circle" />
            <foreignObject
              x={centerX - 28}
              y={centerY - 28}
              width="56"
              height="56"
              className="gateway-fo"
            >
              <div className="gateway-badge-content">
                <Server size={18} className="text-green" />
                <span>GATEWAY</span>
              </div>
            </foreignObject>
          </g>

          {/* Node Glyphs */}
          {nodePositions.map((node) => {
            const isSelected = selectedNodeId === node.node_id;
            const isShadow = node.state === "SHADOW";
            const isRecovering = node.state === "RECOVERING";
            const isSuspicious = node.state === "SUSPICIOUS";
            const overallTrust = node.overall ?? 100;

            let nodeColor = "#67b58a";
            if (isShadow) nodeColor = "#e06c75";
            else if (isSuspicious) nodeColor = "#c7a96b";
            else if (isRecovering) nodeColor = "#7da4c7";

            const reading = getReadingText(node);
            const sensorIcon = getSensorIcon(node.sensorType);

            return (
              <g
                key={node.node_id}
                className={`mesh-node-glyph ${isSelected ? "node-selected" : ""} ${
                  isShadow ? "node-shadowed" : ""
                }`}
                onClick={() => onSelectNode && onSelectNode(node.node_id)}
                style={{ cursor: "pointer" }}
              >
                {/* Selection / Shadow Aura */}
                {isSelected && (
                  <circle cx={node.x} cy={node.y} r="52" fill="url(#selected-glow)" />
                )}

                {/* Node Outer Ring */}
                <circle
                  cx={node.x}
                  cy={node.y}
                  r="34"
                  className="node-base-circle"
                  stroke={nodeColor}
                  strokeDasharray={isShadow ? "4 3" : "none"}
                />

                {/* Node Center Fill */}
                <circle cx={node.x} cy={node.y} r="28" className="node-fill-circle" />

                {/* HTML ForeignObject for rich icon + labels inside glyph */}
                <foreignObject
                  x={node.x - 26}
                  y={node.y - 26}
                  width="52"
                  height="52"
                  className="node-fo"
                >
                  <div className="node-glyph-inner" style={{ color: nodeColor }}>
                    {sensorIcon}
                    <strong className="glyph-id">{node.node_id}</strong>
                  </div>
                </foreignObject>

                {/* Sensor & State Tag Placed Below Node */}
                <foreignObject
                  x={node.x - 70}
                  y={node.y + 36}
                  width="140"
                  height="60"
                  className="node-label-fo"
                >
                  <div className="mesh-node-tag-container">
                    <div className="mesh-node-label">{node.sensorLabel || node.name}</div>
                    <div className="mesh-node-reading-chip">
                      <span className="reading-val">{reading}</span>
                      <span className="trust-pill" style={{ color: nodeColor }}>
                        {overallTrust}%
                      </span>
                    </div>
                  </div>
                </foreignObject>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}

export default memo(MeshTopologyGraph);
