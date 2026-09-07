import { memo } from "react";
import { ShieldAlert, ShieldCheck, Cpu, ArrowRight, Radio } from "lucide-react";

/**
 * Live Challenge Reasoning Feed (Adaptive Challenge Engine)
 * Explains WHY a challenge was picked and its cryptographic outcome.
 */
function ChallengeFeed({ events = [] }) {
  // Filter events relevant to challenges and state changes
  const challengeEvents = events
    .filter(
      (e) =>
        e.type === "CHALLENGE_ISSUED" ||
        e.type === "CHALLENGE_PASSED" ||
        e.type === "CHALLENGE_FAILED" ||
        e.raw?.e === "challenge_issued" ||
        e.raw?.e === "challenge_result"
    )
    .slice(0, 6);

  if (!challengeEvents.length) {
    return (
      <div className="empty-feed">
        <Radio size={16} />
        <span>No active challenge queries. Baseline monitoring nominal.</span>
      </div>
    );
  }

  return (
    <div className="challenge-feed-list">
      {challengeEvents.map((item, idx) => {
        const isResult =
          item.type === "CHALLENGE_PASSED" ||
          item.type === "CHALLENGE_FAILED" ||
          item.raw?.e === "challenge_result";
        const passed = item.passed || item.type === "CHALLENGE_PASSED";
        const type = item.raw?.type || "integrity";

        return (
          <div
            className={`challenge-item ${
              isResult ? (passed ? "challenge-pass" : "challenge-fail") : "challenge-issue"
            }`}
            key={item.id || idx}
          >
            <div className="challenge-item-icon">
              {isResult ? (
                passed ? (
                  <ShieldCheck size={16} />
                ) : (
                  <ShieldAlert size={16} />
                )
              ) : (
                <Cpu size={16} />
              )}
            </div>

            <div className="challenge-item-content">
              <div className="challenge-header">
                <span className="challenge-badge">
                  {isResult
                    ? passed
                      ? "CHALLENGE PASSED"
                      : "CHALLENGE FAILED"
                    : `ADAPTIVE CHALLENGE (${type.toUpperCase()})`}
                </span>
                <span className="challenge-time">{item.timestamp}</span>
                {item.node_id && (
                  <span className="challenge-node-tag">TARGET: NODE {item.node_id}</span>
                )}
              </div>

              <p className="challenge-text">
                {item.reason || item.detail || item.message}
              </p>

              {item.raw?.challenge_id && (
                <div className="challenge-id-meta">
                  <span>ID: {item.raw.challenge_id}</span>
                  <ArrowRight size={10} />
                  <span>
                    {type === "identity"
                      ? "Nonce Signature Proof"
                      : "Partition SHA-256 Fingerprint Check"}
                  </span>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default memo(ChallengeFeed);
