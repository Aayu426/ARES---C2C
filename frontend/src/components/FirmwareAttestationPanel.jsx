import { memo } from "react";
import { ShieldCheck, ShieldAlert, Fingerprint, AlertOctagon } from "lucide-react";

/**
 * Firmware Attestation Panel
 * Shows the one parameter common to every sensor and sensitive to compromise regardless of
 * its readings: the firmware fingerprint. ARES attests every node on a fixed cadence, so a
 * DORMANT / SLEEPER compromise — a node whose data stays perfectly normal but whose firmware
 * was tampered to await a later strike — is caught here, not by data-anomaly detection.
 *
 * The 2x2 matrix (data vs firmware) makes the differentiator visible: the "data normal,
 * firmware compromised" cell is only reachable because of this attestation layer.
 */
function FirmwareAttestationPanel({ node }) {
  if (!node) return null;

  const fwCompromised = node.fwStatus === "COMPROMISED";
  const dataAnomalous =
    (node.consistency ?? 100) < 99 || node.state === "SUSPICIOUS";
  const silent = node.silentCompromise;

  return (
    <div className={`fw-attest-panel ${fwCompromised ? "fw-bad" : "fw-ok"}`}>
      <div className="fw-attest-head">
        <Fingerprint size={16} />
        <span>FIRMWARE ATTESTATION</span>
        <span className="fw-cadence">challenged every ~12s · nonce signed</span>
      </div>

      <div className="fw-attest-status">
        {fwCompromised ? (
          <>
            <ShieldAlert size={20} className="text-red" />
            <div>
              <strong className="text-red">FINGERPRINT COMPROMISED</strong>
              <p>{node.fwDetail || "firmware does not match known-good baseline"}</p>
            </div>
          </>
        ) : (
          <>
            <ShieldCheck size={20} className="text-green" />
            <div>
              <strong className="text-green">FINGERPRINT VERIFIED</strong>
              <p>{node.fwDetail || "firmware matches known-good baseline"}</p>
            </div>
          </>
        )}
      </div>

      {silent && (
        <div className="fw-sleeper-callout">
          <AlertOctagon size={16} />
          <div>
            <strong>SLEEPER COMPROMISE CAUGHT</strong>
            <span>
              Data reads perfectly normal and is correctly signed — no anomaly, no
              disagreement. Only the periodic firmware attestation exposed the tamper.
            </span>
          </div>
        </div>
      )}

      {/* Data vs Firmware 2x2 — the differentiator visual */}
      <div className="fw-matrix">
        <div className="fw-matrix-corner">DATA →<br />FIRMWARE ↓</div>
        <div className="fw-matrix-h">NORMAL</div>
        <div className="fw-matrix-h">ANOMALOUS</div>

        <div className="fw-matrix-v">VERIFIED</div>
        <div className={`fw-cell ${!fwCompromised && !dataAnomalous ? "cell-active cell-clean" : ""}`}>
          Clean
        </div>
        <div className={`fw-cell ${!fwCompromised && dataAnomalous ? "cell-active cell-warn" : ""}`}>
          Noisy / data attack
        </div>

        <div className="fw-matrix-v">COMPROMISED</div>
        <div className={`fw-cell fw-cell-key ${fwCompromised && !dataAnomalous ? "cell-active cell-danger" : ""}`}>
          Sleeper compromise
        </div>
        <div className={`fw-cell ${fwCompromised && dataAnomalous ? "cell-active cell-danger" : ""}`}>
          Active compromise
        </div>
      </div>
    </div>
  );
}

export default memo(FirmwareAttestationPanel);
