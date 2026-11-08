# CloudSage Copilot LLM Provider Configuration

## 1. Provider Independence & Abstraction

CloudSage Copilot is designed with strict provider independence. The conversational engine does not depend on any proprietary LLM vendor features, function calling formats, or external vector stores.

The provider layer (`backend/app/copilot/llm_provider.py`) defines an abstract contract:
```python
class BaseLLMProvider(ABC):
    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        context: Dict[str, Any],
        intent: CopilotIntent,
        citations: List[EvidenceCitationSchema],
    ) -> Tuple[str, int, int]:
        pass
```

---

## 2. Supported LLM Backends

| Provider Identifier | Target Backend | Use Case |
| :--- | :--- | :--- |
| `auto` (default) | Uses `openai` if `COPILOT_API_KEY` is present, else `fallback` | Production & Local Dev automatic switching |
| `openai` | OpenAI API (`gpt-4o-mini`, `gpt-4o`) | Standard cloud deployments |
| `azure` | Azure OpenAI Services (`gpt-4o`, `gpt-35-turbo`) | Enterprise sovereign cloud deployments |
| `vllm` / `ollama` | Self-hosted OpenAI-compatible inference servers | Air-gapped / Private on-premise environments |
| `fallback` | Deterministic Fallback Synthesizer | Offline testing, air-gapped CI/CD, sandboxes |

---

## 3. The Grounded Deterministic Fallback Provider

When running in environments without outbound internet access, without API keys, or during automated CI testing, the **Deterministic Fallback Provider** (`DeterministicFallbackProvider`) takes over seamlessly.

### Characteristics:
1. **Zero External Network Dependencies**: Operates entirely in-process using pure Python and SQLAlchemy.
2. **Strict Zero Float Rule**: Retains full 4-decimal fixed-point precision (`Decimal("0.0000")`) across all totals and breakdowns.
3. **Structured FinOps Template Synthesis**: Assembles answers using domain-specific FinOps templates for all 15 canonical intents.
4. **Verifiable Auditability**: Cites the exact database rows retrieved by the Query Planner.
5. **Zero Hallucination Risk**: Impossible to fabricate figures because numbers are bound directly from SQL aggregate results.

---

## 4. Configuration Environment Variables

Configure Copilot behavior in your `.env` file or container environment:

```bash
# Enable or disable AI Copilot subsystem
COPILOT_ENABLED=true

# Provider mode: auto, openai, fallback
COPILOT_PROVIDER=auto

# Active model identifier
COPILOT_MODEL_NAME=gpt-4o-mini

# External LLM API Key (leave empty to engage deterministic fallback)
COPILOT_API_KEY=

# Custom endpoint (for Azure OpenAI, vLLM, or Ollama)
# e.g., http://localhost:8000/v1/chat/completions
COPILOT_API_ENDPOINT=

# Request timeout in seconds
COPILOT_REQUEST_TIMEOUT_SECONDS=30

# Maximum token allocation for completion
COPILOT_MAX_TOKENS=1500

# Sampling temperature (0.0 for maximum determinism)
COPILOT_TEMPERATURE=0.0

# Rate limit (queries per minute per user)
COPILOT_RATE_LIMIT_PER_MINUTE=60
```

---

## 5. Connecting Self-Hosted vLLM / Ollama

To connect a private, air-gapped model (e.g. `Llama-3-70B-Instruct` or `Mistral-Large` hosted on vLLM):

```bash
COPILOT_PROVIDER=openai
COPILOT_MODEL_NAME=meta-llama/Meta-Llama-3-70B-Instruct
COPILOT_API_KEY=dummy-token-for-local-vllm
COPILOT_API_ENDPOINT=http://vllm-service.internal.net:8000/v1/chat/completions
```

