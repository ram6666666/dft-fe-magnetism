# Numerical execution notes

The mesh and narrower-smearing evaluations retain the prespecified basis, k meshes and smearing widths. Later implementation checkpoints added the option to warm-start the narrower-smearing check from the corresponding converged dense-mesh run at the broader width. This reduces startup cost without changing the physical model or final SCF tolerance. Each warm start records exact parent attempt and copied scratch digests. The observation is a test of how that basin responds to the occupation width. It does not independently search for an alternative magnetic basin.

The dense-mesh input uses QE disk_io='low' to retain the restart scratch during the continuous run. If it is unavailable on recovery, preserve the interrupted or missing attempt, rerun the archived parent or use a new explicitly named cold-start diagnostic with otherwise identical settings. The exact finite-width comparisons use only accepted self-consistent outputs under matched settings at each width.

The independent representative replay starts freshly, with a single MPI rank rather than two k-point pools. It tests whether the reduction/decomposition materially changes the result under the stated tolerance.
