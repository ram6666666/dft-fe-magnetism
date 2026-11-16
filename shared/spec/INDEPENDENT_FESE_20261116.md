# Common independent FeSe benchmark contract

This frozen task is shared by the GPT and Claude AI lanes. Both branches start at commit ea051074ffc1bcac961a1c291ab7bdb565ed4a22.

## Objective

Independently reconstruct a reproducible Quantum ESPRESSO workflow from the supplied original papers for FeSe FM, checkerboard AFM and stripe AFM total energies along a clearly declared lattice-parameter path. Independently choose, prerecord and justify implementation and numerical settings; actually attempt execution; check numerical reliability and the final physical state; explain valid paper comparisons and scope extensions. Effective-J extraction is deferred.

Preserve runnable source, meaningful comments, exact actual inputs and pseudopotential identity, environment, commands, raw success/failure logs, data, scientific interpretation and recovery instructions. Generated inputs, process completion and scientific reproduction have distinct status. Do not invent missing numerical results.

## Immutable shared packet identity

- Original requirements: 01_TASK_REQUIREMENTS.md
- Requirements SHA256: 6384fbedfd36bcc6a37c1a831a0f23c60bd42e170737a00d7c5460c7fd2a3c8a
- Source-manifest SHA256: c2ba78fd29b50ceefd80392ec613c3119e1fb895613eb0c08e825a5d650d7544
- Complete input archive SHA256: 879229403c100b6bbf86b7928723a4ccc033f41a0ad67899f2371b1b863de240
- Sources: Subedi et al., DOI 10.1103/PhysRevB.78.134514; Yildirim, DOI 10.1103/PhysRevLett.101.057010; Johannes, DOI 10.1103/Physics.1.28.
- Common pseudopotential family: PseudoDojo ONCVPSP-PBE-SR v0.4.1 Fe/Se pair; exact bytes/hashes are in the immutable input manifest.

The full source packet and receiver-specific authorized locations are provided separately through the private task handoff. This public index does not publish the original PDFs or private storage locators. Actual source reading by each executor is required.

## Independence

Each AI receives the same scientific/evidence contract, with only actor and destination substitutions. It reads the common inputs, allowed public documentation and its own work. It must not inspect or merge other lanes' scientific code, numerical choices, logs or results until its independent outcome is frozen and comparison is authorized.

The human lane is user-directed and will be created separately. Do not write human-control/. No AI scientific solution preview is sent to the user before they ask for comparison. Branch separation is procedural and does not prevent access.

Record actual environment/resources, substantive added sources, external interventions and any prior complete implementation exposure. A fresh prompt is not proof of separate hardware. Report what actually executed.

## Checkpoints and public content

Publish public-safe code, configuration, small raw logs, data and independently authored reports on the owned branch at natural scientific boundaries. Primary evidence and hot working checkpoints use the assigned durable project storage. Keep private discussions/control records, restricted source PDFs, credentials and private storage identifiers out of this public repository. Heavy QE scratch does not belong in Git.

Do not force-push, rewrite history, merge to main or merge peer branches. Freeze the first independent result or documented stopping point with exact commit and hashes. Later comparison-informed changes preserve that initial version.

This contract records task authority and evidence requirements, not a scientific result.
