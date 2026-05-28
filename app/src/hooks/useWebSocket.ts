import { useEffect, useRef, useState, useCallback } from 'react';

export interface WSEvent {
  event: string;
  project_id: string;
  payload: Record<string, unknown>;
}

const MAX_RECONNECT_ATTEMPTS = 5;

export function useWebSocket() {
  const [events, setEvents] = useState<WSEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const unmountedRef = useRef(false);

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (unmountedRef.current) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    if (reconnectAttemptsRef.current >= MAX_RECONNECT_ATTEMPTS) {
      console.warn('[WebSocket] Max reconnect attempts reached');
      return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/events`);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      reconnectAttemptsRef.current = 0;
      ws.send(JSON.stringify({ action: 'subscribe' }));
    };

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data) as WSEvent;
        setEvents((prev) => [data, ...prev].slice(0, 200));
      } catch {
        // ignore non-JSON
      }
    };

    ws.onclose = () => {
      setConnected(false);
      wsRef.current = null;
      if (unmountedRef.current) return;

      reconnectAttemptsRef.current += 1;
      if (reconnectAttemptsRef.current > MAX_RECONNECT_ATTEMPTS) {
        console.warn('[WebSocket] Max reconnect attempts reached');
        return;
      }

      // 指数退避: 1s -> 2s -> 4s -> 8s -> 16s
      const delay = Math.min(1000 * 2 ** (reconnectAttemptsRef.current - 1), 16000);
      reconnectTimerRef.current = setTimeout(() => connect(), delay);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, []);

  useEffect(() => {
    unmountedRef.current = false;
    reconnectAttemptsRef.current = 0;
    connect();
    return () => {
      unmountedRef.current = true;
      clearReconnectTimer();
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [connect, clearReconnectTimer]);

  return { events, connected, clearEvents: () => setEvents([]) };
}
