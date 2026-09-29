import { IncidentEvent } from '../types/events';

export const MOCK_EVENTS: IncidentEvent[] = [
  {
    event_id: 'evt_001',
    incident_id: 'INC-8891',
    timestamp: '2026-09-29T17:00:00Z',
    event_type: 'agent_thought',
    iteration: 1,
    payload: {
      phase: 'initial_assessment',
      thought_content:
        'High-priority alert INC-8891 received from api-gateway-01. Error signature: HTTP 503 Service Unavailable. Initializing multi-step reasoning loop to assess active service inventory and ingest telemetry.',
      model: 'Sovereign-Llama-3.3-70B-Instruct-Q4_K_M',
      sliding_window_turns: 1,
    },
  },
  {
    event_id: 'evt_002',
    incident_id: 'INC-8891',
    timestamp: '2026-09-29T17:00:01.5Z',
    event_type: 'tool_execution',
    iteration: 1,
    payload: {
      tool_name: 'list_services',
      tool_source: 'cluster_service_registry',
      input_parameters: {
        namespace: 'production',
        filter: 'failing',
      },
      status: 'completed',
      execution_latency_ms: 120,
      output: {
        services: ['api-gateway-01', 'auth-service', 'payment-gateway'],
        status_code: 200,
      },
    },
  },
  {
    event_id: 'evt_004',
    incident_id: 'INC-8891',
    timestamp: '2026-09-29T17:00:03.0Z',
    event_type: 'tool_execution',
    iteration: 2,
    payload: {
      tool_name: 'get_diagnostic_logs',
      tool_source: 'systemd_telemetry_provider',
      input_parameters: {
        unit: 'gateway-proxy',
        lines: 50,
        target_node: 'api-gateway-01',
      },
      status: 'completed',
      execution_latency_ms: 185,
      output: {
        log_snippet:
          'gateway-proxy[4432]: [ERROR] HTTP 503 Service Unavailable - upstream auth-service connection timeout',
        exit_code: 0,
      },
    },
  },
  {
    event_id: 'evt_006',
    incident_id: 'INC-8891',
    timestamp: '2026-09-29T17:00:04.5Z',
    event_type: 'tool_execution',
    iteration: 2,
    payload: {
      tool_name: 'query_infrastructure_graph',
      tool_source: 'infrastructure_dependency_graph',
      input_parameters: {
        trigger_node: 'api-gateway-01',
        max_depth: 3,
      },
      status: 'completed',
      execution_latency_ms: 240,
      output: {
        traced_root_cause: {
          node_id: 'auth-service',
          criticality_pagerank_score: 0.87,
          path_from_trigger: ['api-gateway-01', 'auth-service-pod-x9', 'auth-service'],
        },
      },
    },
  },
  {
    event_id: 'evt_007',
    incident_id: 'INC-8891',
    timestamp: '2026-09-29T17:00:06.0Z',
    event_type: 'agent_thought',
    iteration: 3,
    payload: {
      phase: 'remediation_planning',
      thought_content:
        'Graph analysis pinpoints fault to auth-service (PageRank 0.87). Formulating remediation action: attempting direct unverified deployment rollback execute_k8s_rollback without provenance confidence check.',
      model: 'Sovereign-Llama-3.3-70B-Instruct-Q4_K_M',
      sliding_window_turns: 3,
    },
  },
  {
    event_id: 'evt_008',
    incident_id: 'INC-8891',
    timestamp: '2026-09-29T17:00:07.5Z',
    event_type: 'guardrail_intervention',
    iteration: 3,
    payload: {
      guardrail_type: 'State-Machine Safety Gate (Tier-2 Policy Enforcer)',
      policy_rule:
        'CRITICAL SAFETY RULE: Agent must query Provenance Memory to verify historical confidence before executing rollback.',
      attempted_action: 'execute_k8s_rollback',
      intervention_action: 'BLOCKED',
      corrective_guidance:
        'Execution intercepted by Caged ReAct Enforcer. Call search_provenance_memory to verify historical confidence first before executing rollback.',
    },
  },
  {
    event_id: 'evt_010',
    incident_id: 'INC-8891',
    timestamp: '2026-09-29T17:00:09.0Z',
    event_type: 'tool_execution',
    iteration: 4,
    payload: {
      tool_name: 'search_provenance_memory',
      tool_source: 'enclave_vector_memory',
      input_parameters: {
        error_signature: 'auth-service connection timeout',
        target_service: 'auth-service',
      },
      status: 'completed',
      execution_latency_ms: 310,
      output: {
        matched_runbook: {
          runbook_id: 'RB-AUTH-001',
          historical_fix: 'Roll back auth-service deployment to previous tag v2.1.4',
          provenance_confidence: 0.92,
          prior_success_count: 14,
        },
      },
    },
  },
  {
    event_id: 'evt_013',
    incident_id: 'INC-8891',
    timestamp: '2026-09-29T17:00:10.5Z',
    event_type: 'resolution',
    iteration: 5,
    payload: {
      status: 'RESOLVED',
      triggering_service: 'api-gateway-01',
      traced_root_cause: {
        node_id: 'auth-service',
        criticality_pagerank_score: 0.87,
        path_from_trigger: ['api-gateway-01', 'auth-service', 'db-auth-cluster'],
      },
      matched_runbook: 'RB-AUTH-001 (Auth-Service Recovery)',
      action_taken: 'kubectl rollout undo deployment/auth-service',
      summary:
        'Incident INC-8891 successfully remediated. Unverified rollback attempt was intercepted by Caged ReAct Guardrail, prompting mandatory Provenance Memory lookup (92% confidence across 14 prior resolutions). Rollback executed cleanly.',
      provenance_confidence: 0.92,
      prior_success_count: 14,
    },
  },
];

export class MockSSESimulator {
  private timer: ReturnType<typeof setInterval> | null = null;
  private currentIndex = 0;
  private listeners: ((event: IncidentEvent) => void)[] = [];
  private isRunning = false;
  private intervalMs = 1500;

  public subscribe(listener: (event: IncidentEvent) => void): () => void {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== listener);
    };
  }

  public start(): void {
    if (this.isRunning) return;
    this.isRunning = true;
    this.currentIndex = 0;

    this.timer = setInterval(() => {
      if (this.currentIndex < MOCK_EVENTS.length) {
        const event = MOCK_EVENTS[this.currentIndex];
        this.currentIndex++;
        this.notify(event);
      } else {
        this.stop();
      }
    }, this.intervalMs);
  }

  public stop(): void {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
    this.isRunning = false;
  }

  public reset(): void {
    this.stop();
    this.currentIndex = 0;
  }

  public getIsRunning(): boolean {
    return this.isRunning;
  }

  private notify(event: IncidentEvent): void {
    this.listeners.forEach((listener) => listener(event));
  }
}

export const mockSSESimulator = new MockSSESimulator();
