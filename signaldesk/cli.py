import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path

from .analysis import analyze
from .evaluation import evaluate_all
from .llm import Enrichment, LLMConfig, OpenAICompatibleClient
from .models import Candidate
from .render import render_memo, slugify
from .sources.yc import collect_snapshot


DEFAULT_LLM_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
DEFAULT_LLM_MODEL = "gemini-3.6-flash"


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    if args.command == "source-yc":
        snapshots = collect_snapshot(args.seed, args.output)
        print(f"Wrote {len(snapshots)} YC page snapshots to {args.output}")
        return
    candidates, snapshot_date = _load_candidates(args.input)

    if args.dry_run:
        _print_preflight(candidates, args)
        return

    args.output.mkdir(parents=True, exist_ok=True)
    client = _build_llm_client(args)
    enrichments = _enrich_all(candidates, client, args.output, args.llm_workers) if client else {}
    analyses = [analyze(candidate, enrichments.get(candidate.source_url)) for candidate in candidates]
    analyses.sort(key=lambda item: item.total, reverse=True)

    _write_outputs(analyses, args.output, snapshot_date)
    print(f"Wrote {len(analyses)} memos to {args.output}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate evidence-first investment memos."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run", help="Generate investment memos from a research snapshot.")
    run.add_argument("--input", required=True, type=Path)
    run.add_argument("--output", required=True, type=Path)
    source = subparsers.add_parser("source-yc", help="Fetch a dated snapshot of allow-listed YC company pages.")
    source.add_argument("--seed", required=True, type=Path)
    source.add_argument("--output", required=True, type=Path)
    _add_llm_arguments(run)
    return parser


def _add_llm_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Run evidence-grounded LLM synthesis; requires an API key environment variable.",
    )
    parser.add_argument(
        "--llm-endpoint",
        default=os.getenv("SIGNALDESK_LLM_ENDPOINT", DEFAULT_LLM_ENDPOINT),
        help="Chat-completions-compatible endpoint.",
    )
    parser.add_argument(
        "--llm-model",
        default=os.getenv("SIGNALDESK_LLM_MODEL", DEFAULT_LLM_MODEL),
        help="Model name sent to the configured endpoint.",
    )
    parser.add_argument(
        "--llm-api-key-env",
        default="SIGNALDESK_LLM_API_KEY",
        help="Environment variable holding the API key.",
    )
    parser.add_argument(
        "--llm-workers",
        type=int,
        default=1,
        help="Number of concurrent LLM requests; use 1 for conservative rate limiting.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs and print the safe execution plan without calling an LLM or writing outputs.",
    )
    return parser


def _load_candidates(input_path: Path) -> tuple[list[Candidate], str]:
    raw = json.loads(input_path.read_text())
    candidates = [Candidate.from_dict(item) for item in raw["candidates"]]
    if not 10 <= len(candidates) <= 20:
        raise ValueError("Sourcing stage requires 10-20 candidates")
    return candidates, raw["snapshot_date"]


def _build_llm_client(args: argparse.Namespace) -> OpenAICompatibleClient | None:
    if not args.llm:
        return None
    config = LLMConfig(
        endpoint=args.llm_endpoint,
        model=args.llm_model,
        api_key_env=args.llm_api_key_env,
    )
    return OpenAICompatibleClient(config)


def _enrich_all(
    candidates: list[Candidate], client: OpenAICompatibleClient, output_path: Path, workers: int
) -> dict[str, Enrichment]:
    """Resume LLM synthesis from a local checkpoint after an interrupted batch."""
    checkpoint_path = output_path / "llm-checkpoint.json"
    cached = _load_checkpoint(checkpoint_path, candidates, client.config)
    if workers < 1:
        raise ValueError("--llm-workers must be at least 1")
    pending = [candidate for candidate in candidates if candidate.source_url not in cached]
    errors = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(client.enrich, candidate): candidate for candidate in pending}
        for future in as_completed(futures):
            candidate = futures[future]
            try:
                cached[candidate.source_url] = future.result()
            except Exception as error:
                errors.append((candidate.name, error))
                continue
            _write_checkpoint(checkpoint_path, candidates, cached)
            print(f"Synthesized {candidate.name} ({len(cached)}/{len(candidates)}).")
    if errors:
        names = ", ".join(name for name, _ in errors)
        raise RuntimeError(f"LLM synthesis failed for {names}; rerun to resume from the checkpoint.") from errors[0][1]
    checkpoint_path.unlink(missing_ok=True)
    return cached


def _load_checkpoint(
    checkpoint_path: Path, candidates: list[Candidate], config: LLMConfig
) -> dict[str, Enrichment]:
    if not checkpoint_path.exists():
        return {}
    raw = json.loads(checkpoint_path.read_text())
    if raw.get("endpoint") != config.endpoint or raw.get("model") != config.model:
        return {}
    by_url = {candidate.source_url: candidate for candidate in candidates}
    cached = {}
    for item in raw.get("entries", []):
        candidate = by_url.get(item.get("source_url"))
        if candidate:
            cached[candidate.source_url] = Enrichment.from_response(
                item["enrichment"], candidate, config.endpoint, config.model
            )
    return cached


def _write_checkpoint(
    checkpoint_path: Path, candidates: list[Candidate], cached: dict[str, Enrichment]
) -> None:
    entries = [
        {"company": candidate.name, "source_url": candidate.source_url, "enrichment": cached[candidate.source_url].as_dict()}
        for candidate in candidates
        if candidate.source_url in cached
    ]
    first = next(iter(cached.values()))
    checkpoint_path.write_text(
        json.dumps({"endpoint": first.provider, "model": first.model, "entries": entries}, indent=2) + "\n"
    )


def _print_preflight(candidates: list[Candidate], args: argparse.Namespace) -> None:
    print(f"Validated {len(candidates)} candidates.")
    if args.llm:
        print("LLM calls: enabled.")
        print(f"Endpoint: {args.llm_endpoint}")
        print(f"Model: {args.llm_model}")
        print(f"API key environment variable: {args.llm_api_key_env}")
        print("No API key value, evidence, or output files were read or transmitted.")
    else:
        print("LLM calls: disabled. Run with --llm to enable synthesis.")


def _write_outputs(analyses: list, output_path: Path, snapshot_date: str) -> None:
    index = [
        "# SignalDesk research output",
        "",
        f"Source snapshot: {snapshot_date}",
        "",
        "| Company | Score | Call |",
        "| --- | ---: | --- |",
    ]
    provenance = []
    for item in analyses:
        filename = f"{slugify(item.candidate.name)}.md"
        (output_path / filename).write_text(render_memo(item))
        index.append(
            f"| [{item.candidate.name}]({filename}) | {item.total}/100 | {item.recommendation} |"
        )
        if item.enrichment:
            provenance.append(
                {
                    "company": item.candidate.name,
                    "source_url": item.candidate.source_url,
                    "llm": item.enrichment.as_dict(),
                }
            )
    (output_path / "index.md").write_text("\n".join(index) + "\n")
    evaluations = evaluate_all(analyses)
    (output_path / "evaluation.json").write_text(
        json.dumps(evaluations, indent=2) + "\n"
    )
    if any(not result["passed"] for result in evaluations):
        raise ValueError("Memo evaluation failed; inspect evaluation.json for details.")
    if provenance:
        (output_path / "llm-provenance.json").write_text(
            json.dumps(provenance, indent=2) + "\n"
        )
