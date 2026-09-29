export type EventType =
  | 'agent_thought'
  | 'tool_execution'
  | 'guardrail_intervention'
  | 'resolution';

export interface BaseEvent<T extends EventType, P> {
  event_id: string;
  incident_id: string;
  timestamp: string;
  event_type: T;
  iteration: number;
  payload: P;
}

export interface AgentThoughtPayload {
  phase: string;
  thought_content: string;
  model: string;
  sliding_window_turns: number;
}

export interface ToolExecutionPayload {
  tool_name: string;
  tool_source: string;
  input_parameters: Record<string, any>;
  status: 'running' | 'completed' | 'failed' | string;
  execution_latency_ms: number;
  output: Record<string, any> | string;
}

export interface GuardrailInterventionPayload {
  guardrail_type: string;
  policy_rule: string;
  attempted_action: string;
  intervention_action: 'BLOCKED' | 'MUTATED' | 'HALTED' | string;
  corrective_guidance: string;
}

export interface TracedRootCause {
  node_id: string;
  criticality_pagerank_score: number;
  path_from_trigger: string[];
}

export interface ResolutionPayload {
  status: string;
  triggering_service: string;
  traced_root_cause: TracedRootCause;
  matched_runbook: string;
  action_taken: string;
  summary: string;
  provenance_confidence?: number;
  prior_success_count?: number;
}

export type AgentThoughtEvent = BaseEvent<'agent_thought', AgentThoughtPayload>;
export type ToolExecutionEvent = BaseEvent<'tool_execution', ToolExecutionPayload>;
export type GuardrailInterventionEvent = BaseEvent<'guardrail_intervention', GuardrailInterventionPayload>;
export type ResolutionEvent = BaseEvent<'resolution', ResolutionPayload>;

export type IncidentEvent =
  | AgentThoughtEvent
  | ToolExecutionEvent
  | GuardrailInterventionEvent
  | ResolutionEvent;
