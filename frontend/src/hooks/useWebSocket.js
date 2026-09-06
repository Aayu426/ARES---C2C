import { useEffect, useRef, useState, useCallback } from "react";

/**
 * Reusable WebSocket hook with automatic reconnection and lifecycle management.
 * 
 * @param {string} url - WebSocket server endpoint
 * @param {Function} onMessage - Callback triggered on receiving a message
 * @param {Object} options - Configuration options (reconnectInterval, enabled)
 */
export function useWebSocket(url, onMessage, options = {}) {
  const { reconnectInterval = 3000, enabled = true } = options;
  const [status, setStatus] = useState("DISCONNECTED"); // "CONNECTING" | "CONNECTED" | "DISCONNECTED"
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const onMessageRef = useRef(onMessage);
  const unmountedRef = useRef(false);

  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  const connect = useCallback(() => {
    if (!enabled || !url || unmountedRef.current) return;

    if (wsRef.current) {
      try {
        wsRef.current.close();
      } catch {
        // Ignore close error during reconnect
      }
    }

    setStatus("CONNECTING");
    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (unmountedRef.current) {
          ws.close();
          return;
        }
        setStatus("CONNECTED");
      };

      ws.onmessage = (event) => {
        if (unmountedRef.current) return;
        try {
          const data = JSON.parse(event.data);
          if (onMessageRef.current) {
            onMessageRef.current(data);
          }
        } catch (err) {
          console.error("[WebSocket] Failed to parse message:", err);
        }
      };

      ws.onclose = () => {
        if (unmountedRef.current) return;
        setStatus("DISCONNECTED");
        wsRef.current = null;
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
        }
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, reconnectInterval);
      };

      ws.onerror = (err) => {
        console.warn("[WebSocket] Connection error, will retry:", err);
      };
    } catch {
      setStatus("DISCONNECTED");
      if (!unmountedRef.current) {
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, reconnectInterval);
      }
    }
  }, [url, enabled, reconnectInterval]);

  useEffect(() => {
    unmountedRef.current = false;
    connect();

    return () => {
      unmountedRef.current = true;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  const sendMessage = useCallback((msg) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(typeof msg === "string" ? msg : JSON.stringify(msg));
    }
  }, []);

  return {
    status,
    isConnected: status === "CONNECTED",
    sendMessage,
  };
}

export default useWebSocket;
