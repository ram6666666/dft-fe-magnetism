# Frozen independent production plan R01

Task FESE-GPT-WORK-20261116-R01. Prepared on 2026-11-16; becomes active only after exact Drive and owned-branch readback. The actual persistence receipt records that timestamp and commit. It supersedes the draft for production; the draft and all pilots remain evidence. No other lane's scientific work has been consumed. The source-to-calculation table in SOURCE_READING.md is incorporated unchanged.

## 1. Scope and geometry

Compute fixed-geometry FeSe in FM, checkerboard and stripe starting configurations, compare final self-consistent states and map total energy along an in-plane lattice path. This is an independently reconstructed PBE QE extension of the supplied papers, not the authors' original code or a claim to reproduce a published FeSe three-configuration lattice curve.

All calculations use a four-Fe/four-Se cell with vectors A=(a,a,0), B=(-a,a,0), C=(0,0,c), in Angstrom. Fe fractional positions are (0,0,0),(.5,0,0),(0,.5,0),(.5,.5,0). Se positions are (.25,.75,z),(.75,.25,z),(.25,.25,1-z),(.75,.75,1-z). This is a determinant-two transform of tetragonal Fe(0,0,0),(.5,.5,0), Se(.5,0,z),(0,.5,-z). The nearest Fe distance is a/sqrt(2), and the nearest-neighbor square axes are A/2 and B/2.

Initial Fe signs in the above order: FM (+,+,+,+), checkerboard (+,-,-,+), stripe (+,-,+,-). The checkerboard has all four NN antiparallel and all NNN parallel; stripe has two NN parallel, two opposite and all four NNN opposite. Collinear species Feu/Fed share the identical Fe UPF. Neither total nor site moment is constrained. Translational/symmetry subspaces and one-layer c periodicity restrict the accessible solutions; this is not an exhaustive search over noncollinear, different interlayer, larger-period or disordered magnetic states.

The minimal complete path has a=3.6897,3.7650,3.8403 Angstrom (0.98,1,1.02 times the Subedi Table I reference), c=5.518 Angstrom and zSe=0.2343 held fixed. The physical Se height z*c=1.2928674 Angstrom is therefore fixed. Volume and c/a vary. No atomic relaxation, orthorhombic shear or c optimization is permitted in this primary path. A minimum among sampled points is not an optimized equilibrium lattice parameter or pressure equation of state.

## 2. Model and numerical baseline

Use common PseudoDojo ONCVPSP PBE SR v0.4.1 Fe/Se UPFs with the exact frozen hashes in fese.py. Both have 16 valence electrons; the cell has 128 electrons. No SOC, U, empirical dispersion or alternate functional is used. QE is the actual Debian 6.7-3+b1 build reporting 6.7MaX, with recorded executable/projection/numerical-library hashes. The opt-in LP64 OpenBLAS profile is used for new production cases; no equivalence to a different build is presumed.

Baseline: 90 Ry wavefunction cutoff, 360 Ry density cutoff, a 2x2x2 Gamma-centered automatic grid in this supercell, cold (Marzari-Vanderbilt) smearing 0.02 Ry, 84 bands, SCF threshold 1e-7 Ry/cell, mixing_beta=0.3 and 120 SCF iterations. Initial Fe polarization is +/-0.15 per valence electron. These values are explicit independent choices. The 90 Ry baseline uses the largest common PseudoDojo normal hint; the coarseness of the k mesh is a resource-driven provisional choice, not an adequacy claim. A converged SCF on that grid is not a numerically converged metallic energy difference.

The declared energy-difference accuracy target remains 1 meV/Fe. Basis, k mesh, smearing and magnetic-basin checks gate any physical ordering claim. The finite-smearing energy is QE's printed total energy including its smearing contribution; no unreported zero-smearing extrapolation is applied. An observed gap smaller than the sensitivity envelope is unresolved. If the target is not met, the outcome is scientifically partial even if every baseline SCF succeeds.

## 3. Prespecified execution sequence and adaptation

1. Complete the central baseline triplet and a separate nspin=1 central reference; inspect actual convergence, moments, band occupations and errors. Baseline directories start `B_`.
2. Complete the two outer a values for all three magnetic starts, retaining collapses and failures. This gives the minimal measured energy-versus-a dataset, without asserting its numerical adequacy.
3. At a0 compare 90 versus 110 Ry (density cutoffs 360 versus 440 Ry) for all three starts; compare k grids 2x2x2 and 4x4x3 at the same 90 Ry; compare 0.02 and 0.01 Ry smearing at otherwise identical baseline settings. These directories start `C_`. The already running P003 is 60 Ry and cannot replace a 90 Ry k-mesh check. The Gamma-only P004 is pipeline evidence and excluded from production curves.
4. Repeat a central stripe case from a fresh directory with identical settings. Test lower starting polarization +/-0.03 at the central structure for all three starts where feasible. Preserve any different basin; choose the lowest observed comparable converged state only with the initialization caveat. Directories start `D_`.
5. If differences exceed 1 meV/Fe, do not label the curves numerically converged. If affordable within this execution unit, add the next discriminating setting (basis 130 Ry if basis fails; grid 6x6x4 if k sampling fails; narrower smearing only together with a sufficient mesh). Such added cases are explicitly exploratory successors and require an additive decision entry. They never overwrite R01 observations or silently redefine the original baseline.

The observed maximum change in each relevant magnetic energy difference supplies an empirical sensitivity envelope, not a rigorous error bound. Basis changes couple wavefunction and density cutoffs in the declared 4:1 ratio. Only compare a state across settings if its final spin topology remains the same; otherwise report both basin change and numeric change. Do not subtract absolute energies from different electronic-structure methods.

## 4. Real feasibility evidence and resource decision

P001 and P002 really executed QE and stopped at the executor-selected 360 s caps (370.31 and 369.24 s actual wall); neither converged. These are not platform wall-clock limits. P003 is a bounded 1800 s test with two independent k pools, ongoing at plan preparation. P004 completed a Gamma-only SCF in 65.05 s and projection in 2.93 s; this proves the end-to-end path but not reciprocal-space adequacy. Its measured cost plus the actual iteration times of the denser pilots motivate an initial estimate of roughly 5-20 minutes per baseline/diagnostic run, with substantial uncertainty and state-dependent SCF behavior.

Use two MPI ranks/two k pools for general-grid attempts, one OpenMP/OpenBLAS thread per rank. Up to three independent runs may overlap, bounded by the exposed nine CPUs and approximately 9.7 GiB RAM; include the ongoing two-rank pilot in that resource count. Per-run QE cap is 1800 s, external cleanup bound 1860 s. The producer chooses an initial production natural-unit budget of 7200 s elapsed wall from the first baseline launch, preserving a checkpoint before extending it. This is a deliberate resource management choice, not a user-imposed or measured platform hard cap, and may be extended with an explicit own decision if continuation has high value. No paid resources or personal-machine compute is used.

Priority under an incomplete budget: preserve complete executable source and failures; actual central triplet/NM; complete minimal path; the most discriminating convergence check; clean replay and remaining sensitivities. Report all unfinished prespecified cases as NOT_RUN, not successful or zero-valued. No work is declared to continue after this worker ends.

## 5. Observables, status and comparison gates

For a fixed a and identical numerical settings, Delta E=(E_i-E_j)*13.605693122994*1000/4 in meV/Fe. The factor four is the actual Fe count. A displayed E(a) plot uses one common constant reference across all points; identify its run ID. The suggested reference is the completed central baseline stripe energy, with a disclosed alternative if it is missing. A per-a minimum is only an ordering table, never the E(a) zero.

Require successful process exit, explicit SCF convergence, final energy and completed output; JOB DONE alone is insufficient. Require all four Fe Lowdin site moments from the actual saved SCF wavefunctions plus cell total/absolute spin integrals. A net zero moment alone does not distinguish stripe, checkerboard or nonmagnetic. Fe magnitude below 0.05 muB together with absolute cell spin/Fe below 0.05 is the declared collapsed-state threshold. Projection moments are partition-dependent and incomparable as exact numerical errors to Subedi's 2.1-bohr LAPW sphere moment. Their signs and topology identify the magnetic state.

The primary source comparison is PBE versus the paper's LDA LAPW magnetic energy stabilization at fixed paper geometry, with explicit method differences. No direct numerical reproduction claim is licensed by qualitative agreement. The fixed-moment LaFeAsO energy curves in Yildirim are not reproduced and are not FeSe targets. Effective J, phonons and superconductivity remain out of scope.

## 6. Reproducibility, persistence and completion

Each actual attempt has an immutable source snapshot, exact generated input, configuration, executable/library identity, command, start/end/exit/timing, raw stdout/stderr, projection output, parsed values and checksums. QE's static-SCF randy seed 0 is source-derived for this release, not runtime-printed; full internal rank streams are unexposed, and MPI/pool settings are retained. No initial or restart state is imported from another lane or unprotected previous scratch.

At natural triplet boundaries collect results once, create immutable snapshots, verify primary Drive readback and exact independent Git blob identity on the owned branch. Required text stays below 1 MiB per artifact. Reproducible software and scratch binaries are separate from irreplaceable scientific evidence; no continuation requires an unbacked binary checkpoint. A self-review/helper check is not an independent audit.

Final freeze binds the report, actual table/figures, raw evidence, source, manifest, exact commit, intervention declaration and resume instructions. Completion is reported separately as execution, numerical adequacy and source comparison. No cross-lane scientific opening occurs until independent freeze and the user's later comparison request.
