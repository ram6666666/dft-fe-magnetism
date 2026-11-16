# QE 6.7 random wavefunction initialization: source-derived provenance

Scope: the configured static SCF path with atomic starting potential,
`startingwfc='atomic+random'`, no molecular dynamics, no FCP and no user modification
of the QE executable. This is source inspection, not an instrumented dump of the
running executable's RNG state.

## Exact source identity

Official QEF repository tag `qe-6.7.0`, commit
`a34dabb0f802ee27085d6f5cc0127e2c94cd2a93`:

- `Modules/random_numbers.f90`, SHA-256
  `9614e86bd2d9a39891470f13ff69aa3f3d641424dcf7d9e18c0abb517617db26`.
- `PW/src/wfcinit.f90`, SHA-256
  `3dc62e70b647af40f2ffb8db3cc73eaa4e09e01d6ccc62cd289c9d053592b32f`.
- Caller inspection in `PW/src`, `Modules` and `UtilXlib`; relevant matches retained
  in `rng_seed_call_sites_scoped.log`. A full-tree lazy-blob search hit its 40-second
  bound; that failed search is preserved and is not used to claim whole-repository
  absence of other RNG callers.

The official Debian 6.7-3 patch series was also inspected. None of the applied
patches modifies `random_numbers.f90`, `wfcinit.f90` or the relevant static-SCF RNG
initialization. Applied file paths are in `debian_active_patch_paths.json`.

Source URLs use the commit above under
`https://raw.githubusercontent.com/QEF/q-e/` and are recorded in the source probes.

## Algorithm and seed

The routine is QE's own `randy`, not the compiler's intrinsic `random_number`.
It uses a linear recurrence with `m=714025`, `ia=1366`, `ic=150889` and a 97-entry
shuffle table. The module declares saved `idum=0` and `first=.true.`. If no explicit
seed is passed, the first call deterministically initializes from **seed 0**.
If `randy(irand)` is called, the supplied integer is transformed to
`min(abs(irand),150889)` before initialization.

Initialization first replaces `idum` by `mod(ic-idum,m)`, fills the 97 entries by
repeated `idum=mod(ia*idum+ic,m)`, and advances once more to set `iy`. Each draw
selects `j=1+(97*iy)/m`, returns `ir(j)/m`, advances the recurrence and replaces
the selected shuffle entry. These details are taken directly from the function.

`init_wfc` calls `randy()` without an argument for the amplitude and phase of each
random complex coefficient. It either perturbs atomic wavefunctions or fills
missing wavefunctions, depending on `natomwfc` versus `nbnd`. In this version,
the small atomic perturbation branch requires
`max(natomwfc,nbnd)==natomwfc`; when there are too few atomic wavefunctions, the
additional functions are random instead. The exact branch is therefore determined
by the actual run's atomic-wavefunction and band counts, not just the input string.

The module also defines a clock-based `set_random_seed()`. In the inspected PW
call sites it is used by molecular-dynamics/FCP thermostat routines. That is a
different path from the static SCF configuration reviewed here; the mere existence
of that helper does not make these SCF wavefunction seeds time-based.

## What can and cannot be claimed

Use provenance such as:

```json
{
  "rng_algorithm": "QE6.7 randy: shuffled LCG, m=714025, ia=1366, ic=150889, ntab=97",
  "default_initial_seed": 0,
  "seed_evidence": "SOURCE_DERIVED_DEFAULT_FOR_CONFIGURED_STATIC_SCF_PATH",
  "seed_runtime_printed": false,
  "per_rank_internal_state_captured": false,
  "compiler_intrinsic_rng_used_for_this_wfc_path": false
}
```

Each process has its own saved module state. The default initial value is the same
zero; this is not evidence of independently seeded statistical streams. The mapping
from draws to coefficients depends on call order, k-point/band/G-vector distribution
and MPI/pool layout. Thus preserve rank count, pooling options, executable/source
identity and input together. Default seed 0 is deterministically source-derived;
the full evolving per-rank state is **not exposed by the ordinary run output and
was not captured**. Do not label it a runtime-measured seed dump or promise bitwise
identity across different parallel decompositions or numerical-library builds.
