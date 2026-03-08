/**
 * SSE hook — wraps EventSource with connect/disconnect control.
 * All components MUST use this hook; no raw EventSource elsewhere.
 */

import { useRef } from "react";

type SSECallback = (data: unknown) => void;

export function useSSE(url: string, onMessage: SSECallback) {
  const esRef = useRef<EventSource | null>(null);

  function connect() {
    if (esRef.current) return;
    const es = new EventSource(url);
    esRef.current = es;

    es.onmessage = (event) => {
      try {
        onMessage(event.data);
      } catch {
        // silently skip malformed events
      }
    };

    es.onerror = () => {
      es.close();
      esRef.current = null;
    };
  }

  function disconnect() {
    esRef.current?.close();
    esRef.current = null;
  }

  return { connect, disconnect };
}
