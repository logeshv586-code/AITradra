# AXIOM V4 Nightly Self-Improvement Goal

## Objective
Improve the MythicOrchestrator prediction signal accuracy and consensus confidence scores using only local, open-source models and data.

## Metric Evaluation
```bash
python scripts/eval_predictions.py
# Must output: METRIC accuracy=0.XX
```

## Success Direction
Higher is better (Accuracy Target: >= 0.75)

## Target Files (Modifiable by AI)
- `agents/specialist_agents.py`
- `gateway/llm_prompts.py`
- `agents/orchestrator.py`

## Constraints
- **Zero Paid APIs**: All research and analysis must use local GGUF or self-hosted SearXNG/OpenBB.
- **Fixed Schemas**: Do NOT modify API endpoint signatures or request/response models.
- **Model Stability**: Primary model is `NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf`.
- **Latency**: Each iteration must complete in < 5 minutes on standard hardware.

## Verification
```bash
python test_endpoints.py && python scripts/eval_predictions.py
```

## Stop Condition
- Accuracy reaches >= 0.75
- 20 iterations reached without improvement
- System stability issues detected
