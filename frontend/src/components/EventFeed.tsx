import React, { useEffect, useRef } from 'react';
import { Activity, Zap, RefreshCw, Terminal } from 'lucide-react';
import { IncidentEvent } from '../types/events';
import {
  AgentThoughtEventView,
  ToolExecutionEventView,
  GuardrailInterventionEventView,
  ResolutionEventView,
} from './events';

interface EventFeedProps {
  events: IncidentEvent[];
  isRunning: boolean;
  isCompleted: boolean;
  onTrigger: () => void;
  onReset: () => void;
}

export const EventFeed: React.FC<EventFeedProps> = ({
  events,
  isRunning,
  isCompleted,
  onTrigger,
  onReset,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const isNearBottom = scrollHeight - (scrollTop + clientHeight) < 180;
    if (isNearBottom || events.length <= 2) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [events]);

  const renderEvent = (event: IncidentEvent) => {
    switch (event.event_type) {
      case 'agent_thought':
        return <AgentThoughtEventView key={event.event_id} event={event} />;
      case 'tool_execution':
        return <ToolExecutionEventView key={event.event_id} event={event} />;
      case 'guardrail_intervention':
        return <GuardrailInterventionEventView key={event.event_id} event={event} />;
      case 'resolution':
        return <ResolutionEventView key={event.event_id} event={event} />;
      default:
        return null;
    }
  };

  const hasGuardrail = events.some((e) => e.event_type === 'guardrail_intervention');

  return (
    <div className="w-full max-w-4xl mx-auto my-8 space-y-6">
      {/* Control Room Pipeline Status & Action Header */}
      <div className="w-full bg-black/80 border border-white/10 rounded-2xl p-5 backdrop-blur-2xl shadow-[0_0_40px_rgba(0,0,0,0.8)] flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-violet-500/10 border border-violet-500/30 text-violet-400">
            <Activity className="w-5 h-5" />
          </div>
          <div className="text-left">
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold text-white tracking-widest uppercase">
                SOVEREIGNOPS INCIDENT CONTROL FEED
              </span>
              <span
                className={`w-2 h-2 rounded-full ${
                  isRunning
                    ? 'bg-amber-400 animate-ping'
                    : isCompleted
                    ? 'bg-emerald-400'
                    : 'bg-white/20'
                }`}
              />
            </div>
            <div className="flex items-center gap-2 text-[11px] font-mono text-white/50 mt-0.5">
              <span>INC-8891</span>
              <span>•</span>
              <span className="text-white/80 font-semibold">
                {isRunning
                  ? hasGuardrail
                    ? 'SAFETY GATE INTERVENTION ACTIVE'
                    : 'ANALYZING TELEMETRY...'
                  : isCompleted
                  ? 'INCIDENT REMEDIATED'
                  : 'SYSTEM READY'}
              </span>
            </div>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-3">
          <button
            onClick={onTrigger}
            disabled={isRunning}
            className={`px-6 py-3 rounded-xl font-mono text-xs font-bold uppercase tracking-widest transition-all duration-300 flex items-center gap-2 cursor-pointer ${
              isRunning
                ? 'bg-white/10 text-white/40 border border-white/10 cursor-not-allowed'
                : 'bg-gradient-to-r from-violet-600 via-indigo-600 to-violet-600 hover:from-violet-500 hover:to-indigo-500 text-white border border-violet-400/40 shadow-[0_0_30px_rgba(124,58,237,0.35)] active:scale-95'
            }`}
          >
            {isRunning ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin text-amber-400" />
                <span>PROCESSING INCIDENT...</span>
              </>
            ) : (
              <>
                <Zap className="w-4 h-4 text-amber-300" />
                <span>{isCompleted ? 'RE-TRIGGER ALERT' : 'TRIGGER ALERT'}</span>
              </>
            )}
          </button>

          {(events.length > 0 || isCompleted) && (
            <button
              onClick={onReset}
              disabled={isRunning}
              className="px-4 py-3 rounded-xl font-mono text-xs font-semibold text-white/50 hover:text-white bg-white/5 hover:bg-white/10 border border-white/10 transition-colors cursor-pointer disabled:opacity-30"
            >
              RESET
            </button>
          )}
        </div>
      </div>

      {/* Control Room Live Event Stream Panel */}
      <div
        ref={containerRef}
        className="w-full max-h-[720px] overflow-y-auto pr-2 space-y-5 scrollbar-thin scrollbar-thumb-white/20 scrollbar-track-transparent"
      >
        {events.length === 0 ? (
          <div className="w-full bg-black/60 border border-dashed border-white/15 rounded-2xl p-12 text-center space-y-4 backdrop-blur-xl">
            <div className="w-12 h-12 rounded-full bg-white/5 border border-white/10 flex items-center justify-center mx-auto text-white/40">
              <Terminal className="w-6 h-6" />
            </div>
            <div className="space-y-1">
              <div className="font-mono text-xs text-white/80 font-bold uppercase tracking-widest">
                SYSTEM READY • AWAITING INCIDENT ALERT
              </div>
              <p className="font-sans text-xs text-white/40 max-w-md mx-auto leading-relaxed">
                Click <strong className="text-violet-400 font-semibold">TRIGGER ALERT</strong> above to launch the Caged ReAct reasoning loop and observe live telemetry diagnostics, guardrail safety interventions, and provenance runbook matching.
              </p>
            </div>
          </div>
        ) : (
          events.map((event) => (
            <div key={event.event_id} className="relative pl-6 border-l-2 border-white/10 space-y-2">
              {/* Timeline Indicator Badge */}
              <div
                className={`absolute -left-[9px] top-4 w-4 h-4 rounded-full bg-black border-2 flex items-center justify-center ${
                  event.event_type === 'guardrail_intervention'
                    ? 'border-amber-400 bg-amber-950/80 shadow-[0_0_10px_rgba(245,158,11,0.6)]'
                    : event.event_type === 'resolution'
                    ? 'border-emerald-400 bg-emerald-950/80 shadow-[0_0_10px_rgba(16,185,129,0.6)]'
                    : 'border-violet-400'
                }`}
              >
                <div
                  className={`w-1.5 h-1.5 rounded-full ${
                    event.event_type === 'guardrail_intervention'
                      ? 'bg-amber-400'
                      : event.event_type === 'resolution'
                      ? 'bg-emerald-400'
                      : 'bg-violet-400'
                  }`}
                />
              </div>

              {/* Event Metadata Header */}
              <div className="flex items-center justify-between font-mono text-[10px] text-white/40 px-1">
                <span className="flex items-center gap-2">
                  <strong className="text-white/70 font-semibold">{event.event_id}</strong>
                  <span>•</span>
                  <span
                    className={
                      event.event_type === 'guardrail_intervention'
                        ? 'text-amber-400 font-bold'
                        : event.event_type === 'resolution'
                        ? 'text-emerald-400 font-bold'
                        : 'text-white/50'
                    }
                  >
                    {event.event_type.toUpperCase()}
                  </span>
                </span>
                <span>{new Date(event.timestamp).toLocaleTimeString()}</span>
              </div>

              {/* Component View */}
              {renderEvent(event)}
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
};
