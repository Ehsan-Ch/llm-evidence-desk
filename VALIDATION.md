# Validation record

Date: 2026-10-14.

- **33 offline automated tests passed** on Python 3.12.14 / Windows. The suite uses controlled model doubles for failure paths and needs no model download. Those tests do not claim to measure model intelligence.
- **Real model evaluation:** 19 actual Qwen3-0.6B Q8_0 calls over 20 labeled evaluation questions. One question had no retrieval hit and was handled before generation. No canned responses or simulated inference were used in the saved model run.
- **Task results:** 17/20 passed; all 16 answerable questions passed; only 1/4 unknown questions correctly abstained. All three unknown questions sent to the model received irrelevant source-valid quotations.
- **Retrieval development:** six separate questions; k=1 selected before evaluation. The prompt was finalized using a development question before the evaluation run.
- **Citation checks:** all 19 generated candidates passed source checks. The failing task examples show the limits of provenance-only validation.
- **Browser checks:** live form, failed-case filtering, source inspection, and raw-output disclosure checked in the interactive app.
- **GitHub Actions:** workflow supplied; observed hosted status will be recorded after publication. Local tests and the real local model evaluation do not establish a passing hosted run.

The bundled dataset is small and fictional. No production-reliability claim follows from these results.
