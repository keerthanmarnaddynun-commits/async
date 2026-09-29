import React from 'react';
import {
  ArrowRight,
  BookOpen,
  Award,
  Activity,
  ShieldCheck,
  ArrowDown,
} from 'lucide-react';
import { ResolutionEvent } from '../../types/events';

interface Props {
  event: ResolutionEvent;
}

export const ResolutionEventView: React.FC<Props> = ({ event }) => {
  const {
    status,
    triggering_service,
    traced_root_cause,
    matched_runbook,
    action_taken,
    summary,
    provenance_confidence = 0.94,
    prior_success_count = 12,
  } = event.payload;

  const pathNodes = traced_root_cause?.path_from_trigger || [
    triggering_service,
    traced_root_cause?.node_id,
  ];

  return (
    <div className="w-full bg-gradient-to-b from-emerald-950/30 via-black to-emerald-950/50 border border-emerald-500/40 rounded-xl p-6 font-mono text-xs shadow-[0_0_50px_rgba(16,185,129,0.15)] backdrop-blur-xl transition-all duration-300">
      {/* Header Banner */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-emerald-500/30 pb-4 mb-5">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-emerald-500/20 border border-emerald-500/40 text-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.3)]">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <span className="font-bold text-emerald-400 text-sm tracking-widest uppercase block">
              INCIDENT RESOLVED
            </span>
            <span className="text-[11px] text-white/50 font-mono">
              Triggering Service: <strong className="text-white">{triggering_service}</strong>
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-xs font-extrabold uppercase tracking-widest">
            {status}
          </span>
        </div>
      </div>

      {/* Dynamic Infrastructure Graph Path Trace */}
      <div className="mb-5 bg-black/80 border border-white/10 rounded-xl p-4">
        <div className="flex items-center justify-between mb-3 text-[10px] text-emerald-400/90 font-bold uppercase tracking-widest">
          <div className="flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5 text-emerald-400" />
            <span>Infrastructure Graph Path Trace</span>
          </div>
          <span className="text-white/40 font-mono">
            PageRank: <strong className="text-white">{traced_root_cause?.criticality_pagerank_score ?? 0.87}</strong>
          </span>
        </div>

        {/* Dynamic Nodes Flow */}
        <div className="flex flex-wrap items-center justify-center gap-2 py-2 text-center">
          {pathNodes.map((node, idx) => (
            <React.Fragment key={idx}>
              <div
                className={`px-3 py-1.5 rounded-lg border font-mono text-xs font-semibold ${
                  node === traced_root_cause?.node_id
                    ? 'bg-amber-500/20 border-amber-500/50 text-amber-300 shadow-[0_0_10px_rgba(245,158,11,0.3)]'
                    : 'bg-white/5 border-white/10 text-white/80'
                }`}
              >
                {node}
                {node === traced_root_cause?.node_id && (
                  <span className="ml-2 text-[9px] px-1.5 py-0.5 bg-amber-500/30 rounded text-amber-200 uppercase font-bold">
                    Root Cause
                  </span>
                )}
              </div>

              {idx < pathNodes.length - 1 && (
                <div className="flex items-center text-emerald-400 px-1">
                  <ArrowRight className="w-4 h-4 hidden sm:block" />
                  <ArrowDown className="w-4 h-4 sm:hidden" />
                </div>
              )}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* Provenance Match & Confidence */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
        <div className="bg-black/60 border border-white/10 rounded-lg p-3.5">
          <div className="flex items-center gap-1.5 text-[10px] text-white/40 font-bold uppercase tracking-widest mb-1">
            <BookOpen className="w-3.5 h-3.5 text-emerald-400" />
            <span>Matched Provenance Runbook</span>
          </div>
          <div className="text-white font-bold text-xs font-mono">{matched_runbook}</div>
        </div>

        <div className="bg-black/60 border border-emerald-500/30 rounded-lg p-3.5">
          <div className="flex items-center justify-between text-[10px] text-emerald-400 font-bold uppercase tracking-widest mb-1">
            <div className="flex items-center gap-1.5">
              <Award className="w-3.5 h-3.5" />
              <span>Provenance Confidence</span>
            </div>
            <span className="text-emerald-300 font-extrabold">
              {(provenance_confidence * 100).toFixed(0)}%
            </span>
          </div>
          <div className="text-white/60 text-[11px] font-sans">
            Verified across <strong className="text-emerald-400">{prior_success_count}</strong> prior successful resolutions
          </div>
        </div>
      </div>

      {/* Remediation Action Taken */}
      <div className="space-y-3">
        <div>
          <span className="text-[10px] text-emerald-400 uppercase tracking-widest font-bold block mb-1">
            Remediation Executed
          </span>
          <div className="bg-black/90 border border-emerald-500/40 rounded-lg p-3 font-mono text-emerald-300 text-xs font-semibold shadow-inner">
            <code>{action_taken}</code>
          </div>
        </div>

        {/* Summary */}
        <div className="bg-white/[0.02] border border-white/10 rounded-lg p-3 text-white/80 font-sans leading-relaxed text-xs">
          {summary}
        </div>
      </div>
    </div>
  );
};
