# Evidence Desk — a local LLM evidence lab

A working retrieval-augmented generation (RAG) project that answers document questions using **source quotations selected by a real local language model**. It combines BM25 retrieval, schema-constrained generation, strict citation checks, a live question interface, and an auditable evaluation report.

The central finding is deliberately visible: **source-checked does not mean correct**. Qwen3-0.6B passed 17 of 20 task checks, but returned irrelevant quotations for three questions with missing information. No result has been replaced with a canned answer or hidden to improve the headline score.

## Open the finished result

Download and extract this repository, then open [`reports/evaluation/report.html`](reports/evaluation/report.html) in a browser. It is a standalone interactive replay with every question, retrieved passage, model output, expected fact, and check result. It works without a running model. GitHub displays HTML source; download it to use the interactive report.

The **live app** adds a question form that calls the local model. There are no API keys, hosted inference calls, or paid services. The bundled NorthstarOps handbook is original fictional material, not a real company's policy or professional advice.

## Published run

| Measurement | Observed result |
| --- | ---: |
| Task checks passed | 17 / 20 (85.0%) |
| Required evidence retrieved | 16 / 16 answerable questions |
| Answerable task checks passed | 16 / 16, including two adversarial questions |
| Missing-information abstentions | 1 / 4 |
| Accepted answers meeting the task check | 16 / 19 (84.2%) |
| Actual LLM calls | 19 |
| Median observed model request latency | 2.25 seconds |
| Source-validation failures in this run | 0 |
| Deterministic automated tests | 33 passed locally |

The single successful missing-information abstention occurred **before generation**, because retrieval found no matching passage. For all three unknown questions with a retrieval hit, the model supplied source-valid but irrelevant evidence. These failures are available under **Failed task checks** in the report. Passing all citation checks does not rescue those answers.

The model was **Qwen3-0.6B-GGUF, Q8_0**, served by **llama.cpp b11617** on a Windows laptop CPU (four inference threads). The published run uses 5,481 prompt tokens and 1,081 output tokens. Runtime and model checksums are in [`runtime-reference.json`](runtime-reference.json); exact outputs and hashes are in [`evaluation.json`](reports/evaluation/evaluation.json).

## Quick start — Windows

Python 3.11 or newer is required. The application itself has **no third-party Python runtime dependencies**. The model download is approximately 639 MB, plus a 20 MB Windows CPU runtime archive. They stay in an ignored local folder and are not uploaded with this project.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m unittest discover -s tests -v
python scripts/setup_windows_model.py
```

The setup helper downloads pinned official release files and verifies their SHA-256 checksums before extraction. It does not change system PATH or install a service.

Start the model in one terminal:

```powershell
.\scripts\start_model.ps1
```

Start the app in a second terminal, from this project folder with its environment activated:

```powershell
evidence-desk serve
```

Open **http://127.0.0.1:8774/report.html**. Closing either terminal stops its process. The model listens only on `127.0.0.1:8094`; the app listens only on `127.0.0.1:8774`.

For macOS/Linux, install [llama.cpp from its official repository](https://github.com/ggml-org/llama.cpp), download the [pinned Qwen GGUF file](https://huggingface.co/Qwen/Qwen3-0.6B-GGUF/resolve/23749fefcc72300e3a2ad315e1317431b06b590a/Qwen3-0.6B-Q8_0.gguf), and start an equivalent local server:

```bash
llama-server -m /path/to/Qwen3-0.6B-Q8_0.gguf --host 127.0.0.1 --port 8094 -c 4096 -t 4 --parallel 1 --jinja --alias qwen3-0.6b-local --no-webui
```

Then install this package and run `evidence-desk serve`. Platform/build differences may change generations and latency; only the stated Windows runtime was used for the published model run.

## Commands

```bash
# Ask a new question, returning source evidence and diagnostics as JSON:
evidence-desk ask "How quickly must a SEV-1 page be acknowledged?"

# Reproduce the evaluation using the pinned runtime above:
evidence-desk evaluate --provenance runtime-reference.json

# Rebuild the HTML report from saved results, without a model:
evidence-desk render

# A different local server/model (do not reuse the reference provenance file):
evidence-desk --endpoint http://127.0.0.1:8095 --model my-local-model ask "What is the backup retention?"

# Use your own local JSON corpus:
evidence-desk --corpus private-inputs/handbook.json serve
```

Global options precede the command. `ask --k` supports retrieval depths from 1 to 5; the published configuration and live app use 1. `evaluate` always uses the bundled corpus and labels. Runtime provenance is operator-supplied, not inferred from a model alias. If omitted, reruns record it as unknown. The live interface labels its active model/corpus separately from the saved evaluation.

The CLI returns 0 for a completed answer or abstention, 2 when `ask` rejects model output, and 1 for an input/backend error. Evaluation exits 1 for backend errors; imperfect answer quality is reported in its metrics, not hidden as an execution failure.

## Pipeline

1. **Curate:** accept only documents with `approved: true` and `current: true`. Exclude an archived procedure and an unreviewed malicious note in the sample corpus.
2. **Chunk:** split paragraphs into stable `document-id:paragraph-number` passages. Require paragraphs of at most 1,200 characters instead of silently truncating them.
3. **Retrieve:** BM25 over lowercase alphanumeric tokens with a small stopword list; deterministic sorting; no vector database or embedding model.
4. **Generate:** the local LLM selects exact quotations in schema-constrained JSON with `decision` and `evidence`. Temperature 0, seed 41, 384 output tokens, thinking disabled.
5. **Check:** reject unknown sources, extra fields, malformed/duplicate-key JSON, duplicate entries, modified or empty quotations, and generation that did not finish normally. Whitespace is normalized for quote matching.
6. **Present:** render only checked quotations with source IDs. Keep the unvalidated model draft in a diagnostic disclosure. A quotation can pass provenance checks while failing the question's task check.

The assistant performs evidence selection rather than free-form answer synthesis. It cannot execute tools or document instructions, browse the web, or access files beyond the corpus explicitly loaded by the application.

## Data and evaluation design

The original fictional corpus contains eight approved current documents, split into 16 passages, plus one superseded document and one unapproved injection fixture. The document inclusion flags are human assertions; the app does not determine their trustworthiness.

Six development questions select the smallest retrieval depth maximizing complete-source recall from `k = 1, 3, 5`. All achieved full recall on those six questions, so `k = 1` was selected. The separate 20-question evaluation contains 14 ordinary answerable questions, four unknown questions, and two adversarial-but-answerable questions. The same handbook is available throughout; this is not an unseen-document benchmark and no model is trained or fine-tuned.

An answerable task passes when every expected fact string appears in checked evidence under its expected source ID, and no unexpected source is included. An unknown question passes only on `ABSTAIN`. These are deterministic, human-authored fixture checks—not semantic entailment judgments, human grading, or an external LLM judge. Partial answers, wrong sources, and failures remain visible in the results. All model calls and raw outputs are saved; no retry or best-of-many selection is performed.

## Limitations and next experiments

- The small local model fails to abstain on plausible but unanswered questions. Source checks detect fabricated quotations, not relevance, completeness, or truth.
- Top-one lexical retrieval is economical on this tiny corpus, but can miss paraphrases or evidence spread across documents. No multi-document questions are in the published evaluation.
- The 20 examples and two adversarial prompts are too few to establish general reliability or resistance to prompt injection. Filtering an explicitly unapproved fixture is not automatic attack detection.
- Trust flags and document currency require manual curation. An attacker-controlled document wrongly marked approved/current can still influence the answer.
- No PDF/OCR ingestion, multilingual evaluation, conversational memory, authentication, or production deployment is included. This is a local portfolio demonstration.

A useful next experiment is a separate, labeled development set for relevance checking and a larger untouched evaluation set. Do not add special-case rules for the three known failures and then report the same questions as an independent test.

## Privacy and local behavior

The model client accepts only loopback HTTP endpoints, disables proxy use, and refuses redirects. The app rejects unrecognized hosts and cross-origin requests and does not enable CORS. It processes one live generation at a time. The demo server is intended for local use only.

Questions are not written to application request logs. The model server's own logging is controlled separately by llama.cpp. Custom corpora and responses are sent to that local model process; downloaded evaluation files contain their full recorded questions and evidence. Review any custom artifacts before sharing. `private-inputs/`, `reports/custom/`, `runtime/`, and `models/` are ignored by Git. Publishing or logging private material is not part of this demo.

## Repository

```text
evidence_desk/core.py          Retrieval, prompt, and source validation
evidence_desk/model.py         Local llama.cpp HTTP client
evidence_desk/evaluate.py      Development selection and task metrics
evidence_desk/server.py        Local live app endpoints
evidence_desk/template.html    Interactive live/report interface
evidence_desk/data/            Original fictional corpus and labeled questions
reports/evaluation/           Real saved model run and standalone report
scripts/                      Pinned Windows model/runtime setup
tests/                        Offline deterministic checks; no model download
```

See [VALIDATION.md](VALIDATION.md) for observed validation and hosted CI status, and [ATTRIBUTION.md](ATTRIBUTION.md) for model and runtime sources. Application code, corpus, questions, and authored report are MIT-licensed. Third-party model/runtime files retain their own licenses and are not included in the repository.
