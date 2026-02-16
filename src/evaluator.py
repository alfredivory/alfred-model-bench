"""Scoring engine: automated checks + LLM-as-judge."""

import json
import re
from typing import Any

from .providers.openrouter import OpenRouterProvider


def _extract_json(text: str) -> Any:
    """Try to extract JSON from text, handling markdown code blocks."""
    text = text.strip()
    # Try code block extraction
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if m:
        text = m.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


class Evaluator:
    def __init__(self, evaluator_model: str, api_key_file: str):
        self.model = evaluator_model
        self.provider = OpenRouterProvider(api_key_file)

    def llm_judge(self, prompt: str, response: str, rubric: str) -> int:
        """Use LLM-as-judge to score a response 0-100."""
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert evaluator. Score the AI response against the rubric. "
                    "Return ONLY a JSON object: {\"score\": <0-100>, \"reasoning\": \"<brief>\"}"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"## Original Prompt\n{prompt}\n\n"
                    f"## AI Response\n{response}\n\n"
                    f"## Scoring Rubric\n{rubric}\n\n"
                    "Score this response 0-100."
                ),
            },
        ]
        raw = self.provider.complete(self.model, messages, temperature=0.0)
        text = self.provider.get_text(raw)
        parsed = _extract_json(text)
        if parsed and isinstance(parsed, dict) and "score" in parsed:
            return max(0, min(100, int(parsed["score"])))
        # Fallback: find a number
        nums = re.findall(r"\b(\d{1,3})\b", text)
        for n in nums:
            v = int(n)
            if 0 <= v <= 100:
                return v
        return 50  # default

    def evaluate_scenario(self, scenario: dict, model_response: str) -> dict:
        """Evaluate a model response for a scenario. Returns {score, details}."""
        eval_type = scenario.get("evaluation", {}).get("type", "llm_judge")
        checks = scenario.get("evaluation", {}).get("checks", [])
        rubric = scenario.get("evaluation", {}).get("rubric", "")
        ground_truth = scenario.get("evaluation", {}).get("ground_truth")
        prompt_text = scenario.get("prompt", "")

        details = {}
        auto_scores = []

        # Automated checks
        for check in checks:
            ctype = check.get("type")
            if ctype == "json_valid":
                parsed = _extract_json(model_response)
                passed = parsed is not None
                auto_scores.append(100 if passed else 0)
                details["json_valid"] = passed
            elif ctype == "contains_all":
                keywords = check.get("keywords", [])
                found = sum(1 for kw in keywords if kw.lower() in model_response.lower())
                score = int(found / max(len(keywords), 1) * 100)
                auto_scores.append(score)
                details["contains_all"] = {"found": found, "total": len(keywords)}
            elif ctype == "classification_accuracy":
                if ground_truth:
                    correct = 0
                    total = len(ground_truth)
                    for item_id, expected_label in ground_truth.items():
                        if expected_label.lower() in model_response.lower():
                            correct += 1
                    score = int(correct / max(total, 1) * 100)
                    auto_scores.append(score)
                    details["classification"] = {"correct": correct, "total": total}
            elif ctype == "exact_match":
                if ground_truth:
                    matches = 0
                    total = len(ground_truth) if isinstance(ground_truth, dict) else 1
                    if isinstance(ground_truth, dict):
                        for key, val in ground_truth.items():
                            if str(val).lower() in model_response.lower():
                                matches += 1
                    score = int(matches / max(total, 1) * 100)
                    auto_scores.append(score)
                    details["exact_match"] = {"matches": matches, "total": total}
            elif ctype == "binary_decision":
                if ground_truth and isinstance(ground_truth, dict):
                    correct = 0
                    total = len(ground_truth)
                    for item_id, expected in ground_truth.items():
                        expected_lower = expected.lower()
                        # Check if the response contains the expected decision near the item reference
                        if expected_lower in model_response.lower():
                            correct += 1
                    score = int(correct / max(total, 1) * 100)
                    auto_scores.append(score)
                    details["binary_decision"] = {"correct": correct, "total": total}

        # LLM-as-judge component
        llm_score = None
        if eval_type in ("llm_judge", "hybrid") or rubric:
            llm_score = self.llm_judge(prompt_text, model_response, rubric)
            details["llm_judge_score"] = llm_score

        # Combine scores
        if auto_scores and llm_score is not None:
            auto_avg = sum(auto_scores) / len(auto_scores)
            final = int(auto_avg * 0.5 + llm_score * 0.5)
        elif auto_scores:
            final = int(sum(auto_scores) / len(auto_scores))
        elif llm_score is not None:
            final = llm_score
        else:
            final = 50

        return {"score": final, "details": details}

    def close(self):
        self.provider.close()
