import React from 'react';
import { ShieldAlert, ShieldX, FileText, Compass, AlertOctagon } from 'lucide-react';
import { GuardrailInterventionEvent } from '../../types/events';

interface Props {
  event: GuardrailInterventionEvent;
}

export const GuardrailInterventionEventView: React.FC<Props> = ({ event }) => {
  const {
    guardrail_type,
    policy_rule,
    attempted_action,
    intervention_action,
    corrective_guidance,
  } = event.payload;

  return (
    <div className="w-full bg-gradient-to-b from-amber-950/40 via-black to-rose-950/30 border-2 border-amber-500/60 rounded-xl p-6 font-mono text-xs shadow-[0_0_50px_rgba(245,158,11,0.25)] relative overflow-hidden backdrop-blur-xl transition-all duration-300">
      {/* Animated warning beam stripe */}
      <div className="absolute top-0 right-0 left-0 h-1 bg-gradient-to-r from-amber-500 via-rose-500 to-amber-500 animate-pulse" />

      {/* Header Banner */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-amber-500/30 pb-4 mb-5">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-amber-500/20 border border-amber-500/50 text-amber-400 shadow-[0_0_15px_rgba(245,158,11,0.4)]">
            <ShieldAlert className="w-6 h-6 animate-bounce" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-amber-400 text-sm tracking-widest uppercase">
                SAFETY INTERVENTION • CAGED REACT GATE
              </span>
            </div>
            <span className="text-[11px] text-amber-200/70 font-sans block mt-0.5">
              {guardrail_type}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-3 py-1 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/50 text-xs font-extrabold uppercase tracking-widest shadow-[0_0_15px_rgba(244,63,94,0.3)] flex items-center gap-1.5">
            <AlertOctagon className="w-3.5 h-3.5" />
            {intervention_action}
          </span>
        </div>
      </div>

      {/* Grid Content */}
      <div className="space-y-4">
        {/* Attempted Action (Blocked) */}
        <div>
          <div className="flex items-center gap-1.5 text-[10px] text-rose-400 font-bold uppercase tracking-widest mb-1.5">
            <ShieldX className="w-3.5 h-3.5" />
            <span>Attempted Dangerous / Unverified Action</span>
          </div>
          <div className="bg-black/90 border border-rose-500/40 rounded-lg p-3 text-rose-300 text-xs font-mono line-through decoration-rose-500/70 bg-rose-950/20 shadow-inner">
            <code>{attempted_action}</code>
          </div>
        </div>

        {/* Policy Rule Enforced */}
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3.5 space-y-1">
          <div className="flex items-center gap-1.5 text-[10px] text-amber-400 font-bold uppercase tracking-widest">
            <FileText className="w-3.5 h-3.5" />
            <span>Policy Rule Enforced</span>
          </div>
          <p className="text-amber-100/90 text-xs leading-relaxed font-sans">
            {policy_rule}
          </p>
        </div>

        {/* Corrective Guidance */}
        <div className="bg-emerald-950/30 border border-emerald-500/40 rounded-lg p-3.5 space-y-1">
          <div className="flex items-center gap-1.5 text-[10px] text-emerald-400 font-bold uppercase tracking-widest">
            <Compass className="w-3.5 h-3.5" />
            <span>Corrective Guidance</span>
          </div>
          <p className="text-emerald-200/90 text-xs leading-relaxed font-sans">
            {corrective_guidance}
          </p>
        </div>
      </div>
    </div>
  );
};
