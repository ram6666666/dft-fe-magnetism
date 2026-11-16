# FeSe independent scientific plan, draft before pilot

2026-11-16, GPT independent lane. This draft authorizes only the already permitted bounded capability pilot. A versioned production plan will be frozen after real timing and diagnostics, before a production sweep. SOURCE_READING.md is the preproduction source-to-calculation table.

## Scientific design

Use a common eight-atom/four-Fe supercell for FM, checkerboard AFM, stripe AFM, and the central non-spin-polarized reference. Original tetragonal axes have lattice parameter a. The supercell vectors are (a,a,0),(-a,a,0),(0,0,c), so volume is 2 a^2 c. In its fractional coordinates Fe sites are (0,0,0),(.5,0,0),(0,.5,0),(.5,.5,0). Se sites at (.25,.75,z),(.75,.25,z),(.25,.25,1-z),(.75,.75,1-z) form alternating tetrahedral caps. This follows the PbO structure; it is an independently derived coordinate/origin representation.

Fe spin signs in that order are FM (++ ++), CB (+--+), stripe (+-+-), with stripe chains parallel to the second supercell axis. Nearest Fe separation is a/sqrt(2). The patterns repeat along c: no antiferromagnetic interlayer doubling is included. All Fe sites use identical supplied PBE NC scalar-relativistic UPF bytes; separate species labels initialize opposite signs. No total/local magnetic moment is constrained. Symmetry can retain the chosen collinear subspace, so these are self-consistent states within imposed cell/topology and starting conditions, not exhaustive unconstrained global searches. No SOC, Hubbard U, dispersion correction or structural distortion is included.

The primary proposed scan is a/a0=0.98,1.00,1.02 about a0=3.765 Angstrom, with fixed c=5.518 Angstrom and fractional z=0.2343 (Subedi Table I). Because c is fixed, the Se height is also fixed at z*c. Neither c/a nor volume is fixed. All ionic coordinates and the tetragonal metric are fixed; this tests an in-plane strain path, not an equation of state, pressure relaxation or an optimized lattice constant. More points may be added only as an explicitly logged extension if the pilot makes them economical.

PBE is required by the common supplied pair and differs from Subedi's magnetic LDA LAPW method. The primary energy quantities are QE's consistent smeared SCF energy, differences between completed states at a fixed structure, divided by four Fe and converted using 1 Ry=13.605693122994 eV. Smearing sensitivity is mandatory before a zero-temperature ordering claim. A nonmagnetic central reference permits a qualified source comparison; projected Fe moments are not treated as equal to LAPW-sphere moments.

## Numerical target and pilot

Declared energy-difference accuracy target: 1 meV/Fe for the evaluated ordering; SCF tolerance alone does not certify this. Initial pilot uses 60/240 Ry wavefunction/density cutoffs, 4x4x3 Gamma-centered supercell grid, Marzari-Vanderbilt smearing 0.02 Ry, SCF threshold 1e-7 Ry per cell, 84 bands per spin and starting Fe polarization +/-0.15 per 16 valence electrons (about +/-2.4 muB atomic seed). These are independent provisional choices, not parameters copied from the paper's phonon calculation. The pilot is capped at 360 seconds within QE, plus a 60-second external cleanup margin.

Production candidates will test 60/80/100 Ry and grids beginning at 6x6x4, then 8x8x6 or finer if feasible; narrower smearing 0.01 Ry (and 0.005 if a decision is sensitive) will separate integration artifacts from physical conclusions. Test energy differences, not only absolute energies. The precision gate and final number of points depend on actual compute feasibility, not on a desired source match. Repeat one representative state from a fresh directory; test lower magnetic seeds where collapse/metastability matters.

Final-state evidence will combine cell total/absolute spin with projwfc.x Lowdin site polarizations. Below 0.05 muB per Fe plus cell absolute spin/Fe below 0.05 is a declared collapsed-state label. Missing projection diagnostics mean UNVERIFIED_FINAL_STATE. A zero net moment alone never certifies AFM.

## Persistence and stop policy

Each attempt has a unique directory, exact input/config, stdout/stderr, command, timestamp, executable/input/pseudo hashes, status and parsed values. A failure remains in the table. The parser requires explicit convergence plus JOB DONE and a successful process. Source, input, raw text evidence and tables remain below 1 MiB/file and are checkpointed to assigned Drive plus the owned GitHub branch before protected continuation. Scratch/wavefunctions are reproducible by a full fresh run and are not required for restarting this campaign; they remain locally retained but have no independent bulk backup. No expensive continuation may silently depend on unprotected scratch.

Priority: real pilot and pipeline check; central magnetic/NM comparison and convergence; minimal three-point, three-start scan; targeted sensitivity and clean replay; qualified report and independent freeze. If a reliable energy ordering remains unresolved, deliver the actual scientifically partial outcome and exact continuation commands. No source curve or numeric result will be invented.
