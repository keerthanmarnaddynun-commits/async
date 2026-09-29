import React from 'react';
import { Wrench, Clock, CheckCircle2, AlertCircle, PlayCircle } from 'lucide-react';
import { ToolExecutionEvent } from '../../types/events';

interface Props {
  event: ToolExecutionEvent;
}

export const ToolExecutionEventView: React.FC<Props> = ({ event }) => {
  const { tool_name, tool_source, input_parameters, status, execution_latency_ms, output } =
    event.payload;

  const renderData = (data: any) => {
    if (data === null || data === undefined) return <span className="text-white/30">None</span>;
    if (typeof data === 'string') return data;
    try {
      return JSON.stringify(data, null, 2);
    } catch {
      return String(data);
    }
  };

  const getStatusBadge = () => {
    switch (status.toLowerCase()) {
      case 'completed':
      case 'success':
        return (
          <span className="flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-[10px] font-bold uppercase tracking-wider">
            <CheckCircle2 className="w-3 h-3" /> SUCCESS ({execution_latency_ms}ms)
          </span>
        );
      case 'failed':
      case 'failure':
        return (
          <span className="flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/30 text-[10px] font-bold uppercase tracking-wider">
            <AlertCircle className="w-3 h-3" /> FAILED ({execution_latency_ms}ms)
          </span>
        );
      case 'running':
      case 'active':
        return (
          <span className="flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/30 text-[10px] font-bold uppercase tracking-wider animate-pulse">
            <PlayCircle className="w-3 h-3 animate-spin" /> EXECUTING...
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/30 text-[10px] font-bold uppercase tracking-wider">
            <Clock className="w-3 h-3" /> {status.toUpperCase()} ({execution_latency_ms}ms)
          </span>
        );
    }
  };

  return (
    <div className="w-full bg-black/70 border border-cyan-500/30 rounded-xl p-5 font-mono text-xs shadow-[0_0_30px_rgba(6,182,212,0.08)] backdrop-blur-md transition-all duration-300">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-3 mb-4">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
            <Wrench className="w-4 h-4" />
          </div>
          <div>
            <span className="font-bold text-cyan-300 text-xs block uppercase tracking-wider">
              TOOL EXECUTION: {tool_name}
            </span>
            <span className="text-[10px] text-white/40 font-mono">Source: {tool_source}</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-2 py-0.5 rounded bg-white/5 text-white/50 text-[10px] border border-white/10">
            Iter #{event.iteration}
          </span>
          {getStatusBadge()}
        </div>
      </div>

      {/* Input Parameters & Output */}
      <div className="space-y-3">
        <div>
          <span className="text-[10px] text-cyan-400/80 uppercase tracking-widest font-bold block mb-1">
            Input Parameters
          </span>
          <pre className="bg-black/90 border border-white/10 rounded-lg p-3 text-[11px] text-cyan-200/90 overflow-x-auto shadow-inner">
            <code>{renderData(input_parameters)}</code>
          </pre>
        </div>

        <div>
          <span className="text-[10px] text-white/40 uppercase tracking-widest font-bold block mb-1">
            Output Payload
          </span>
          <pre className="bg-black/90 border border-white/10 rounded-lg p-3 text-[11px] text-emerald-300/90 overflow-x-auto max-h-48 shadow-inner">
            <code>{renderData(output)}</code>
          </pre>
        </div>
      </div>
    </div>
  );
};
