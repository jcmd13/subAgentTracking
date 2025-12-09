# Provider Adapters (Phase 3)

Current status: stub adapters implemented for Claude, Ollama, and Gemini with a simple fallback manager. Real API integration is pending.

## Interfaces

- `BaseProvider`: abstract class with `generate(prompt: str) -> str`.
- `ClaudeProvider`: stubbed; returns `[claude:<model>] <prompt>`.
- `OllamaProvider`: stubbed; returns `[ollama:<model>] <prompt>`.
- `GeminiProvider`: stubbed; returns `[gemini:<model>] <prompt>`.
- `FallbackManager`: tries providers in order until one succeeds.

## Usage (stubbed)

```python
from src.core.providers import ClaudeProvider, OllamaProvider, GeminiProvider, FallbackManager

providers = [ClaudeProvider(), OllamaProvider(model="llama3"), GeminiProvider()]
mux = FallbackManager(providers)
print(mux.generate("hello"))
```

## Next steps

- Wire real API clients (Anthropic, Ollama HTTP/local, Google Gemini).
- Add config-driven provider selection and keys.
- Add retry/backoff and structured errors.
- Integration tests hitting mocked APIs.
