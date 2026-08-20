# dft-fe-magnetism

Computational project for reproducing the current Fe-magnetism DFT exam task and comparing two independent workflows under one shared, frozen task specification.

## Repository layout

- `human-control/` — the user's independent control track.
- `ai-autonomous/` — the AI-autonomous track.
- `shared/spec/` — task definition shared by both tracks once frozen.
- `shared/comparison/` — cross-track comparison, opened only after independent work is complete.
- `docs/project-background.md` — project decisions recovered from the ChatGPT DFT/QMC project discussions.

The project is deliberately lightweight at this stage. The immediate goals are to reproduce the exam calculation, establish a clean and recoverable scientific-computing workflow, and develop an order-of-magnitude sense of computational cost. Cloud/HPC resources will be considered only if the actual workload justifies them.

The exact scientific task, software stack, numerical parameters, and acceptance criteria are not yet frozen. Those belong in `shared/spec/` before the two tracks begin substantive independent work.
