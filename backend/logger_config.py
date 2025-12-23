import json
import os
from typing import Any, Dict, Optional, Tuple

LOG_FILE = "query_logs.json"

# Try to import a BaseCallbackHandler from langchain if available.
# If not available, provide a tiny fallback so inheritance still works.
try:
    from langchain.callbacks.base import BaseCallbackHandler  # type: ignore
except Exception:
    class BaseCallbackHandler:
        """Fallback base class when langchain isn't installed / import path differs."""
        pass


class TokenMetricsCallback(BaseCallbackHandler):
    """
    Token accounting for Gemini / Google models.

    Priority order:
    1. Provider-returned usage metadata (usageMetadata, promptTokenCount, etc.)
    2. Google official tokenizer (vertexai.preview.tokenization)

    NO heuristic fallback.
    """

    # Attributes expected by LangChain's callback manager / inspector.
    ignore_llm: bool = False
    ignore_chain: bool = False
    ignore_agent: bool = False
    raise_error: bool = False
    always_verbose: bool = False

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name
        self.input_tokens = 0
        self.output_tokens = 0
        self._recorded_via_hook = False

    # ---------------- no-op callback methods (prevent AttributeError) ----------------
    # These are simple safe defaults so that various callback managers can call them.

    def on_chain_start(self, *args, **kwargs) -> None:
        return None

    def on_chain_end(self, *args, **kwargs) -> None:
        return None

    def on_llm_start(self, *args, **kwargs) -> None:
        return None

    def on_llm_new_token(self, *args, **kwargs) -> None:
        return None

    def on_tool_end(self, *args, **kwargs) -> None:
        return None

    def on_tool_error(self, *args, **kwargs) -> None:
        return None

    def on_agent_action(self, *args, **kwargs) -> None:
        return None

    def on_text(self, *args, **kwargs) -> None:
        return None

    # ---------------- public helpers ----------------

    def add_usage(self, input_tokens: int, output_tokens: int) -> None:
        self.input_tokens += int(input_tokens)
        self.output_tokens += int(output_tokens)

    def set_usage(self, input_tokens: int, output_tokens: int) -> None:
        self.input_tokens = int(input_tokens)
        self.output_tokens = int(output_tokens)

    # ---------------- langchain hook ----------------

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        in_toks, out_toks = self._parse_token_usage_from_response(response)
        if in_toks is not None or out_toks is not None:
            self.set_usage(in_toks or 0, out_toks or 0)
            self._recorded_via_hook = True

    # ---------------- parsing helpers ----------------

    def _parse_token_usage_from_response(
        self, obj: Any
    ) -> Tuple[Optional[int], Optional[int]]:
        """
        Extract token usage from Gemini / Vertex responses.
        """

        # LangChain LLMResult.llm_output
        llm_output = getattr(obj, "llm_output", None)
        if isinstance(llm_output, dict):
            extracted = self._extract_from_dict(llm_output)
            if extracted:
                return extracted

        # LangChain generations metadata
        gens = getattr(obj, "generations", None)
        if gens:
            for gen_list in gens:
                for gen in gen_list:
                    meta = (
                        getattr(gen, "generation_info", None)
                        or getattr(gen, "metadata", None)
                        or {}
                    )
                    if isinstance(meta, dict):
                        extracted = self._extract_from_dict(meta)
                        if extracted:
                            return extracted

        # Raw dict response
        if isinstance(obj, dict):
            extracted = self._extract_from_dict(obj)
            if extracted:
                return extracted

        return (None, None)

    def _extract_from_dict(self, d: Dict[str, Any]) -> Optional[Tuple[int, int]]:
        """
        DFS search for Gemini / Vertex usage fields.
        """
        stack = [d]

        while stack:
            cur = stack.pop()
            if not isinstance(cur, dict):
                continue

            usage = (
                cur.get("usageMetadata")
                or cur.get("usage")
                or cur.get("usage_metadata")
            )

            if isinstance(usage, dict):
                pt = usage.get("promptTokenCount")
                ct = usage.get("candidatesTokenCount")
                if pt is not None or ct is not None:
                    return (pt or 0, ct or 0)

            pt = cur.get("promptTokenCount") or cur.get("prompt_tokens")
            ct = cur.get("candidatesTokenCount") or cur.get("completion_tokens")

            if pt is not None or ct is not None:
                return (pt or 0, ct or 0)

            for v in cur.values():
                if isinstance(v, dict):
                    stack.append(v)
                elif isinstance(v, list):
                    for item in v:
                        if isinstance(item, dict):
                            stack.append(item)

        return None

    # ---------------- fallback: OFFICIAL tokenizer only ----------------

    def ensure_usage_from_response(
        self, response: Any, inputs: Optional[str] = None
    ) -> None:
        """
        Use Google official tokenizer if provider metadata is missing.
        NO heuristic fallback.
        """
        if self._recorded_via_hook:
            return

        # Try provider metadata again
        in_toks, out_toks = self._parse_token_usage_from_response(response)
        if in_toks is not None or out_toks is not None:
            self.set_usage(in_toks or 0, out_toks or 0)
            return

        # Google official tokenizer (Vertex AI)
        try:
            from vertexai.preview import tokenization
        except Exception:
            # Vertex tokenizer isn't available — nothing to do here.
            return

        tokenizer = tokenization.get_tokenizer_for_model(self.model_name)

        input_count = tokenizer.count_tokens(inputs).total_tokens if inputs else 0

        if hasattr(response, "content"):
            output_text = response.content
        elif hasattr(response, "text"):
            output_text = response.text
        elif isinstance(response, dict):
            output_text = response.get("content", "")
        else:
            output_text = ""

        output_count = (
            tokenizer.count_tokens(output_text).total_tokens
            if output_text
            else 0
        )

        self.set_usage(input_count, output_count)


def save_log_to_file(query_data: Dict):
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f:
            json.dump([], f)

    with open(LOG_FILE, "r+") as f:
        data = json.load(f)
        data.append(query_data)
        f.seek(0)
        json.dump(data, f, indent=4)
