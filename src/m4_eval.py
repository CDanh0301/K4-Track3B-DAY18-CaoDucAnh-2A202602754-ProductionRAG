from __future__ import annotations

"""Module 4: RAGAS Evaluation — 4 metrics + failure analysis."""

import os, sys, json
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TEST_SET_PATH


@dataclass
class EvalResult:
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float


def load_test_set(path: str = TEST_SET_PATH) -> list[dict]:
    """Load test set from JSON. (Đã implement sẵn)"""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def evaluate_ragas(questions: list[str], answers: list[str],
                   contexts: list[list[str]], ground_truths: list[str]) -> dict:
    """Run RAGAS evaluation."""
    try:
        from ragas import evaluate
        from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
        from datasets import Dataset

        dataset = Dataset.from_dict({
            "question": questions,
            "answer": answers,
            "contexts": contexts,
            "ground_truth": ground_truths,
        })
        from ragas.run_config import RunConfig
        from ragas.llms import LangchainLLMWrapper
        from langchain_openai import ChatOpenAI
        from config import OPENAI_API_KEY

        eval_llm = LangchainLLMWrapper(ChatOpenAI(
            model="gpt-4o-mini",
            api_key=OPENAI_API_KEY,
            max_retries=2,
            timeout=30
        ))
        for m in [faithfulness, answer_relevancy, context_precision, context_recall]:
            m.llm = eval_llm

        run_config = RunConfig(max_workers=8, timeout=45, max_retries=2, max_wait=10)

        result = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
            run_config=run_config
        )
        df = result.to_pandas()

        per_question = [
            EvalResult(
                question=str(row["question"]),
                answer=str(row["answer"]),
                contexts=row["contexts"] if isinstance(row["contexts"], list) else [str(row["contexts"])],
                ground_truth=str(row["ground_truth"]),
                faithfulness=float(row.get("faithfulness", 0.0) or 0.0),
                answer_relevancy=float(row.get("answer_relevancy", 0.0) or 0.0),
                context_precision=float(row.get("context_precision", 0.0) or 0.0),
                context_recall=float(row.get("context_recall", 0.0) or 0.0)
            )
            for _, row in df.iterrows()
        ]

        def _safe_mean(col):
            vals = [float(v) for v in df[col].dropna() if v is not None]
            return float(sum(vals) / len(vals)) if vals else 0.0

        return {
            "faithfulness": _safe_mean("faithfulness") if "faithfulness" in df else 0.0,
            "answer_relevancy": _safe_mean("answer_relevancy") if "answer_relevancy" in df else 0.0,
            "context_precision": _safe_mean("context_precision") if "context_precision" in df else 0.0,
            "context_recall": _safe_mean("context_recall") if "context_recall" in df else 0.0,
            "per_question": per_question
        }
    except Exception as e:
        print(f"  ⚠️  RAGAS evaluation failed: {e}")
        return {
            "faithfulness": 0.0,
            "answer_relevancy": 0.0,
            "context_precision": 0.0,
            "context_recall": 0.0,
            "per_question": []
        }


def failure_analysis(eval_results: list[EvalResult], bottom_n: int = 10) -> list[dict]:
    """Analyze bottom-N worst questions using Diagnostic Tree."""
    if not eval_results:
        return []

    diagnostic_tree = {
        "faithfulness": (
            "LLM hallucinating",
            "Tighten prompt, lower temperature, and emphasize strict grounding"
        ),
        "context_recall": (
            "Missing relevant chunks",
            "Improve chunking granularity or boost BM25/Dense fusion parameters"
        ),
        "context_precision": (
            "Too many irrelevant chunks",
            "Add cross-encoder reranking or stricter metadata filtering"
        ),
        "answer_relevancy": (
            "Answer doesn't match question",
            "Improve prompt template or refine question intent parsing"
        ),
    }

    scored_evals = []
    for item in eval_results:
        metrics = {
            "faithfulness": float(item.faithfulness),
            "answer_relevancy": float(item.answer_relevancy),
            "context_precision": float(item.context_precision),
            "context_recall": float(item.context_recall),
        }
        avg_score = sum(metrics.values()) / len(metrics)
        worst_metric = min(metrics, key=metrics.get)
        diagnosis, suggested_fix = diagnostic_tree.get(
            worst_metric,
            ("Unknown retrieval or generation issue", "Investigate end-to-end prompt and retrieval pipeline")
        )
        scored_evals.append({
            "avg_score": avg_score,
            "question": item.question,
            "answer": item.answer,
            "ground_truth": item.ground_truth,
            "worst_metric": worst_metric,
            "score": metrics[worst_metric],
            "diagnosis": diagnosis,
            "suggested_fix": suggested_fix,
        })

    scored_evals.sort(key=lambda x: x["avg_score"])
    bottom_failures = scored_evals[:bottom_n]

    return [
        {
            "question": f["question"],
            "answer": f["answer"],
            "ground_truth": f["ground_truth"],
            "worst_metric": f["worst_metric"],
            "score": f["score"],
            "diagnosis": f["diagnosis"],
            "suggested_fix": f["suggested_fix"],
        }
        for f in bottom_failures
    ]


def save_report(results: dict, failures: list[dict], path: str = "reports/ragas_report.json"):
    """Save evaluation report to JSON. (Đã implement sẵn)"""
    parent_dir = os.path.dirname(path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    report = {
        "aggregate": {k: v for k, v in results.items() if k != "per_question"},
        "num_questions": len(results.get("per_question", [])),
        "failures": failures,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Report saved to {path}")


if __name__ == "__main__":
    test_set = load_test_set()
    print(f"Loaded {len(test_set)} test questions")
    print("Run pipeline.py first to generate answers, then call evaluate_ragas().")
