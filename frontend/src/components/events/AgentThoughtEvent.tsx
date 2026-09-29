import React, { useState, useEffect } from 'react';
import { Terminal, Cpu, Layers } from 'lucide-react';
import { AgentThoughtEvent } from '../../types/events';

interface Props {
  event: AgentThoughtEvent;
}

export const AgentThoughtEventView: React.FC<Props> = ({ event }) => {
  const { phase, thought_content, model, sliding_window_turns } = event.payload;
  const [displayedText, setDisplayedText] = useState('');

  useEffect(() => {
    let index = 0;
    const interval = setInterval(() => {
      index += 3;
      if (index >= thought_content.length) {
        setDisplayedText(thought_content);
        clearInterval(interval);
      } else {
        setDisplayedText(thought_content.slice(0, index));
      }
    }, 12);

    return () => clearInterval(interval);
  }, [thought_content]);

  return (
    <div className="w-full bg-black/70 border border-violet-500/30 rounded-xl p-5 font-mono text-xs shadow-[0_0_30px_rgba(139,92,246,0.08)] backdrop-blur-md transition-all duration-300">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-3 mb-4">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded bg-violet-500/10 border border-violet-500/30 text-violet-400">
            <Terminal className="w-4 h-4" />
          </div>
          <span className="font-bold text-violet-300 uppercase tracking-wider text-[11px]">
            AGENT THOUGHT STREAM
          </span>
          <span className="px-2 py-0.5 rounded bg-violet-500/20 text-violet-300 text-[10px] font-semibold border border-violet-500/30">
            Iter #{event.iteration}
          </span>
        </div>

        <div className="flex items-center gap-3 text-[10px] text-white/50">
          <div className="flex items-center gap-1">
            <Cpu className="w-3 h-3 text-violet-400" />
            <span>{model}</span>
          </div>
          <span>•</span>
          <div className="flex items-center gap-1">
            <Layers className="w-3 h-3 text-violet-400" />
            <span>Window: {sliding_window_turns} turns</span>
          </div>
        </div>
      </div>

      {/* Phase metadata */}
      <div className="mb-3 text-[11px] font-semibold text-white/80 flex items-center gap-2">
        <span className="text-violet-400">PHASE:</span>
        <span className="px-2.5 py-0.5 rounded bg-white/5 border border-white/10 text-white font-mono uppercase tracking-wide">
          {phase}
        </span>
      </div>

      {/* Content box */}
      <div className="bg-black/90 border border-white/10 rounded-lg p-4 text-white/90 leading-relaxed font-mono whitespace-pre-wrap relative min-h-[60px] shadow-inner">
        <span className="text-violet-400 font-bold mr-2">&gt;</span>
        {displayedText}
        {displayedText.length < thought_content.length && (
          <span className="inline-block w-2 h-4 bg-violet-400 ml-1 animate-pulse align-middle" />
        )}
      </div>
    </div>
  );
};
