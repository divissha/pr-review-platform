"""
Week 2: score the eligible PRs with the LLM.

Run from the backend/ folder:
    python -m scoring.run_llm --dry-run            # no API call, no key needed
    python -m scoring.run_llm --limit 10           # tiny test run (format check)
    python -m scoring.run_llm                      # the full run

Safe to interrupt and re-run: finished PRs are cached on disk.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from scoring.features import (DATA_DIR, eligible_mask, iter_raw_records,
                              load_labeled_dataset)
from scoring.llm_based import (DEFAULT_MODEL, SYSTEM_PROMPT, build_user_prompt,
                               load_cached, make_client, save_cached,
                               score_with_llm)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--limit", type=int, default=None,
                    help="score only a random sample of this many PRs")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--dry-run", action="store_true",
                    help="build prompts and estimate tokens, no API calls")
    ap.add_argument("--price-in", type=float, default=0.10,
                    help="USD per million input tokens (CHECK the pricing page)")
    ap.add_argument("--price-out", type=float, default=0.50,
                    help="USD per million output tokens (CHECK the pricing page)")
    args = ap.parse_args()

    df = load_labeled_dataset()
    elig = df[eligible_mask(df)].reset_index(drop=True)
    print(f"Usable PRs: {len(df)} | eligible (change source code, not "
          f"docs/CI/typing): {len(elig)} | risky among eligible: {elig['risky'].sum()}")
    if args.limit:
        elig = elig.sample(min(args.limit, len(elig)), random_state=0)
        print(f"Using a random sample of {len(elig)} PRs (--limit)")

    keys = {(r, int(n)) for r, n in zip(elig["repo"], elig["number"])}
    records = list(iter_raw_records(keys))

    if args.dry_run:
        prompts = [build_user_prompt(r) for r in records]
        est = sum(len(p) + len(SYSTEM_PROMPT) for p in prompts) / 4
        print(f"\nEstimated input: ~{est:,.0f} tokens total, "
              f"~{est / len(prompts):,.0f} per PR (rough chars/4 rule)")
        print("\n===== SYSTEM PROMPT =====\n" + SYSTEM_PROMPT)
        print("\n===== EXAMPLE USER PROMPT =====\n" + prompts[0][:3500])
        return

    client = make_client()
    todo = [r for r in records if load_cached(args.model, r) is None]
    print(f"{len(records) - len(todo)} already cached, {len(todo)} to score "
          f"with {args.model}")

    def work(rec):
        try:
            res = score_with_llm(client, args.model, rec)
            save_cached(args.model, rec, res)
            return rec, None
        except Exception as e:  # keep going; failed PRs are retried next run
            return rec, e

    failed = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for i, (rec, err) in enumerate(pool.map(work, todo), 1):
            if err is not None:
                failed += 1
                print(f"  FAILED {rec['repo']}#{rec['number']}: {err}")
            if i % 25 == 0 or i == len(todo):
                print(f"  {i}/{len(todo)} done")

    # ---- collect everything from the cache and save ----
    rows, tin, tout = [], 0, 0
    risky = dict(zip(zip(elig["repo"], elig["number"]), elig["risky"]))
    for rec in records:
        res = load_cached(args.model, rec)
        if res is None:
            continue
        tin += res["input_tokens"]
        tout += res["output_tokens"]
        rows.append({
            "repo": rec["repo"], "number": int(rec["number"]),
            "risky": int(risky[(rec["repo"], int(rec["number"]))]),
            "llm_score": res["score"], "llm_label": res["label"],
            "llm_summary": res["summary"],
            "llm_factors": "; ".join(res["reasons"]),
        })
    out = DATA_DIR / ("scores_llm_sample.csv" if args.limit else "scores_llm.csv")
    pd.DataFrame(rows).to_csv(out, index=False)

    cost = tin / 1e6 * args.price_in + tout / 1e6 * args.price_out
    print(f"\nScored {len(rows)}/{len(records)} PRs ({failed} failed this run) -> {out}")
    print(f"Tokens: {tin:,} in, {tout:,} out | est. cost ${cost:.2f} "
          f"at ${args.price_in}/${args.price_out} per million (verify prices)")
    if failed:
        print("Re-run the same command to retry the failed PRs.")


if __name__ == "__main__":
    main()