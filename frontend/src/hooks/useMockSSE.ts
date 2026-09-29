import { useState, useEffect, useCallback } from 'react';
import { IncidentEvent } from '../types/events';
import { mockSSESimulator } from '../simulator/mockSSE';

export function useMockSSE() {
  const [events, setEvents] = useState<IncidentEvent[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [isCompleted, setIsCompleted] = useState(false);

  useEffect(() => {
    const unsubscribe = mockSSESimulator.subscribe((newEvent) => {
      setEvents((prev) => [...prev, newEvent]);
      if (newEvent.event_type === 'resolution') {
        setIsRunning(false);
        setIsCompleted(true);
      }
    });

    return () => {
      unsubscribe();
      mockSSESimulator.stop();
    };
  }, []);

  const triggerSimulation = useCallback(() => {
    if (mockSSESimulator.getIsRunning()) return;
    mockSSESimulator.reset();
    setEvents([]);
    setIsCompleted(false);
    setIsRunning(true);
    mockSSESimulator.start();
  }, []);

  const resetSimulation = useCallback(() => {
    mockSSESimulator.reset();
    setEvents([]);
    setIsRunning(false);
    setIsCompleted(false);
  }, []);

  return {
    events,
    isRunning,
    isCompleted,
    triggerSimulation,
    resetSimulation,
  };
}
