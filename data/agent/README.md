# Offline agent source pack

`source-pack.json` contains three frozen cards of real papers: S01 Task Shield,
S02 AgentDojo and S03 WASP. The cards were prepared through AI-assisted reading
of the cited PDFs. Each card records reading coverage, bibliographic links,
the PDF hash, evidence locations, a detailed summary and short brief fields.

This pack is prepared for this coursework. It is not a teacher-provided fixture.
The full papers are not fetched by the runner; `read_source` reads these local
cards. Reading events prove which card bytes were used, not human reading of the
entire paper. `source-pack.json` SHA-256:

`8e4f6e4e78f079c323e162902389954c943a14ab685e0ed0914e2020ee32273f`

`task-contract.json` and `tool-schema.json` are fixed across both conditions.
Only the execution budget changes between 3 and 6 attempted tool calls. Search
matches all case-folded query tokens against title and keywords, not a canned
list regardless of the query. `--check` also confirms an unrelated query matches
no sources.

## Re-run from the repository root

Python 3.10 or newer, standard library only; no package installation is required.

```bash
python3 src/offline_agent.py --check
python3 src/offline_agent.py --output-dir results/agent-rerun
python3 src/verify_agent_evidence.py --results-dir results/agent-rerun
```

Choose a fresh output directory so the recorded submission run remains intact.
The verifier can be repeated against the same result directory. The expected
comparison is 3 calls / 2 reads / FAIL versus 5 calls / 3 reads / PASS. The
failure condition deliberately has no final brief.

## Evidence

Each condition keeps task contract, tool schema, full source pack, trajectory,
tool results, evaluation CSV, provenance, error note and independent validation.
The successful condition also keeps `final-brief.md`. `comparison.csv` has only
the two budget conditions. `qa-negative/` contains copies with a tampered brief
or invalid citation to demonstrate that validation rejects them; these are
quality checks, not extra experimental conditions or valid submissions.

The trajectory binds each tool result to a SHA-256 chain and checks successful
read order before writing. The independent verifier imports no runner code; it
reopens the actual files and reconstructs order, checks matching source content,
citation placement and written bytes. Hashes detect inconsistent alterations;
they are not a digital signature or proof against an attacker able to rewrite
the complete evidence package.

No LLM, network request, paid API, GPU or agent framework runs in this fixture.
The source-card summaries and integration paragraph are prewritten inputs and a
fixed template. This experiment does not reproduce the three papers' model
results and does not measure natural-language planning capability.
