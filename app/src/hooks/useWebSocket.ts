import { useEffect, useRef, useState, useCallback } from 'react';

export interface WSEvent {
  event: string;
  project_id: string;
  payload: Record<string, unknown>;
}

const MAX_RECONNECT_ATTEMPTS = 5;

export function useWebSocket(projectId?: string) {
  const [events, setEvents] = useState<WSEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const unmountedRef = useRef(false);
  const projectIdRef = useRef(projectId);

  // 保持 projectId 最新
  projectIdRef.current = projectId;

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const sendSubscribe = useCallback(() => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    const pid = projectIdRef.current;
    if (pid) {
      ws.send(JSON.stringify({ action: 'subscribe', project_id: pid }));
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
      sendSubscribe();
    };

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        // 忽略订阅确认消息，只处理真实事件
        if (data.type === 'subscribed' || data.type === 'pong') return;
        const eventData = data as WSEvent;
        // 只接收与当前 projectId 匹配的事件
        const pid = projectIdRef.current;
        if (pid && eventData.project_id && eventData.project_id !== pid) return;
        setEvents((prev) => [eventData, ...prev].slice(0, 200));
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
  }, [sendSubscribe]);

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

  // projectId 变化时重新订阅
  useEffect(() => {
    sendSubscribe();
  }, [projectId, sendSubscribe]);

  return { events, connected, clearEvents: () => setEvents([]) };
}
