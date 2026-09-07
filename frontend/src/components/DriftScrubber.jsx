import { useState, memo } from "react";
import { FastForward, Clock, Gauge } from "lucide-react";

/**
 * Drift Scrubber Component
 * Visualizes accelerated time drift: "6 HOURS IN 30 SECONDS"
 */
function DriftScrubber() {
  const [driftValue, setDriftValue] = useState(0); // 0 to 100%
  const [isPlaying, setIsPlaying] = useState(false);

  // Compute simulated hours and drift offset
  const simulatedHours = ((driftValue / 100) * 6).toFixed(1);
  const simulatedTempOffset = ((driftValue / 100) * 4.2).toFixed(2);
  const simulatedPIRDrift = (driftValue * 0.8).toFixed(0);

  const handleSliderChange = (e) => {
    setDriftValue(Number(e.target.value));
  };

  const handleQuickPreset = (pct) => {
    setDriftValue(pct);
  };

  return (
    <div className="drift-scrubber-card">
      <div className="drift-header">
        <div className="drift-title">
          <FastForward size={17} className="text-amber" />
          <div>
            <h4>ACCELERATED DRIFT TIMELINE</h4>
            <span>6 HOURS IN 30 SECONDS (PHYSICS BASELINE SIMULATOR)</span>
          </div>
        </div>

        <div className="simulated-time-badge">
          <Clock size={13} />
          <span>T+ {simulatedHours} HOURS</span>
        </div>
      </div>

      <div className="scrubber-control-row">
        <input
          type="range"
          min="0"
          max="100"
          value={driftValue}
          onChange={handleSliderChange}
          className="drift-slider"
        />
      </div>

      <div className="drift-metrics-summary">
        <div className="drift-metric-box">
          <span>TIME COMPRESSION</span>
          <strong>720x ACCELERATED</strong>
        </div>

        <div className="drift-metric-box">
          <span>THERMAL SENSOR DRIFT</span>
          <strong className={driftValue > 50 ? "text-amber" : "text-green"}>
            +{simulatedTempOffset} °C BIAS
          </strong>
        </div>

        <div className="drift-metric-box">
          <span>CONSISTENCY DEBT</span>
          <strong className={driftValue > 75 ? "text-red" : "text-green"}>
            +{simulatedPIRDrift} PTS
          </strong>
        </div>
      </div>

      <div className="scrubber-presets">
        <button onClick={() => handleQuickPreset(0)}>T+ 0h (Nominal)</button>
        <button onClick={() => handleQuickPreset(33)}>T+ 2h (Subtle Drift)</button>
        <button onClick={() => handleQuickPreset(66)}>T+ 4h (Threshold Alert)</button>
        <button onClick={() => handleQuickPreset(100)}>T+ 6h (Physics Violation)</button>
      </div>
    </div>
  );
}

export default memo(DriftScrubber);
