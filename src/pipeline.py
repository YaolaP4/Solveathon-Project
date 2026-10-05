"""Run the whole pipeline end to end.

    python src/pipeline.py          # real run; model calls come from data/cache/ when cached
    python src/pipeline.py --mock   # dry run with fake model answers (data/results/mock/)

Order: Layer 0 clean -> Layer 1 features -> keyword baseline -> Layer 2 Jev triage
-> Layer 3 deep analysis -> Layer 4 scoring -> top-results report -> historical-award
check (USAspending) -> validation report (if labels exist).

With every model response committed under data/cache/, a real run makes no API
calls and needs no key: the same raw data + config + prompts + cache always give
the same ranking.
"""

import argparse
import sys

import award_history
import clean_data
import config
import deep_analysis
import deterministic
import keyword_baseline
import report
import scoring
import semantic_triage
import validation


def main(mock: bool) -> None:
    print("=== Layer 0: clean ===")
    clean_data.main()
    print("\n=== Layer 1: deterministic features ===")
    deterministic.main()
    print("\n=== Layer 5 baseline: keyword TF-IDF ===")
    keyword_baseline.run()

    if not mock and not config.api_key():
        print("\nNote: no AI_GATEWAY_API_KEY - Layers 2-3 will use cached answers only; "
              "any grant not in data/cache/ will fail and be reported.")
    print("\n=== Layer 2: Jev triage ===")
    l2 = semantic_triage.run(mock=mock)
    if l2.empty:
        sys.exit("Layer 2 produced no results (no API key and no cache?). Add the key to .env or use --mock.")
    print("\n=== Layer 3: deep analysis ===")
    deep_analysis.run(mock=mock)
    print("\n=== Layer 4: scoring ===")
    scoring.run(mock=mock)
    print("\n=== Report ===")
    report.run(mock=mock)

    if not mock:
        print("\n=== Layer 5: historical-award check (USAspending.gov, cached) ===")
        award_history.run()

    if not mock and validation.LABELS.exists():
        print("\n=== Layer 5: validation ===")
        try:
            validation.cmd_evaluate()
        except SystemExit as e:  # no labels filled in yet
            print(e)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mock", action="store_true", help="fake model answers; no API key needed")
    main(ap.parse_args().mock)
