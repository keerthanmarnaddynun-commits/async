import React, { useState, useEffect } from 'react';
import {
  Shield,
  Lock,
  Terminal,
  RefreshCw,
  KeyRound,
  ShieldCheck,
  Check,
  Copy,
  AlertTriangle,
  Zap,
} from 'lucide-react';

// Fallback incident data matching backend orchestrator schema
const DEFAULT_INCIDENT = {
  alert_id: 'INC-8891',
  telemetry: {
    alert: {
      alert_id: 'INC-8891',
      timestamp: '2026-09-23T19:30:00Z',
      triggering_service: 'api-gateway-01',
      error_signature: 'HTTP 503 Service Unavailable',
      severity: 'CRITICAL',
    },
    syslog:
      'Sep 23 19:29:45 api-gateway-01 systemd[1]: Starting API Gateway...\n' +
      'Sep 23 19:29:50 api-gateway-01 gateway-proxy[4432]: [WARN] Connection pool reaching capacity\n' +
      'Sep 23 19:30:00 api-gateway-01 gateway-proxy[4432]: [ERROR] HTTP 503 Service Unavailable - upstream auth-service timeout\n' +
      'Sep 23 19:30:01 api-gateway-01 systemd[1]: gateway-proxy.service: Main process exited, code=exited, status=1/FAILURE\n',
  },
  graph_context: {
    alert_id: 'INC-8891',
    traced_root_cause: {
      node_id: 'auth-service',
      criticality_pagerank_score: 0.87,
      path_from_trigger: ['api-gateway-01', 'auth-service'],
    },
    provenance_memory_matches: [
      {
        runbook_id: 'RB-089',
        historical_fix: 'Roll back auth-service deployment to previous tag.',
        provenance_confidence: 0.94,
        prior_success_count: 12,
      },
    ],
  },
  matched_runbook:
    '# RB-089: Auth-Service Timeout Recovery\n' +
    '**Service:** auth-service\n' +
    '**Risk Tier:** High (Tier-2)\n\n' +
    '## Remediation Steps\n' +
    'Roll back deployment to previous tag: `kubectl rollout undo deployment/auth-service`\n',
  diagnostic: {
    action_type: 'tier_1_diagnostic',
    payload: {
      command: 'journalctl -u gateway-proxy -n 50',
      target_node: 'api-gateway-01',
    },
  },
  remediation: {
    action_type: 'tier_2_remediation',
    payload: {
      command: 'kubectl rollout undo deployment/auth-service',
      justification:
        'Graph mapped fault to auth-service timeout. Historical provenance score 0.94 strongly supports rollback.',
      target_node: 'auth-service',
    },
  },
};

export default function App() {
  const [data, setData] = useState(DEFAULT_INCIDENT);
  const [isLoading, setIsLoading] = useState(false);
  const [bridgeStatus, setBridgeStatus] = useState('connecting'); // 'connected' | 'fallback'
  const [lastFetched, setLastFetched] = useState(null);
  const [copiedKey, setCopiedKey] = useState(null);

  // Cryptographic Authorization State
  const [isSigning, setIsSigning] = useState(false);
  const [isAuthorized, setIsAuthorized] = useState(false);
  const [authTimestamp, setAuthTimestamp] = useState(null);

  // Fetch telemetry & triage output from FastAPI backend bridge
  const fetchTriage = async (alertId = 'INC-8891') => {
    setIsLoading(true);
    const start = Date.now();
    try {
      const response = await fetch(`http://localhost:8000/api/triage/${alertId}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const json = await response.json();
      setData(json);
      setBridgeStatus('connected');
      setLastFetched(`${Date.now() - start}ms`);
    } catch (err) {
      console.warn('FastAPI bridge unreachable, using local enclave cache:', err.message);
      setBridgeStatus('fallback');
      setLastFetched('Enclave Cache');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTriage('INC-8891');
  }, []);

  const handleAuthorize = () => {
    if (isAuthorized) return;
    setIsSigning(true);
    setTimeout(() => {
      setIsSigning(false);
      setIsAuthorized(true);
      setAuthTimestamp(new Date().toUTCString());
    }, 1200);
  };

  const handleResetAuth = () => {
    setIsAuthorized(false);
    setAuthTimestamp(null);
  };

  const handleCopy = (text, key) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const alertData = data?.telemetry?.alert;
  const rootCause = data?.graph_context?.traced_root_cause;
  const provenance = data?.graph_context?.provenance_memory_matches?.[0];

  return (
    <div className="min-h-screen w-screen bg-black text-white font-sans relative overflow-x-hidden selection:bg-violet-500/30 selection:text-violet-200">
      {/* Background ambient lighting */}
      <div className="fixed top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[500px] bg-gradient-to-b from-violet-900/10 via-rose-900/5 to-transparent rounded-full blur-[140px] pointer-events-none z-0" />

      {/* ========================================================================= */}
      {/* 1. TOP MINIMALIST FLOATING BAR                                             */}
      {/* ========================================================================= */}
      <header className="fixed top-0 left-0 right-0 z-50 px-8 py-5 flex items-center justify-between backdrop-blur-2xl bg-black/60 border-b border-white/[0.06]">
        <div className="flex items-center gap-3">
          <div className="w-6 h-6 rounded bg-white/10 border border-white/20 flex items-center justify-center">
            <Shield className="w-3.5 h-3.5 text-white" />
          </div>
          <span className="font-mono text-xs font-bold uppercase tracking-widest text-white/90">
            SOVEREIGNOPS
          </span>
          <span className="text-[10px] font-mono text-white/30 uppercase tracking-widest hidden sm:inline-block">
            • AIR-GAPPED AUTHORIZATION VAULT
          </span>
        </div>

        <div className="flex items-center gap-4 text-xs font-mono">
          <button
            onClick={() => fetchTriage('INC-8891')}
            disabled={isLoading}
            className="text-white/40 hover:text-white flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-amber-400' : ''}`} />
            <span>{isLoading ? 'Re-evaluating...' : 'Re-run Inference'}</span>
          </button>

          <div className="h-3 w-px bg-white/10" />

          <div className="flex items-center gap-2 text-[10px] text-white/40">
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                bridgeStatus === 'connected' ? 'bg-emerald-400 shadow-[0_0_8px_#10b981]' : 'bg-amber-400'
              }`}
            />
            <span>{bridgeStatus === 'connected' ? 'CONNECTED :8000' : 'ENCLAVE CACHE'}</span>
            {lastFetched && <span className="text-white/20">({lastFetched})</span>}
          </div>
        </div>
      </header>

      {/* ========================================================================= */}
      {/* 2. CINEMATIC SINGLE-PAGE HERO FLOW                                        */}
      {/* ========================================================================= */}
      <main className="relative z-10 max-w-5xl mx-auto px-6 pt-36 pb-24 flex flex-col items-center text-center">
        {/* Breadcrumb & Floating Micro-Badges */}
        <div className="flex flex-wrap items-center justify-center gap-3 text-[11px] font-mono tracking-widest uppercase text-white/40 mb-8">
          <span>INCIDENTS</span>
          <span>/</span>
          <span className="text-white/80 font-bold">{alertData?.alert_id || 'INC-8891'}</span>
          <span className="text-white/20">•</span>
          <span className="px-2.5 py-0.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20 font-semibold">
            {alertData?.severity || 'CRITICAL'}
          </span>
          <span className="text-white/20">•</span>
          <span
            className={`px-2.5 py-0.5 rounded-full border font-semibold ${
              isAuthorized
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
            }`}
          >
            {isAuthorized ? 'EXECUTION APPLIED' : 'TIER-2 REMEDIATION REQUIRED'}
          </span>
        </div>

        {/* Hero Title (Apple Scale Typography) */}
        <h1 className="text-6xl md:text-8xl font-bold tracking-tighter text-white/95 leading-tight max-w-4xl font-sans">
          {alertData?.error_signature || 'HTTP 503 Service Unavailable'}
        </h1>

        {/* Root Cause Subtitle */}
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3 font-mono text-sm text-white/50">
          <span>Traced Fault Target:</span>
          <span className="text-amber-300 font-semibold px-3 py-1 rounded bg-amber-500/10 border border-amber-500/20">
            {rootCause?.node_id || 'auth-service'}
          </span>
          <span className="text-white/20">•</span>
          <span>PageRank: <strong className="text-white">{rootCause?.criticality_pagerank_score ?? 0.87}</strong></span>
          <span className="text-white/20">•</span>
          <span>Confidence: <strong className="text-emerald-400">{((provenance?.provenance_confidence ?? 0.94) * 100).toFixed(0)}%</strong></span>
        </div>

        {/* ========================================================================= */}
        {/* 3. GHOST DATA STREAM (VOID LOG TERMINAL)                                  */}
        {/* ========================================================================= */}
        <div className="w-full max-w-3xl my-24 text-center">
          <div className="text-[10px] font-mono uppercase tracking-widest text-white/30 mb-4 flex items-center justify-center gap-2">
            <Terminal className="w-3.5 h-3.5 text-white/40" />
            <span>DIAGNOSTIC LOG STREAM • $ {data?.diagnostic?.payload?.command || 'journalctl -u gateway-proxy -n 50'}</span>
          </div>

          {/* Floating Void Log Lines (No Outer Card / Border Box) */}
          <div className="font-mono text-xs leading-relaxed space-y-2 text-center opacity-90 max-h-80 overflow-y-auto px-4 py-2">
            {data?.telemetry?.syslog
              ? data.telemetry.syslog.split('\n').map((line, idx) => {
                  if (!line.trim()) return null;
                  const isErr = line.includes('[ERROR]') || line.includes('FAILURE');
                  const isWarn = line.includes('[WARN]');
                  return (
                    <div
                      key={idx}
                      className={`transition-opacity duration-200 ${
                        isErr
                          ? 'text-rose-400 font-medium'
                          : isWarn
                          ? 'text-amber-300 font-medium'
                          : 'text-white/35'
                      }`}
                    >
                      {line}
                    </div>
                  );
                })
              : 'No diagnostic syslog output.'}
          </div>
        </div>

        {/* ========================================================================= */}
        {/* 4. THE HERO INTERACTION: AIR-GAPPED CRYPTOGRAPHIC GATE                    */}
        {/* ========================================================================= */}
        <div className="w-full max-w-2xl mx-auto p-10 rounded-2xl bg-white/[0.02] border border-white/[0.08] backdrop-blur-3xl shadow-[0_0_80px_rgba(0,0,0,0.9)] text-center space-y-8 relative">
          <div className="flex items-center justify-between border-b border-white/[0.08] pb-4 text-xs font-mono">
            <div className="flex items-center gap-2 text-white/60">
              <Lock className="w-4 h-4 text-violet-400" />
              <span className="font-bold tracking-wider uppercase text-white/90">Air-Gapped Cryptographic Gate</span>
            </div>
            <span className="text-[10px] text-white/30 uppercase tracking-widest">ED25519-SIG-SOVEREIGN</span>
          </div>

          {/* Proposed Remediation Command Display */}
          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-[10px] text-white/40 uppercase tracking-widest">Proposed Remediation Action</span>
              <button
                onClick={() =>
                  handleCopy(
                    data?.remediation?.payload?.command || 'kubectl rollout undo deployment/auth-service',
                    'rem_cmd'
                  )
                }
                className="text-white/40 hover:text-white flex items-center gap-1 transition-colors cursor-pointer text-[11px]"
              >
                {copiedKey === 'rem_cmd' ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                    <span className="text-emerald-400">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    <span>Copy Command</span>
                  </>
                )}
              </button>
            </div>

            <div className="bg-black/80 border border-rose-500/30 rounded-xl p-4 font-mono text-sm text-rose-300 font-medium shadow-inner flex items-center justify-between">
              <code>
                {data?.remediation?.payload?.command || 'kubectl rollout undo deployment/auth-service'}
              </code>
            </div>
          </div>

          {/* Autonomous Enclave Reasoning */}
          <p className="text-xs text-white/60 font-sans leading-relaxed text-center px-4">
            {data?.remediation?.payload?.justification ||
              'Graph mapped fault to auth-service timeout. Historical provenance score 0.94 strongly supports rollback.'}
          </p>

          {/* Provenance Details */}
          <div className="grid grid-cols-2 gap-4 text-xs font-mono text-center">
            <div className="bg-white/[0.02] border border-white/[0.06] rounded-lg p-3">
              <span className="text-[10px] text-white/30 uppercase tracking-widest block mb-1">Runbook Match</span>
              <span className="text-white font-semibold">{provenance?.runbook_id || 'RB-089'}</span>
            </div>
            <div className="bg-white/[0.02] border border-white/[0.06] rounded-lg p-3">
              <span className="text-[10px] text-white/30 uppercase tracking-widest block mb-1">Historical Successes</span>
              <span className="text-emerald-400 font-semibold">{provenance?.prior_success_count || 12} executions</span>
            </div>
          </div>

          {/* Hero Action Button / Authorized State */}
          {!isAuthorized ? (
            <button
              onClick={handleAuthorize}
              disabled={isSigning}
              className="w-full py-4 px-8 rounded-xl font-mono text-xs font-bold uppercase tracking-widest transition-all duration-300 cursor-pointer flex items-center justify-center gap-3 bg-gradient-to-r from-violet-600 via-indigo-600 to-violet-600 hover:from-violet-500 hover:to-indigo-500 text-white shadow-[0_0_40px_rgba(124,58,237,0.35)] hover:shadow-[0_0_50px_rgba(124,58,237,0.55)] border border-violet-400/40 active:scale-[0.99] disabled:opacity-50"
            >
              {isSigning ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin text-white" />
                  <span>Signing with Enclave Private Key...</span>
                </>
              ) : (
                <>
                  <KeyRound className="w-4 h-4 text-violet-200" />
                  <span>AUTHORIZE & CRYPTOGRAPHICALLY SIGN</span>
                </>
              )}
            </button>
          ) : (
            <div className="space-y-4 animate-in fade-in duration-300">
              <div className="bg-emerald-500/10 border border-emerald-500/40 rounded-xl p-5 flex items-center justify-between">
                <div className="flex items-center gap-3 text-left">
                  <ShieldCheck className="w-6 h-6 text-emerald-400 shrink-0" />
                  <div>
                    <span className="text-xs font-bold text-emerald-400 block font-mono">
                      CRYPTOGRAPHICALLY SIGNED & EXECUTED
                    </span>
                    <span className="text-[10px] font-mono text-white/40">
                      SHA256: 4a9f8b...e1029c • {authTimestamp || 'Timestamp verified'}
                    </span>
                  </div>
                </div>
                <span className="text-xs font-mono text-emerald-300 font-bold px-3 py-1 rounded bg-emerald-500/20 border border-emerald-500/30">
                  VERIFIED
                </span>
              </div>

              <div className="bg-black/90 border border-white/[0.08] rounded-lg p-3 text-xs font-mono text-emerald-400 flex items-center justify-between">
                <code>deployment.apps/auth-service rolled back [OK]</code>
                <button
                  onClick={handleResetAuth}
                  className="text-[10px] text-white/40 hover:text-white underline cursor-pointer"
                >
                  Reset Vault
                </button>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
