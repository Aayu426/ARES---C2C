import { memo } from "react";
import { FastForward, Gauge } from "lucide-react";
import DriftScrubber from "../components/DriftScrubber";

function DriftView() {
  return (
    <div className="view-container drift-view-container">
      <div className="view-header">
        <div>
          <p className="eyebrow">PHYSICS BASELINE SIMULATOR</p>
          <h2>Accelerated Sensor Drift: 6 Hours in 30 Seconds</h2>
          <p className="subtitle">
            Simulate gradual thermal drift, zero-variance sensor faults, or sudden rate-of-change physics violations to observe consistency debt accumulation.
          </p>
        </div>

        <div className="view-badge-info text-amber">
          <FastForward size={16} />
          <span>720x ACCELERATED DRIFT ENGINE</span>
        </div>
      </div>

      <div className="drift-fullpage-wrapper">
        <DriftScrubber />
      </div>
    </div>
  );
}

export default memo(DriftView);
