# Validation record

Date: 2026-10-14.

- **33 offline automated tests passed** on Python 3.12.14 / Windows. The suite uses controlled model doubles for failure paths and needs no model download. Those tests do not claim to measure model intelligence.
- **Real model evaluation:** 19 actual Qwen3-0.6B Q8_0 calls over 20 labeled evaluation questions. One question had no retrieval hit and was handled before generation. No canned responses or simulated inference were used in the saved model run.
- **Task results:** 17/20 passed; all 16 answerable questions passed; only 1/4 unknown questions correctly abstained. All three unknown questions sent to the model received irrelevant source-valid quotations.
- **Retrieval development:** six separate questions; k=1 selected before evaluation. The prompt was finalized using a development question before the evaluation run.
- **Citation checks:** all 19 generated candidates passed source checks. The failing task examples show the limits of provenance-only validation.
- **Browser checks:** live form, failed-case filtering, source inspection, and raw-output disclosure checked in the interactive app.
- **Packaging:** installed successfully in a fresh virtual environment. All 33 tests passed there. All 20 saved results were replayed through the current validator/evaluator and matched their recorded outcomes.
- **GitHub publication:** all 24 project files uploaded and verified. Model weights and runtime binaries are excluded.
- **GitHub Actions:** [run 38587822513](https://github.com/Ehsan-Ch/llm-evidence-desk/actions/runs/38587822513), for code commit `c88625d35e97b8d764fae75987f383cd21718529`, was blocked with zero job steps. GitHub reports: "The job was not started because your account is locked due to a billing issue." This is not a passing hosted run or an observed test failure. The workflow can be rerun when the account issue is resolved.

The bundled dataset is small and fictional. No production-reliability claim follows from these results.
