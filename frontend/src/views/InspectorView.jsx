import { memo } from "react";
import { ArrowLeft, Cpu, Radio } from "lucide-react";
import NodeDetailInspector from "../components/NodeDetailInspector";

function InspectorView({
  nodes = {},
  selectedNodeId,
  onSelectNode,
  onNavigate,
  events = [],
}) {
  const node = nodes[selectedNodeId] || nodes.A || Object.values(nodes)[0];

  // Filter events related to this specific node
  const nodeEvents = events.filter(
    (e) =>
      e.node_id === node?.node_id ||
      e.raw?.node_id === node?.node_id ||
      e.message?.includes(`Node ${node?.node_id}`)
  );

  return (
    <div className="view-container inspector-view-container">
      {/* Top Back Navigation & Header */}
      <div className="inspector-view-topbar">
        <button
          className="back-to-mesh-btn"
          onClick={() => onNavigate("mesh")}
        >
          <ArrowLeft size={16} />
          <span>← BACK TO MESH TOPOLOGY</span>
        </button>

        <div className="inspector-view-title-block">
          <span className="eyebrow">DEEP TELEMETRY & TRUST AUDIT</span>
          <h2>Node {node?.node_id} Forensic Inspector</h2>
        </div>
      </div>

      {/* Main Inspector Component */}
      <div className="inspector-fullpage-content">
        <NodeDetailInspector
          node={node}
          allNodes={nodes}
          onSelectNode={onSelectNode}
        />

        {/* Node-Specific Recent Event History */}
        <div className="node-events-card">
          <div className="card-heading-row">
            <Radio size={16} className="text-blue" />
            <h3>Recent Node {node?.node_id} Audit Log</h3>
          </div>

          <div className="node-events-list">
            {nodeEvents.slice(0, 5).map((ev, i) => (
              <div className="node-event-row" key={ev.id || i}>
                <span className="event-row-time">{ev.timestamp}</span>
                <span className="event-row-type">{ev.type}</span>
                <p className="event-row-msg">{ev.message || ev.reason}</p>
              </div>
            ))}
            {nodeEvents.length === 0 && (
              <div className="empty-node-events">
                <span>No node-specific security faults recorded for Node {node?.node_id}.</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default memo(InspectorView);
