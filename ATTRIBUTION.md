# Attribution and reproducibility

- [Qwen/Qwen3-0.6B-GGUF](https://huggingface.co/Qwen/Qwen3-0.6B-GGUF): official Qwen model, Apache 2.0. Pinned revision: `23749fefcc72300e3a2ad315e1317431b06b590a`. The Q8_0 file is 639,446,688 bytes. It is downloaded separately, not redistributed here.
- [llama.cpp b11617](https://github.com/ggml-org/llama.cpp/releases/tag/b11617): local inference engine, MIT. The Windows CPU archive is downloaded separately, not included in this repository.
- [llama.cpp server documentation](https://github.com/ggml-org/llama.cpp/tree/master/tools/server): local chat-completion endpoint, schema-constrained JSON, and `enable_thinking` template setting.

`runtime-reference.json` records observed file checksums and runtime settings for the published run. The setup helper verifies those hashes. A rerun on another build or machine may differ even with a fixed sampling seed.

All handbook facts, organization names, dataset questions, task labels, and adversarial examples were authored specifically for this project. NorthstarOps, Harbor Desk, Boreal archive, and Meridian register are fictional names used in the example corpus. These materials do not represent any real organization's procedures or requirements.

This project does not claim to have trained the model. The work is retrieval, evidence selection, validation, evaluation design, local serving, and the inspection interface.
