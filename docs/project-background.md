# Project background

_Last updated: 2026-08-21. This document is a decision record synthesized from the discussions in the ChatGPT **DFT QMC COMPUTING** project. It is background, not yet the frozen scientific specification._

## Immediate purpose

The first objective is practical: reproduce the current DFT exam calculation and use that real task to rebuild a disciplined scientific-computing workflow. The project should not be inflated into a large study of autonomous scientific computing before the calculation itself has been run.

A second, deliberately modest objective is to acquire direct intuition for computational scale. The initial plan is to run representative calculations on a personal computer, record a few basic resource numbers, and only then judge whether cloud or institutional HPC resources are useful.

The repository name records the present physical theme (DFT / Fe magnetism), but the exact system, scientific target, code, pseudopotentials, functional, convergence protocol, and acceptance criteria must be specified separately in `shared/spec/` before substantive work begins.

## Two-track design

The same exam-reproduction task will be attempted through two independent tracks maintained in this repository.

### Human-led control track

The human track is the control. The user should make the scientific choices, reason through the calculation, write/modify the implementation, and form an independent interpretation of the results. During implementation, ChatGPT may be used for programming-language syntax, software syntax, command usage, or mechanical debugging when explicitly requested. It should not inject the physics strategy or interpret the scientific result before the user's own conclusion has been formed.

### AI-autonomous track

After the task specification is frozen, the AI track may autonomously plan the workflow, construct code and runnable inputs, test them, perform available calculations, check convergence/validation, inspect failures, iterate, and audit its own output within the available tool and compute environment.

### Isolation rule

Both tracks start from the same frozen specification. Intermediate reasoning, numerical results, and conclusions from one track should not be used to steer the other. Cross-track comparison belongs in `shared/comparison/` only after each track has reached an independent result or a documented stopping point.

The purpose of the comparison is practical rather than theatrical: understand where automation saves effort, where scientific judgment remains essential, and where apparently successful computation is or is not epistemically reliable.

## Role of GitHub and ChatGPT

GitHub is the engineering and audit layer: versioned source, input files, scripts, compact result summaries, provenance, diffs, and recoverable project states. ChatGPT Project conversations are the discussion/controller layer. The repository should remain usable without reconstructing old chat history.

The project should teach Git/GitHub through actual scientific work rather than through a separate software-engineering exercise. The core habit is: one scientifically meaningful change should correspond to a clear, recoverable commit. Avoid file-name versioning such as `final2`, `new`, or `really-final`; use Git history instead.

Repository naming convention adopted for scientific-computing projects:

`<method>-<system-or-topic>-<purpose>`

with an optional fourth qualifier only when it carries real information. This repository predates the full three-field form because its present scope is naturally captured by `dft-fe-magnetism`; the convention remains the default for future repositories.

## Minimal compute-cost intuition

Do not build a heavy telemetry system initially. For representative runs, record only what is useful for scale intuition:

- wall-clock time;
- CPU core count;
- peak memory when readily available;
- calculation type and the main numerical parameters;
- optionally, a crude core-hour estimate = cores × wall time in hours.

This is enough to learn whether a representative SCF is a seconds-, minutes-, or hours-scale job and how parameter sweeps multiply that cost.

The key distinction between a personal machine and professional HPC is not merely single-job speed. It is throughput and scheduling capacity: a parameter grid that is awkward when run serially on one computer may be routine when many independent jobs can be dispatched concurrently. This should be assessed from the actual exam workload rather than assumed in advance.

## Compute-backend policy at project start

Start locally if the calculation is feasible. First establish a minimal closed loop:

1. define the task;
2. construct a minimal valid input;
3. run it;
4. obtain a successful output;
5. extract the scientific quantity of interest;
6. perform a basic sanity check;
7. preserve enough provenance to reproduce the run.

Only after this first loop should the project decide whether more systematic convergence work, cloud execution, CINECA/other HPC, automated batching, or runners are worth adding.

## Working repository structure

```text
dft-fe-magnetism/
├── README.md
├── docs/
│   └── project-background.md
├── shared/
│   ├── spec/
│   └── comparison/
├── human-control/
│   ├── inputs/
│   ├── scripts/
│   ├── runs/
│   └── results/
└── ai-autonomous/
    ├── inputs/
    ├── scripts/
    ├── runs/
    └── results/
```

This is intentionally a minimal starting structure. Add complexity only when a real computational need appears.
