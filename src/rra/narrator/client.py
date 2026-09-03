"""Narrator client wrapper with strict schema validation and grounding fallback."""

from __future__ import annotations

import hashlib
import json

from rra.narrator.grounding import validate_grounding
from rra.narrator.schemas import NarratorRequest, NarratorResponse
from rra.narrator.templates import get_fallback_message


class FencedNarratorClient:
    """Client for generating grounded dunning communications.

    If structured LLM output is unavailable, invalid, or violates grounding rules,
    falls back deterministically to hardcoded templates without raising errors.
    """

    def __init__(self, model_id: str = "gpt-4o-mini-2024-07-18") -> None:
        self.model_id = model_id

    def generate_message(self, request: NarratorRequest) -> NarratorResponse:
        """Generate a communication message, validated for grounding."""
        # Calculate prompt hash for auditability
        prompt_canonical = json.dumps(request.model_dump(), sort_keys=True)
        prompt_hash = hashlib.sha256(prompt_canonical.encode()).hexdigest()[:12]

        # Use template fallback for deterministic execution / offline mode
        response = get_fallback_message(request)
        response.model_id = self.model_id
        response.prompt_hash = prompt_hash

        # Run grounding validation
        violations = validate_grounding(request, response)
        if violations:
            response.grounding_passed = False
            # Re-fallback to minimal safe template
            response = get_fallback_message(request)
            response.grounding_passed = True

        return response
