# Labelling PR task types for the pre-ChatGPT group

How to label the 477 pre-ChatGPT PRs so the labels match the methodology of
*The Rise of AI Teammates in Software Engineering (SE) 3.0* (Li et al., arXiv:2507.15003v1 —
the AIDev dataset paper).

## What the paper actually specifies

The whole methodology is one paragraph — Section 4.1, p. 8:

> "Each PR (title and body) is automatically classified into one of 11 task categories
> defined by Conventional Commits Specification (e.g., `feat`, `fix`, `docs`) using
> *GPT-4.1-mini*."

That is all. Everything else has to be reconstructed from Table 4 (p. 9), whose columns give
the 11 categories. There is no published prompt — the
[SAILResearch/AI_Teammates_in_SE3](https://github.com/SAILResearch/AI_Teammates_in_SE3) repo
and the HuggingFace dataset ship the labels, not the classification code. So "exactly
following the paper" reduces to matching four things: **model**, **input fields**,
**label set**, and **one label per PR**.

## Files

| File | Role |
|---|---|
| `rq3_pre_chatgpt_prs_titles.csv` | Input: 477 PRs with `pr_id, repo, html_url, title, body` + blank `type`/`confidence`/`reason` |
| `label_pre_chatgpt_prs.py` | Labeller — GPT-4.1-mini via OpenRouter, one call per PR, resumable |
| `rq3_pre_chatgpt_labels.jsonl` | Raw model output cache (resume state) |
| `rq3_pre_chatgpt_prs_with_task_type.csv` | Output: input + filled labels, same layout as the agent/human files |
| `rq3_labelling_prompt.md` | The prompt and label-set rationale |
| `make_labelling_batches.py` | Manual fallback: paste-ready chat batches |

## Steps

### 1. Input fields — done

The paper classifies on **title *and* body**. `rq3_pre_chatgpt_prs_titles.csv` now carries
both for all 477 PRs (378 have a non-empty body; the other 99 genuinely have none on GitHub,
so they are judged on title alone — the prompt says so explicitly).

This mattered: the other two RQ3 groups inherited AIDev's labels, which were produced with
bodies. Labelling this group on titles alone would have made it methodologically unequal to
the two groups it is compared against.

### 2. Use the paper's 11 categories

Lowercase, exactly these, no others:

    build, chore, ci, docs, feat, fix, other, perf, refactor, style, test

This is Table 4's column set, and the same list hardcoded as `FLOW_ORDER` in the authors' own
`scripts/productivity.py` on HuggingFace.

AIDev's shipped `pr_task_type.parquet` (retrievable at tag `v3` — it was removed from `main`
when v4/AIDev-2.7M was promoted) does contain a 12th value, `revert`, but only on 16 of 33,596
rows (0.05%), and neither the paper nor the authors' script uses it. Excluding it keeps the
three RQ3 groups on an identical vocabulary. Label a reverting PR as `other`.

`other` is the fallback; never invent a label.

### 3. Model: GPT-4.1-mini via OpenRouter

    export OPENROUTER_API_KEY=sk-or-...
    python label_pre_chatgpt_prs.py --limit 10   # smoke test
    python label_pre_chatgpt_prs.py              # full run

The script pins `openai/gpt-4.1-mini`, `temperature=0`, `seed=42`. This is what makes the
"GPT-4.1-mini, as in the paper" claim literally true — the ChatGPT web UI cannot be pinned to
that model, so the manual fallback would silently label with a different one.

### 4. Prompt

Lives in the script as `SYSTEM_PROMPT` and is reproduced in `rq3_labelling_prompt.md`. It
states the 11-value vocabulary, the title+body input, the empty-body case, the 3–10 confidence
scale, and one-label-per-PR.

### 5. One request per PR, resumable

Not batched. One PR per call means the `pr_id` is never sent to the model and so cannot be
rounded or reformatted — the failure mode that silently corrupts a join. A JSON-schema
`response_format` pins `type` to the 11-value enum, so an invented label cannot come back
either.

Every result is appended to `rq3_pre_chatgpt_labels.jsonl`. Re-running labels only what is
still missing, so a partial or rate-limited run is resumed, not restarted. `--merge-only`
rebuilds the output CSV from the cache without touching the API.

### 6. Validation

The script checks, and reports, on every run:

- every row carries a label (477/477);
- no duplicate `pr_id`;
- every `type` is in the 11-value vocabulary;
- the resulting distribution, as percentages.

Still worth doing by hand: manually label a random ~50 PRs and report agreement (Cohen's
kappa) against the model. The paper does not do this, but reviewers will ask, and it costs
about an hour.

### 7. Sanity-check the distribution

Compare the pre-ChatGPT `%feat`/`%fix` split against Table 4's human row (29.4 / 26.9), and
against your own agent and human groups. A wildly different shape usually means a prompt
problem, not a real finding.

## Notes on `confidence`

The agent group has it (integers 3–10); the human group does not — AIDev left it NULL for all
6,618 human rows. So `confidence` cannot be used as a filter across all three groups. Collect
it for completeness, but plot on `type` alone.
