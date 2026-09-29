# SovereignOps - Infrastructure Graph Module (Sub-Team 2)

## Module Scope
The `infrastructure_graph` module models simulated IT infrastructure dependency topologies and provides algorithms for graph traversal, fault localization, and node criticality analysis.

## IT Infrastructure Topology Description
The topology models an 8-node enterprise microservice architecture as a **Directed Dependency Graph (DiGraph)**:

### Nodes (Services & Components)
1. `api-gateway-01` (`gateway`): Ingress gateway routing client traffic.
2. `auth-service` (`microservice`): Identity access and token authentication service.
3. `user-service` (`microservice`): User profile and authorization service.
4. `payment-service` (`microservice`): Payment processing service.
5. `order-service` (`microservice`): Order lifecycle management service.
6. `db-auth-cluster` (`database`): Database cluster for credentials and auth data.
7. `db-orders-cluster` (`database`): Database cluster for orders and payment state.
8. `external-payment-api` (`external_api`): External third-party payment gateway integration.

## How to Load & Analyze Topology

```python
from graph.topology import load_topology
from graph.fault_localization import localize_fault

# Load graph from data/topology.json
graph = load_topology()

# Process incident alert payload
alert = {
    "alert_id": "INC-8891",
    "timestamp": "2026-09-23T19:30:00Z",
    "triggering_service": "api-gateway-01",
    "error_signature": "HTTP 503 Service Unavailable",
    "severity": "CRITICAL"
}

result = localize_fault(graph, alert)
print(result)
```

## Data Contracts & Schemas
Pydantic data schemas are defined in [`contracts/schemas.py`](contracts/schemas.py):
- `AlertSchema`: Validates Team 2 Contract A alert payloads.
- `TracedRootCauseSchema`: Structure for root-cause candidate diagnosis.
- `FaultLocalizationOutputSchema`: Validates end-to-end fault localization output payload.

## Running Tests
```bash
pytest tests/
```

## Running Demo
```bash
python demo.py
```
