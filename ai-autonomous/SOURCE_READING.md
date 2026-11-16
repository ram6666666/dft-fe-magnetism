# Original-source reading and calculation map

Task: FESE-GPT-WORK-20261116-R01. Prepared independently on 2026-11-16 before production. The acting GPT worker reopened every original PDF, computed SHA256, extracted its full text locally, and read that text. Critical visual checks: Subedi printed page 134514-2 (Table I including signs/headers), 134514-3; Yildirim printed page 057010-2 (cell diagram, both magnetic patterns and fixed-moment plot). The three PDFs were respectively 6, 4 and 3 pages. No previous lane input, implementation or results were read. Local extracts are reading aids; original PDF identity is authoritative.

| Original | SHA256 | Scope actually read |
| --- | --- | --- |
| Subedi et al., PRB 78, 134514 (2008), DOI 10.1103/PhysRevB.78.134514 | 576ef9042df458a3814fd64a0c23060986b37ca62777d3983b21c22d4e6bd1ef | All six pages; particular attention to Sec. II, Table I, Sec. IV and footnote 24 |
| Yildirim, PRL 101, 057010 (2008), DOI 10.1103/PhysRevLett.101.057010 | 22d5412cf6c46651adcd2debb8a2390b2fcb4cd60c98b082889fa8951d91c8f9 | All four pages; Fig. 1 cell transformation, Fig. 2 magnetic topology, Fig. 3 constrained-moment semantics, Fig. 4 structural path |
| Johannes, Physics 1, 28 (2008), DOI 10.1103/Physics.1.28 | 70cbc25cc00438959346f9c3cb1d246862524d448abfa7c16af9c8b12130b20f | All three pages, including references; contextual interpretation, no new numerical target |

## What the sources support

Subedi asks how the simpler PbO-structure iron chalcogenides relate to the iron arsenides. Its electronic and magnetic calculations use LDA with all-electron LAPW plus local orbitals. Its phonon/electron-phonon work uses PBE Quantum ESPRESSO with a different pseudopotential construction. The software name in the latter calculation does not make the magnetic Table I a PBE/QE target. The table uses experimental a,c and non-spin-polarized LDA-minimized chalcogen heights, kept fixed for the SDW calculation (Sec. IV). FeSe values are a=3.765 Angstrom, c=5.518 Angstrom, zSe=0.2343. The Fe moment 0.65 Bohr magneton is integrated in a LAPW sphere of radius 2.1 bohr, not a whole-cell or projector moment.

Table I prints the positive number 5 for FeSe and 47 for FeTe under E_SDW although its caption says energy relative to the non-spin-polarized state. The surrounding text identifies the SDW instability and explicitly calls the FeTe number an energy gain. We therefore preserve the printed numbers as stabilization magnitudes and interpret the FeSe comparison as E_SDW-E_NM approximately -5 meV/Fe; this sign interpretation is disclosed, not silently changed. No numerical curve was digitized. The article reports no ferromagnetic instability in its FeSe LDA calculation. It does not report the present three-configuration FeSe energy-versus-a scan. Its dependence on chalcogen height makes the structural path load-bearing.

Yildirim concerns LaFeAsO, not FeSe. Its AFM1 has opposite nearest-neighbor spins; AFM2 has alternating rows, with opposite next-nearest-neighbor spins. Figure 1 uses a sqrt(2) by sqrt(2) crystallographic supercell. The principal energy curves are all-electron LDA fixed-local-moment scans, followed by unconstrained optimizations; Figure 4 changes a shear angle and permits orthorhombic distortion. Neither those LaFeAsO moment values nor the energies become FeSe targets. The paper explains why a magnetic starting label cannot certify the final state and why different magnetic/structural restrictions change comparisons. Its approximate exchange mapping is outside this task.

Johannes motivates FeSe as a simpler chemical testbed and discusses the distinction between a static DFT moment and fluctuating magnetism. It supplies no independent FeSe numerical convergence recipe. Its 2008 physical hypotheses and trends are treated as historical context, not experimentally established present-day conclusions or validation of this calculation.

## Source-to-calculation table (before production)

| Source target and location | Definition and conditions | Planned calculation | Correspondence and acceptance boundary |
| --- | --- | --- | --- |
| Subedi Table I / Sec. II-IV: FeSe structure | Experimental a,c; nonmagnetic LDA zSe | Adopt a0,c,z exactly for a fixed-geometry PBE baseline | Structural inputs reused; not a relaxation reproduction |
| Subedi Table I: FeSe SDW stabilization, printed 5 meV/Fe | LDA LAPW, fixed nonmagnetic-relaxed z; energy gain versus NM | Separate nspin=1 reference at central structure; stripe-start PBE SCF, difference per 4 Fe | Reproduction with substantial method differences; only qualified trend comparison, not a 1 meV match claim |
| Subedi Table I: 0.65 muB/Fe | Fe LAPW sphere radius 2.1 bohr | Fe Lowdin spin populations from projwfc.x, plus total and absolute spin integrals | Different local observable; characterize state, do not compute a misleading percent error |
| Subedi Sec. IV: no FeSe FM instability | LDA at specified geometry | Unconstrained FM starts, inspect final state and compare NM | Qualitative check with different functional/pseudos; convergence from a finite start is not a global stability proof |
| Yildirim Figs. 1-2 | LaFeAsO cell and NN/NNN spin topology | Derive same topology for Fe square plane in FeSe | Methodological transfer only; no LaFeAsO numerical energies/moments used as FeSe targets |
| Yildirim Fig. 3 | Energy versus constrained Fe moment, LaFeAsO | No fixed-moment scan in this deliverable | Not reproduced; ordinary initialized SCF has different semantics |
| Teacher scoped FeSe FM/CB/stripe energy versus a | No identical curve in supplied sources | Fixed c,z tetragonal in-plane scan, same 4-Fe cell | Project extension; each point needs converged SCF and final-state diagnostics |
| Johannes pp. 1-2 | Historical superconductivity/magnetism context | Explain limits of static PBE energy ordering | Context only; no superconductivity or experimental ground-state claim |

## Allowed added documentation and exposure

Consulted official QE INPUT_PW online manual (displayed version 7.5 on 2026-11-16) for routing, then retrieved QE 6.7 tagged INPUT_PW.def and INPUT_PROJWFC.def for the actually installed release. Inputs use fractional starting magnetizations within [-1,1], valid in QE 6.7; these are initial polarizations per valence electron, not fixed magnetic moments. General official documentation is the only scientific code assistance. Runtime package installation is engineering assistance recorded separately. No authentic author input/scripts or complete reproduction implementation was obtained.
