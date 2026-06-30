"""NeuralPal：类脑四层记忆 + 英国绅士特助人设的个人 AGI 骨架包。"""

from neuralpal.core_rules import (
    RuleValidationResult,
    get_system_prompt,
    get_system_prompt_fingerprint_sha256,
    validate_before_generation,
    validate_system_prompt_text,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "get_system_prompt",
    "get_system_prompt_fingerprint_sha256",
    "validate_before_generation",
    "validate_system_prompt_text",
    "RuleValidationResult",
]
