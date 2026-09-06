import { memo } from "react";
import { ShieldAlert, Radio, Info } from "lucide-react";
import ChallengeFeed from "../components/ChallengeFeed";

function ChallengesView({ events = [] }) {
  return (
    <div className="view-container challenges-view-container">
      <div className="view-header">
        <div>
          <p className="eyebrow">ADAPTIVE CHALLENGE ENGINE (ACE)</p>
          <h2>Live Challenge Reasoning & Cryptographic Audit</h2>
          <p className="subtitle">
            The type of doubt selects the challenge. Nonce signatures prove device identity; SHA-256 partition fingerprints verify unmodified firmware.
          </p>
        </div>

        <div className="view-badge-info text-amber">
          <ShieldAlert size={16} />
          <span>REAL-TIME CHALLENGE MONITOR</span>
        </div>
      </div>

      <div className="challenge-feed-card fullpage-card">
        <ChallengeFeed events={events} />
      </div>
    </div>
  );
}

export default memo(ChallengesView);
