import { useEffect, useRef, useState, useCallback } from "react";
import type { WsEvent } from "../types";

type Status = "connecting" | "connected" | "disconnected" | "error";

interface UseWebSocketReturn {
  events: WsEvent[];
  status: Status;
  clear: () => void;
}

/**
 * Subscribes to a backend WebSocket endpoint and accumulates received JSON
 * events.  Automatically reconnects (up to maxRetries) on unexpected closure.
 *
 * Path examples:
 *   /ws/logs/{workflowId}
 *   /ws/agent-status/{agentId}
 */
export function useWebSocket(path: string | null, maxRetries = 5): UseWebSocketReturn {
  const [events, setEvents] = useState<WsEvent[]>([]);
  const [status, setStatus] = useState<Status>("disconnected");
  const wsRef   = useRef<WebSocket | null>(null);
  const retries = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clear = useCallback(() => setEvents([]), []);

  useEffect(() => {
    if (!path) return;

    // Build ws:// or wss:// URL from the current page origin
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const url = `${protocol}://${window.location.host}${path}`;

    function connect() {
      setStatus("connecting");
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setStatus("connected");
        retries.current = 0;
      };

      ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data) as WsEvent;
          setEvents(prev => [...prev, data]);
        } catch { /* ignore non-JSON frames */ }
      };

      ws.onerror = () => setStatus("error");

      ws.onclose = (e) => {
        if (e.wasClean) {
          setStatus("disconnected");
          return;
        }
        if (retries.current < maxRetries) {
          retries.current++;
          const delay = Math.min(1000 * 2 ** retries.current, 30_000);
          timerRef.current = setTimeout(connect, delay);
        } else {
          setStatus("error");
        }
      };
    }

    connect();
    return () => {
      wsRef.current?.close(1000, "component unmounted");
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [path, maxRetries]);

  return { events, status, clear };
}
