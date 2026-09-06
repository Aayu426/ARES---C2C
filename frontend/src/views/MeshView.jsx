import { memo } from "react";
import { Radio, Info, ArrowRight } from "lucide-react";
import MeshTopologyGraph from "../components/MeshTopologyGraph";

function MeshView({ nodes = {}, selectedNodeId, onSelectNode, onNavigate }) {
  const handleNodeClick = (nodeId) => {
    onSelectNode(nodeId);
    onNavigate("inspector");
  };

  return (
    <div className="view-container mesh-view-container">
      {/* Header */}
      <div className="view-header">
        <div>
          <p className="eyebrow">PRIMARY TOPOLOGY SCREEN</p>
          <h2>Graphical Cyber-Physical Mesh</h2>
          <p className="subtitle">
            Full-stage topology graph. Displays edge devices, sensor modalities, peer verification links, and gateway connections.
          </p>
        </div>

        <div className="mesh-hint-badge">
          <Info size={16} />
          <span>Click any node to open full Inspector view</span>
        </div>
      </div>

      {/* Full-Stage Mesh Graph Component */}
      <div className="mesh-fullstage-wrapper">
        <MeshTopologyGraph
          nodes={nodes}
          selectedNodeId={selectedNodeId}
          onSelectNode={handleNodeClick}
        />
      </div>
    </div>
  );
}

export default memo(MeshView);
