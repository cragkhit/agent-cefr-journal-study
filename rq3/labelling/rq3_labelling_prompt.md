# PR task-type labelling prompt (RQ3, pre-ChatGPT group only)

AIDev ships task-type labels for both of the other groups — `pr_task_type.parquet` for
agent PRs and `human_pr_task_type.parquet` for human PRs — so neither needs labelling.

The **pre-ChatGPT** group is the exception: those 477 PRs predate the AIDev sample and
appear in neither table, so they have to be labelled separately. For RQ3 to stay a
like-for-like comparison, the labels must use **exactly** AIDev's schema — otherwise the
three groups are not comparable.

## Label set (exactly these 11, lowercase, no others)

`build`, `chore`, `ci`, `docs`, `feat`, `fix`, `other`, `perf`, `refactor`,
`style`, `test`

These are the 11 categories the AIDev paper reports (Li et al., Section 4.1 and
Table 4), and the same 11 hardcoded in the authors' own analysis script
(`scripts/productivity.py` on HuggingFace, `FLOW_ORDER`).

Note: AIDev's shipped `pr_task_type.parquet` (available at tag `v3`; dropped from
`main` when v4 was promoted) does carry a 12th value, `revert`, on 16 of its 33,596
rows (0.05%). Both the paper and the authors' script exclude it, so we exclude it
too — label a reverting PR as `other`.

`other` is the fallback — use it rather than inventing a new label.

## Confidence

Integer **3–10** (the range AIDev's own labels span). 10 = the PR states its task
type unambiguously; 3 = it is too vague to be sure.

## How the labelling is run

The prompt below lives in `label_pre_chatgpt_prs.py` as `SYSTEM_PROMPT`; that script is
the canonical path. It calls **GPT-4.1-mini through OpenRouter**
(`openai/gpt-4.1-mini`, `temperature=0`, `seed=42`), one request per PR, and caches
results to `rq3_pre_chatgpt_labels.jsonl` so the run is resumable.

    export OPENROUTER_API_KEY=sk-or-...
    python label_pre_chatgpt_prs.py --limit 10   # smoke test first
    python label_pre_chatgpt_prs.py              # full run
    python label_pre_chatgpt_prs.py --merge-only # rebuild the CSV from the cache

One call per PR means the `pr_id` never round-trips through the model, so it cannot be
rounded or reformatted. A JSON-schema `response_format` pins `type` to the 11-value enum,
so an out-of-vocabulary label cannot come back either.

The prompt, in full:

> You are labelling GitHub pull requests by task type, following the Conventional Commits
> specification.
>
> Assign exactly one label to the pull request. `type` must be exactly one of: build,
> chore, ci, docs, feat, fix, other, perf, refactor, style, test.
>
> Judge from the PR title and body together. Some PRs have an empty body — judge from the
> title alone in that case. If the PR is ambiguous, pick the most likely label and lower
> the confidence rather than falling back to `other`. Reserve `other` for PRs that
> genuinely fit no category; label a revert as `other`.
>
> `confidence` is an integer from 3 to 10: 10 means the PR states its task type
> unambiguously, 3 means it is too vague to be sure.
>
> `reason` is one sentence explaining the choice.

The user message carries the PR's `title` and `body` verbatim (`(empty)` where a PR has no
body — 99 of the 477 do not).

### Manual fallback

`make_labelling_batches.py` writes the same PRs into `labelling_batches/batch_NN.txt`,
25 PRs per file, each file a self-contained message to paste into a chat UI. Use this only
if the API route is unavailable — note that a chat UI cannot be pinned to GPT-4.1-mini, so
the model would no longer match the paper's.

## Feeding the results back

Labels join onto `rq3_pre_chatgpt_prs_titles.csv` on `pr_id`, filling its blank `type` /
`confidence` / `reason` columns; the script does this and writes
`rq3_pre_chatgpt_prs_with_task_type.csv`. That file already shares the agent and
human files' column layout, so all three concatenate directly for plotting.

Note on `confidence`: the agent group has it (integers 3–10), the human group does not
(AIDev left it NULL for all 6,618 human rows). So `confidence` cannot be used as a filter
across all three groups — collect it for completeness, but plot on `type` alone.

**Watch the `pr_id`s** — they are 10-digit integers and chat models sometimes round or
reformat them. The script sidesteps this by never sending the id to the model; if you use
the manual fallback instead, check that every returned `pr_id` matches an input `pr_id`
exactly before joining.
