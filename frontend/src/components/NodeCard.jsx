import {
  ShieldCheck,
  ShieldAlert,
  Thermometer,
  Droplets,
  Activity,
} from "lucide-react";

function getStateClass(state) {
  switch (state) {
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
      return "";
  }
}

function NodeCard({ node }) {
  const stateClass = getStateClass(node.state);

  const Icon =
    node.state === "TRUSTED" ? ShieldCheck : ShieldAlert;

  return (
    <article className={`node-card ${stateClass}`}>
      <div className="node-card-header">
        <div className="node-identity">
          <div className="node-icon">
            <Icon size={20} />
          </div>

          <div>
            <h4>NODE {node.node_id}</h4>
            <span>ESP32 SENSOR NODE</span>
          </div>
        </div>

        <span className={`state-badge ${stateClass}`}>
          {node.state}
        </span>
      </div>

      <div className="node-divider" />

      <div className="readings">
        <div className="reading">
          <Droplets size={17} />
          <div>
            <span>WATER</span>
            <strong>{node.water ?? "--"}</strong>
          </div>
        </div>

        <div className="reading">
          <Thermometer size={17} />
          <div>
            <span>TEMPERATURE</span>
            <strong>
              {node.temp_c != null ? `${node.temp_c}°C` : "--"}
            </strong>
          </div>
        </div>

        <div className="reading">
          <Activity size={17} />
          <div>
            <span>MOTION</span>
            <strong>
              {node.motion ? "DETECTED" : "CLEAR"}
            </strong>
          </div>
        </div>
      </div>

      <div className="trust-preview">
        <div className="trust-label">
          <span>TRUST</span>
          <strong>{node.trust ?? 100}%</strong>
        </div>

        <div className="trust-track">
          <div
            className="trust-fill"
            style={{ width: `${node.trust ?? 100}%` }}
          />
        </div>
      </div>

      <div className="node-footer">
        <span>SEQ {node.seq ?? "--"}</span>
        <span>● CONNECTED</span>
      </div>
    </article>
  );
}

export default NodeCard;