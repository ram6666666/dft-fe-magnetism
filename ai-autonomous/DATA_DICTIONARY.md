# Result definitions and evidence hierarchy

`runs/<run_id>/input.in`, raw `pw.out`/`pw.err`, postprocessing output when run,
`config.json`, execution records and `receipt.json` are the observation layer.
`parsed.json` is the parser result produced at that attempt's end. Its source
version is frozen by SHA256 under `source_versions/`. `results.json`/`.csv` are
regenerable collected views. `analysis_plot.py` independently reopens actual
records, verifies hashes and reparses raw outputs before selecting plot points.
An index row never rescues a failed raw-output gate.

## Identity and structure

| Field | Meaning |
| --- | --- |
| `run_id` | Unique immutable attempt; repairs/replays use a new ID |
| `stage` | Planned role, such as pilot, baseline, sensitivity or replay; not a success label |
| `path_id` | Fixed-c,z tetragonal lattice-path identity |
| `a_ang`, `c_ang` | Tetragonal lattice parameters in Angstrom; supercell vectors A=(a,a,0), B=(-a,a,0), C=(0,0,c) |
| `z_se` | Fractional height; physical height is z_se*c_ang |
| `n_fe` | Four Fe atoms in each computed eight-atom cell |
| `functional`, `pseudo_sha256` | Actual PBE model and exact common UPF identities |
| `qe_version`, `pw_sha256`, `projwfc_sha256` | Actual executable banner/hashes, not package-name inference alone |
| `runtime_profile_sha256` | Hash over resolved numerical-library names and byte hashes |
| `source_sha256` | Generator/runner source version used by this attempt |
| `input_path`, `log_path`, `receipt_path` | Relative source-evidence paths from ai-autonomous/ |

## Numerical settings

`ecutwfc_ry` and `ecutrho_ry` are plane-wave and density cutoffs in Ry.
`kgrid` and `kshift` are the three integer automatic-grid divisions and shifts in
the common supercell. `gamma_only=true` means the distinct Gamma algorithm;
the Gamma pipeline pilot is never selected as a production point.
`degauss_ry` is the cold-smearing width. `conv_thr_ry` is the requested electronic
SCF threshold per cell, not an uncertainty bound on magnetic energy differences.
`nbnd` includes unoccupied bands. Mixing and maximum-step metadata remain in JSON.

`starting_polarization` is the QE6.7 fractional Fe valence spin polarization.
It is an initial condition, not a constrained local magnetic moment. The exact
command records ranks, k pools and CPU binding; the environment records BLAS and
OpenMP threads plus MPI temporary/backing directories. RNG default seed zero is
source-derived for this static-SCF path. Evolving per-rank streams were not
runtime-dumped; the clean replay tests the actual operational repeatability.

## Energies and moments

| Field | Definition |
| --- | --- |
| `energy_total_ry` | Final QE printed total energy for all four Fe and four Se; includes the printed finite-smearing contribution |
| `energy_per_fe_ry` | energy_total_ry / 4 |
| `relative_to_group_min_mev_fe` | Difference from the minimum completed energy at identical collected physical/numerical settings; all observed initializations in that group may contribute |
| `relative_to_nm_mev_fe` | Difference from the explicit nspin=1 reference at matched geometry/settings, if it exists |
| `energy_relative_common_zero_mev_fe` | Plot-only difference from one identified fixed reference across every lattice point; never a separate zero at each a |
| `total_magnetization_muB_cell` | QE cell-integrated signed spin density, if printed |
| `absolute_magnetization_muB_cell` | QE cell integral of absolute spin density, if printed |
| `fe_lowdin_moments_muB` | Signed projected spin populations for Fe1–Fe4 in the exact input order |
| `all_lowdin_moments_muB` | The same diagnostic for all eight atoms |

Conversion: 1 Ry = 13.605693122994 eV; energy differences in meV/Fe multiply a
cell difference in Ry by 13.605693122994*1000/4. Absolute energies from different
methods are not subtracted. Lowdin moments are partition-dependent and differ
from the paper's LAPW-sphere moments.

`initial_state` is the intended start. `final_state` uses actual projected Fe
signs plus cell integrals; a near-zero total moment alone never proves AFM or NM.
The predeclared collapsed threshold is every Fe magnitude below0.05 muB and
absolute cell magnetization/Fe below0.05 muB. `NM_ENFORCED_NSPIN1` is a separate
imposed reference. Its projected moments remain null because no magnetic
projection was performed. The first NM parser record retained the old generic
diagnostic phrase; the collected view corrects that description while preserving
the original record. No value is invented or altered by this annotation.

## Status and cost

`RUN_COMPLETED` requires a successful QE exit, explicit SCF convergence, final
energy and completed output. `RUN_FAILED`, `UNCONVERGED`, `RUNNING` and `NOT_RUN`
are retained and excluded from accepted numerical comparisons. An external
context interruption can leave QE exit and elapsed cost unknown; separate
interruption receipts preserve the last live evidence without inventing an exit.
Successful SCF is distinct from numerical adequacy and source comparison.

`elapsed_seconds` measures that SCF attempt's wall time; postprocessing has its
own execution record. Summing per-run wall times is not the elapsed campaign
time when runs overlap. Child CPU totals are OS-accounted where exposed;
maximum RSS is a child high-water mark, not measured simultaneous node memory.

Null JSON values and empty CSV cells mean unavailable or inapplicable data.
They never mean numerical zero. Arrays/maps are JSON strings inside CSV cells.
Every final report and plot identifies its exact selected run IDs and exclusions.
