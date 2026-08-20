# Human-control track

This directory is the independent human-led control track.

The scientific strategy, implementation choices, and interpretation should originate from the user. Before the user forms an independent conclusion, AI assistance in this track should be limited to explicitly requested programming-language/software syntax, command usage, or mechanical debugging. Physics strategy and scientific interpretation should not be imported from the AI-autonomous track.

Suggested subdirectories:

- `inputs/` — calculation inputs used by the human track;
- `scripts/` — helper/analysis scripts written for this track;
- `runs/` — lightweight run records and manifests; keep bulky scratch data out of Git;
- `results/` — compact processed results, tables, figures, and conclusions.

The track should start from the same frozen specification as `ai-autonomous/`, but thereafter remain independent until the comparison gate.
