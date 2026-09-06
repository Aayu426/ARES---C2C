import { memo } from "react";
import { KeyRound, ShieldCheck, Sparkles, Scale } from "lucide-react";

/**
 * Trust Vector Panel
 * Visualizes the mathematical breakdown of trust:
 * overall = 0.35*identity + 0.35*integrity + 0.30*consistency
 */
function TrustVectorPanel({ node }) {
  if (!node) return null;

  const identity = node.identity ?? 100;
  const integrity = node.integrity ?? 100;
  const consistency = node.consistency ?? 100;
  const overall = node.overall ?? 100;

  const getBarColor = (val) => {
    if (val >= 70) return "#67b58a"; // Green
    if (val >= 40) return "#c7a96b"; // Amber
    return "#e06c75"; // Red
  };

  const vectorComponents = [
    {
      id: "identity",
      label: "IDENTITY (HMAC)",
      weight: "35%",
      value: identity,
      icon: <KeyRound size={13} />,
      color: getBarColor(identity),
      desc: "Cryptographic proof (key validity)",
    },
    {
      id: "integrity",
      label: "INTEGRITY (FW)",
      weight: "35%",
      value: integrity,
      icon: <ShieldCheck size={13} />,
      color: getBarColor(integrity),
      desc: "SHA-256 firmware fingerprint",
    },
    {
      id: "consistency",
      label: "CONSISTENCY",
      weight: "30%",
      value: consistency,
      icon: <Scale size={13} />,
      color: getBarColor(consistency),
      desc: "Multi-witness & physics consensus",
    },
  ];

  return (
    <div className="trust-vector-panel">
      <div className="trust-vector-header">
        <span className="vector-title">
          <Sparkles size={12} />
          TRUST VECTOR DECOMPOSITION
        </span>
        <span className="vector-formula">0.35·Id + 0.35·Int + 0.30·Con</span>
      </div>

      <div className="vector-bars">
        {vectorComponents.map((c) => (
          <div className="vector-row" key={c.id}>
            <div className="vector-row-header">
              <span className="vector-label">
                {c.icon}
                {c.label}
                <small>({c.weight})</small>
              </span>
              <strong style={{ color: c.color }}>{c.value}</strong>
            </div>

            <div className="vector-track">
              <div
                className="vector-fill"
                style={{
                  width: `${Math.max(0, Math.min(100, c.value))}%`,
                  backgroundColor: c.color,
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default memo(TrustVectorPanel);
