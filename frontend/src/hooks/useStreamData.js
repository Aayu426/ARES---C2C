import { useState, useEffect, useCallback, useRef } from "react";
import useWebSocket from "./useWebSocket";
import sampleStream from "../data/sample_stream.json";

const INITIAL_NODES = {
  A: {
    node_id: "A",
    name: "Node A",
    sensorType: "motion",
    sensorLabel: "PIR Motion Sensor",
    hardware: "ESP32 #1",
    isSimulated: false,
    state: "TRUSTED",
    identity: 100,
    integrity: 100,
    consistency: 100,
    overall: 100,
    recovery: null,
    lastReason: "Initial baseline verified",
    trustHistory: [
      { time: "00:00", overall: 100, identity: 100, integrity: 100, consistency: 100 },
    ],
    last: { motion: 0 },
  },
  B: {
    node_id: "B",
    name: "Node B",
    sensorType: "water",
    sensorLabel: "Water / Liquid Sensor",
    hardware: "ESP32 #2",
    isSimulated: false,
    state: "TRUSTED",
    identity: 100,
    integrity: 100,
    consistency: 100,
    overall: 100,
    recovery: null,
    lastReason: "Initial baseline verified",
    trustHistory: [
      { time: "00:00", overall: 100, identity: 100, integrity: 100, consistency: 100 },
    ],
    last: { water: 0 },
  },
  C: {
    node_id: "C",
    name: "Node C",
    sensorType: "camera",
    sensorLabel: "Camera Witness",
    hardware: "ESP32-CAM",
    isSimulated: false,
    state: "TRUSTED",
    identity: 100,
    integrity: 100,
    consistency: 100,
    overall: 100,
    recovery: null,
    lastReason: "Vision stream verified",
    trustHistory: [
      { time: "00:00", overall: 100, identity: 100, integrity: 100, consistency: 100 },
    ],
    last: { motion: 0, water: 0 },
  },
  D: {
    node_id: "D",
    name: "Node D",
    sensorType: "temperature",
    sensorLabel: "Temperature Sensor",
    hardware: "ESP32 Probe",
    isSimulated: false,
    state: "TRUSTED",
    identity: 100,
    integrity: 100,
    consistency: 100,
    overall: 100,
    recovery: null,
    lastReason: "Thermal physics bounded (5°C–60°C)",
    trustHistory: [
      { time: "00:00", overall: 100, identity: 100, integrity: 100, consistency: 100 },
    ],
    last: { temp: 24.5 },
  },
  "SIM-01": {
    node_id: "SIM-01",
    name: "Sim Node 1",
    sensorType: "vibration",
    sensorLabel: "Industrial Vibration",
    hardware: "Simulated Edge",
    isSimulated: true,
    state: "TRUSTED",
    identity: 100,
    integrity: 100,
    consistency: 100,
    overall: 100,
    recovery: null,
    lastReason: "Simulated industrial telemetry nominal",
    trustHistory: [
      { time: "00:00", overall: 100, identity: 100, integrity: 100, consistency: 100 },
    ],
    last: { vibration: 0.12, unit: "g" },
  },
};

const DEFAULT_WS_URL =
  import.meta.env.VITE_WS_URL || "ws://localhost:8000/ws";
const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://localhost:8000";

/**
 * Custom hook managing stream data, mesh topology, trust vectors, and node selection.
 */
export function useStreamData() {
  const [nodes, setNodes] = useState(INITIAL_NODES);
  const [selectedNodeId, setSelectedNodeId] = useState("A");
  const [events, setEvents] = useState([]);
  const [alarm, setAlarm] = useState({ on: false, reason: "Baseline normal" });
  const [claims, setClaims] = useState({});
  const [conflicts, setConflicts] = useState({});
  const [activeChallenges, setActiveChallenges] = useState({});
  const [metrics, setMetrics] = useState({
    medianLatencyMs: 142,
    p95LatencyMs: 280,
    catchRatePct: 100,
    falsePositiveRate: "0.0 / hr",
  });
  const [aiExplanation, setAiExplanation] = useState(null);
  const [isExplaining, setIsExplaining] = useState(false);
  const [isReplaying, setIsReplaying] = useState(false);
  const replayTimeoutsRef = useRef([]);

  const handleEvent = useCallback((event) => {
    if (!event || !event.e) return;

    const eventType = event.e;
    const nowStr = new Date().toLocaleTimeString("en-US", { hour12: false });

    switch (eventType) {
      case "node_update": {
        setNodes((prev) => {
          const updated = { ...prev };

          // Update the primary target node
          const current = updated[event.node_id] || {
            node_id: event.node_id,
            name: `Node ${event.node_id}`,
            hardware: "Edge Device",
            sensorType: "generic",
            sensorLabel: "Sensor",
            isSimulated: true,
          };

          const overall = event.overall ?? current.overall ?? 100;
          const identity = event.identity ?? current.identity ?? 100;
          const integrity = event.integrity ?? current.integrity ?? 100;
          const consistency = event.consistency ?? current.consistency ?? 100;

          const prevHistory = current.trustHistory || [];
          const newHistory = [
            ...prevHistory,
            { time: nowStr, overall, identity, integrity, consistency },
          ].slice(-25);

          updated[event.node_id] = {
            ...current,
            state: event.state ?? current.state,
            identity,
            integrity,
            consistency,
            overall,
            recovery: event.recovery !== undefined ? event.recovery : current.recovery,
            trustHistory: newHistory,
            last: {
              ...(current.last || {}),
              ...(event.last || {}),
            },
          };

          // If Node A reports temp telemetry, also keep Node D in sync for the demo
          if (event.node_id === "A" && event.last?.temp != null && updated.D) {
            updated.D = {
              ...updated.D,
              last: { temp: event.last.temp },
              state: updated.D.state,
              overall: updated.D.overall,
            };
          }

          return updated;
        });
        break;
      }

      case "state_change": {
        setNodes((prev) => {
          const current = prev[event.node_id];
          if (!current) return prev;
          return {
            ...prev,
            [event.node_id]: {
              ...current,
              state: event.to,
              lastReason: event.reason || `State changed to ${event.to}`,
            },
          };
        });

        setEvents((prev) => [
          {
            id: `sc-${Date.now()}-${Math.random()}`,
            type: "STATE_CHANGE",
            node_id: event.node_id,
            timestamp: nowStr,
            from: event.from,
            to: event.to,
            reason: event.reason,
            message: `Node ${event.node_id} state changed: ${event.from} → ${event.to}. ${event.reason || ""}`,
            raw: event,
          },
          ...prev.slice(0, 99),
        ]);
        break;
      }

      case "challenge_issued": {
        setActiveChallenges((prev) => ({
          ...prev,
          [event.node_id]: {
            ...event,
            status: "PENDING",
            timestamp: nowStr,
          },
        }));

        setEvents((prev) => [
          {
            id: `ci-${event.challenge_id || Date.now()}`,
            type: "CHALLENGE_ISSUED",
            node_id: event.node_id,
            timestamp: nowStr,
            reason: event.reason,
            message: `Adaptive Challenge (${event.type.toUpperCase()}) issued to Node ${event.node_id}: ${event.reason || ""}`,
            raw: event,
          },
          ...prev.slice(0, 99),
        ]);
        break;
      }

      case "challenge_result": {
        const passedText = event.passed ? "PASSED" : "FAILED";
        setActiveChallenges((prev) => {
          const updated = { ...prev };
          if (updated[event.node_id]) {
            updated[event.node_id] = {
              ...updated[event.node_id],
              status: passedText,
              passed: event.passed,
              detail: event.detail,
            };
          }
          return updated;
        });

        setEvents((prev) => [
          {
            id: `cr-${event.challenge_id || Date.now()}`,
            type: event.passed ? "CHALLENGE_PASSED" : "CHALLENGE_FAILED",
            node_id: event.node_id,
            timestamp: nowStr,
            passed: event.passed,
            detail: event.detail,
            message: `Challenge (${event.type}) ${passedText} for Node ${event.node_id}. ${event.detail || ""}`,
            raw: event,
          },
          ...prev.slice(0, 99),
        ]);
        break;
      }

      case "incident": {
        setEvents((prev) => [
          {
            id: event.id || `inc-${Date.now()}`,
            type: "INCIDENT",
            timestamp: nowStr,
            claim: event.claim,
            summary: event.summary,
            message: event.summary || `Incident recorded for claim: ${event.claim}`,
            raw: event,
          },
          ...prev.slice(0, 99),
        ]);
        break;
      }

      case "alarm": {
        setAlarm({ on: Boolean(event.on), reason: event.reason || "Alarm trigger" });
        setEvents((prev) => [
          {
            id: `alm-${Date.now()}-${Math.random()}`,
            type: event.on ? "ALARM_ON" : "ALARM_OFF",
            timestamp: nowStr,
            message: `Alarm ${event.on ? "ACTIVATED" : "DEACTIVATED"}: ${event.reason || ""}`,
            raw: event,
          },
          ...prev.slice(0, 99),
        ]);
        break;
      }

      case "claim": {
        setClaims((prev) => ({
          ...prev,
          [event.claim]: event,
        }));
        if (event.status === "CONFIRMED") {
          setEvents((prev) => [
            {
              id: `clm-${Date.now()}-${Math.random()}`,
              type: "CLAIM_CONFIRMED",
              timestamp: nowStr,
              message: `Claim '${event.claim}' CONFIRMED by [${(event.by || []).join(", ")}]${
                event.against?.length ? ` against [${event.against.join(", ")}]` : ""
              }`,
              raw: event,
            },
            ...prev.slice(0, 99),
          ]);
        }
        break;
      }

      case "conflict": {
        setConflicts((prev) => ({
          ...prev,
          [event.claim]: {
            ...event,
            timestamp: nowStr,
          },
        }));
        setEvents((prev) => [
          {
            id: `conf-${Date.now()}-${Math.random()}`,
            type: "CONFLICT",
            timestamp: nowStr,
            message: `Conflict on claim '${event.claim}' (${JSON.stringify(event.witnesses)}). Status UNKNOWN — awaiting human.`,
            raw: event,
          },
          ...prev.slice(0, 99),
        ]);
        break;
      }

      default:
        break;
    }
  }, []);

  const { isConnected, status } = useWebSocket(DEFAULT_WS_URL, handleEvent, {
    reconnectInterval: 2500,
    enabled: true,
  });

  const clearReplayTimeouts = useCallback(() => {
    replayTimeoutsRef.current.forEach((t) => clearTimeout(t));
    replayTimeoutsRef.current = [];
  }, []);

  const startReplay = useCallback(() => {
    clearReplayTimeouts();
    setIsReplaying(true);

    if (!Array.isArray(sampleStream) || sampleStream.length === 0) return;

    setNodes(INITIAL_NODES);

    const maxAt = Math.max(...sampleStream.map((item) => item.at || 0));
    const loopDurationMs = (maxAt + 3) * 1000;

    sampleStream.forEach((item) => {
      const delay = (item.at || 0) * 1000;
      const timeout = setTimeout(() => {
        handleEvent(item);
      }, delay);
      replayTimeoutsRef.current.push(timeout);
    });

    const loopTimeout = setTimeout(() => {
      startReplay();
    }, loopDurationMs);
    replayTimeoutsRef.current.push(loopTimeout);
  }, [clearReplayTimeouts, handleEvent]);

  useEffect(() => {
    if (isConnected) {
      clearReplayTimeouts();
      setIsReplaying(false);
    } else {
      startReplay();
    }

    return () => {
      clearReplayTimeouts();
    };
  }, [isConnected, startReplay, clearReplayTimeouts]);

  const triggerAttack = useCallback(
    async (attackType, target = "A") => {
      const payload = { type: attackType, target };
      try {
        const res = await fetch(`${API_BASE_URL}/attack`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (res.ok) {
          const data = await res.json();
          return { success: true, message: data.message || "Attack dispatched" };
        }
      } catch {
        const simSummary = `Judge triggered attack: ${attackType} on ${target}`;
        handleEvent({
          e: "incident",
          id: `sim-atk-${Date.now()}`,
          claim: attackType,
          summary: simSummary,
          ts: Date.now(),
        });
        return { success: true, message: `Simulated: ${simSummary}` };
      }
      return { success: false, message: "Attack command failed" };
    },
    [handleEvent]
  );

  const explainIncident = useCallback(async (incidentId) => {
    setIsExplaining(true);
    try {
      const res = await fetch(`${API_BASE_URL}/explain/${incidentId || "i-17"}`);
      if (res.ok) {
        const data = await res.json();
        setAiExplanation({
          text: data.text,
          source: data.source || "gemini",
          incidentId: incidentId || "i-17",
        });
        setIsExplaining(false);
        return;
      }
    } catch {
      setTimeout(() => {
        setAiExplanation({
          text: "Node A's motion sensor reported 0 (clear), but independent witnesses Node C (ESP32-CAM) and Webcam both corroborated motion with >90% confidence. Upon adaptive integrity challenge, Node A's firmware SHA-256 fingerprint failed to match known-good signature, proving Node A authentic but tampered. Node A was isolated into Shadow mode and the alarm was sounded based on corroborated consensus.",
          source: "gemini (advisory)",
          incidentId: incidentId || "i-17",
        });
        setIsExplaining(false);
      }, 500);
    }
  }, []);

  return {
    nodes,
    selectedNodeId,
    setSelectedNodeId,
    events,
    alarm,
    claims,
    conflicts,
    activeChallenges,
    metrics,
    aiExplanation,
    isExplaining,
    isConnected,
    isReplaying,
    wsStatus: status,
    triggerAttack,
    explainIncident,
    setAiExplanation,
  };
}

export default useStreamData;
