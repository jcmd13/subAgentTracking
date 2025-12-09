# Provider Adapters (Phase 3)

Current status: stub adapters implemented for Claude, Ollama, and Gemini with a simple fallback manager and config-driven provider selection. Real API integration is pending.

## Interfaces

- `BaseProvider`: abstract class with `generate(prompt: str) -> str`.
- `ClaudeProvider`: stubbed; returns `[claude:<model>] <prompt>`.
- `OllamaProvider`: stubbed; returns `[ollama:<model>] <prompt>`.
- `GeminiProvider`: stubbed; returns `[gemini:<model>] <prompt>`.
- `FallbackManager`: tries providers in order until one succeeds.

## Usage (stubbed)

```python
from src.core.providers import load_provider_config, build_providers, FallbackManager

cfg = load_provider_config()  # reads .subagent/config/providers.yaml if present
providers = build_providers(cfg)
mux = FallbackManager(providers)
print(mux.generate("hello"))
```

## Next steps

- Wire real API clients (Anthropic, Ollama HTTP/local, Google Gemini).
- Add config-driven provider selection and keys.
- Add retry/backoff and structured errors.
- Integration tests hitting mocked APIs.
