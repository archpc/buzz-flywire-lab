# Buzz lab — Phase V report: Banana Peel (sugar-GRN stimulation, MN9 readout)
Date: 2026-10-19. No kernel-metal changes; all code additive on `lab-bridge` (commits 1ab55ff, cf0bf7e — one compile fix caught before any results were accepted).

## 1. What was built

- **`stim_trial` kernel primitive**: settle → deterministic current drive at explicitly targeted neuron indices → post-stimulus silence, with per-step spike-membership recording for up to 256 watched neurons. Uses the kernel's existing external-drive path (extInput: `vi += extInput[gid]` each step) — the same drive class as the loom port. Zero changes to LIF.metal or the StepParams contract; GPUCHECK and simtest re-verified PASS after the change.
- **Stimulus population**: the 21 sugar-sensitive GRNs of the Shiu-lineage feeding-initiation experiment (fly-brain repo `code/benchmark.py` experiment `sugar`, 200 Hz Poisson in the original). All 21 FlyWire root IDs verified present in the specimen connectome (21/21) and mapped to siliconfly indices. The reference model's own notebook (`reference_model/example.ipynb`) contains a second sugar set (right-hemisphere example): 20/21 of those roots are present; both sets are left-lateralized in the v783 mapping. The benchmark list was used as the experiment set; provenance recorded in the dataset.
- **Readout**: MN9 (proboscis-extension motor neuron), root ID 720575940660219265 taken from the reference model's own annotations, mapped to siliconfly index 138947. Plus the 13 sugar-pathway interneurons that directly drive MN9 (computed from the connectome: MN9 has 227 direct in-neighbors, 13 of which are one hop from the sugar GRNs, with signed weight sum +94 — net excitatory at the bottleneck).
- **Drive class honesty**: the stimulus is deterministic per-step current at the GRNs — a rate-code approximation of Shiu's 200 Hz Poisson protocol, NOT a Poisson draw. Delivering true Poisson would require touching the kernel's RNG stream, which would break the bit-exactness guarantees of every existing mode. Documented in the dataset metadata and below.

## 2. Results (OBSERVED; 36 trials: 15 intact sugar sweep + 15 shuffled-control + 3 loom bookkeeping + 3 loom-with-MN9-watch)

### Intact connectome — MN9 dose-response (spikes per 1.2 s trial)

| sugar drive | MN9 spikes (3 seeds) | MN9 first spike (ms) | interneurons (sum) | GF spikes |
|---|---|---|---|---|
| 0.0 (no-stim) | 26, 23, 19 | 7, 30, 1 | 149, 153, 178 | 0, 0, 0 |
| 0.1 | 41, 47, 33 | 7, 17, 1 | 207, 299, 215 | 0, 0, 0 |
| 0.2 | 60, 51, 55 | 7, 14, 1 | 327, 362, 326 | 0, 0, 0 |
| 0.3 | 65, 65, 77 | 6, 12, 1 | 420, 427, 475 | 0, 0, 0 |
| 0.5 | 82, 87, 74 | 6, 11, 1 | 609, 620, 587 | 0, 0, 0 |

- Dose-response: baseline 19-26 → 74-87 spikes at the highest drive (~3.5x). [Corrected 2026-10-24: the original text said "monotonic in every seed"; seed 12347 is not monotonic at the top step (0.3 → 77, 0.5 → 74).]
- MN9 first-spike latency shortens with drive in 2/3 seeds (30→11 ms; 7 ms floor in the third).
- The 13-interneuron pathway tracks drive from the first level (149 → 620 total spikes).

### Shuffled connectome (0xC0FFEE) — flat null (OBSERVED)
MN9 fires exactly 14 spikes at every drive level (13 in one trial), first spike 58-77 ms, no dose dependence. The interneurons immediately downstream of the stimulated GRNs still follow the drive (201 → 705 — they receive it directly), but the signal does NOT propagate to the motor neuron. The sugar→MN9 pathway is wiring-specific, exactly as the escape circuit proved to be. This is the feeding-circuit replication of the Phase III/IV dissociation, now in both directions.

### Cross-circuit contamination checks
- Taste → escape: GF spikes = 0 in ALL 18 sugar trials across both arms. Taste input does not recruit escape.
- Escape → feeding: driving the entire left looming-detector population (162 neurons, strength 0.3) activates the escape pathway massively (GF 97-102 spikes) while MN9 fires 2-10 spikes per 600 ms window — below its own no-stim baseline rate. Looming does not recruit the feeding readout.
- Grooming/steering during sugar trials: DNg11 grooming rate stayed in the 0-3.9 Hz resting band [corrected 2026-10-24 from 0-3.8; max recorded 3.9]; DNa steering rates unchanged. No unrelated circuit activation.

## 3. Interpretation (categories kept separate)

OBSERVED: the dose-response table, the flat shuffled null, and the zero cross-circuit activation above.

MODEL PREDICTION: under the LIF + connectome assumptions, the reconstructed sugar→feeding-interneuron→MN9 pathway transduces gustatory drive into graded motor-neuron activation, is wiring-specific, and is independent of the escape circuit. MN9 carries baseline activity (~20 spikes/1.2 s) that sugar drive modulates upward ~3.5x; the net-excitatory bottleneck (+94 signed weight through 13 interneurons) is consistent with the graded transmission.

BIOLOGICAL EVIDENCE: Shiu et al. 2024 (Nature) validated feeding-initiation predictions from exactly this stimulation protocol against optogenetic split-GAL4 experiments; MN9 activation producing proboscis extension is the established behavioral readout in the literature. The model's graded MN9 response to sugar-GRN drive is consistent in kind with those published experiments. As in all prior phases: consistency is not independent prediction, and the drive here is deterministic rate-code, not the paper's Poisson protocol.

NOT CLAIMED: hunger, satisfaction, preference, enjoyment, consciousness, or nutrition. No measurable model response in this dataset corresponds to "enjoyed"; the claim would require an operational definition that does not exist, so it is not made.

## 4. Data-integrity incidents this phase (both caught and corrected)

1. A compile error in the new primitive was committed before the build check ran (shell chaining defect in MY procedure, not the code). Caught on the next build; fixed (cf0bf7e); GPUCHECK + simtest re-verified before any experiment ran.
2. The shuffled-arm run overwrote the intact-arm dataset file. Root cause: my script replaced the output file instead of merging by arm. Fixed (merge-by-arm); the intact arm was re-run and reproduced the recorded console values EXACTLY (every MN9 count, latency, interneuron sum, and GF zero) — the accidental deletion became a determinism cross-check. Loom-control trials were also re-run and reproduced identically (10/5/2 MN9; GF 97/101/102).

## 5. Trial-count reconciliation

An earlier summary miscounted. Ledger, counted from the datasets on disk (not memory):

| phase | arm | trials |
|---|---|---|
| II | intact sweep (seed 0x5EED1F1F) | 42 |
| II | shuffle 0xC0FFEE | 42 |
| III | shuffle 0xDEADBE0F baseline | 9 |
| III | ablation battery | 126 |
| IV | Mirror Image intact arm | 180 |
| IV | Mirror Image shuffle 0xBAADF00D | 45 |
| **total, Phases II-IV** | | **444** |
| V | Banana Peel (all arms + controls) | 36 |
| **total, all phases** | | **480** |

A reviewer's 435 = 84 + 126 + 225 was correct arithmetic on the numbers as reported; the 9-trial gap is the Phase III second-shuffle-seed baseline sweep (0xDEADBE0F), omitted from that summary, which also contained an addition error ("375"). The synapse count (54,492,922) was right because a computer did it.

## 6. Limitations
- Deterministic rate-code drive, not Poisson (see §1). A Poisson-faithful port requires kernel RNG-stream surgery with bit-exactness implications; feasible, not undertaken.
- MN9 identity comes from the reference model's annotation (one root ID); siliconfly's own cell-type table does not tag MN9. The mapping is root-ID-exact but single-neuron; Shiu's protocol may include additional MN9-class readouts.
- One shuffle seed for the feeding-circuit control (0xC0FFEE). Given Phase IV's finding that shuffle outcomes are a distribution, a second shuffle seed would strengthen the null. Cheap follow-up.
- Loom-control drive was delivered at the detector somas (extInput path), not through the loom input port; GF latency under this drive (~400 ms) differs from the port-driven 3-5 ms because tonic somatic current does not produce the synchronous onset volley the gap-junction path is calibrated for. Noted to keep the drive-class distinction honest.

## 7. Evidence
- Dataset: data/banana_peel.json (36 trials, per-trial raw records incl. per-step watch series)
- Figure: figs/banana_peel.png
- Code: run_banana.py, analyze_banana.py; kernel: specimen commits 1ab55ff, cf0bf7e
- GPUCHECK PASS + simtest PASS post-change; baseline restored (ablate_clear) after runs
- Feasibility doc (design phase): gustatory_feasibility.md

## 8. What "feeding the banana" means
The "banana" is the sugar-GRN drive in §2: deterministic current at the 21 identified gustatory receptor neurons for 1,000 ms, highest level run 0.5. [Corrected 2026-10-24: an earlier version of this section said 1.0 strength; no 1.0 trial exists in the dataset.] Measurable response: the dose-response table in §2. Nothing was eaten. No response corresponding to "enjoyed" exists, and none is claimed.

## Metadata correction (2026-10-24)
The merged dataset's top-level `shuffle_seed: 0` describes only the intact arm.
The 15 shuffled-arm trials used `0xC0FFEE` (12648430), independently confirmed
by the original bridge startup log. See [data/PROVENANCE.md](../data/PROVENANCE.md).
Raw measurements and dataset bytes are unchanged.
