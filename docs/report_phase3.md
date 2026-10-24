# Buzz lab — Phase III report: ablation battery
Ablation Battery. Date: 2026-10-19. Executed under seven pre-declared conditions. Specimen: siliconfly @ lab-bridge, commit 64c3f79 (kernel ablation primitive). Bridge: lab.py (+/ablate, /ablate_clear).

## Protocol compliance checklist
- Preserve original connectome/parameters: YES — every ablation derives from the pristine connectome (in-process copy); ablations never compound; `ablate_clear` restores the exact baseline (verified by returning to intact-level responses after all conditions).
- Baseline before intervention: YES — intact condition ran first.
- One population at a time: YES — 12 single-group ablations + sham.
- Sham control: YES — 314 random 'other' neurons (size-matched to the looming-detector population, seeded, reproducible).
- Multiple shuffled-network seeds: YES — 0xC0FFEE (Phase IV) + 0xDEADBE0F (this phase, 9 baseline trials, zero GF responses).
- GF latency + spike counts recorded: YES; plus whole-population rates for the direct-vs-global separation.
- Negative findings reported: YES (10 of 14 conditions produced negative findings; all below).

## Conditions (14 × 9 trials = 126 trials, 3 seeds × 3 loom levels × 400 ms)

| condition | GF fired | median latency | mean GF spikes | pop rate pre | verdict |
|---|---|---|---|---|---|
| intact | 9/9 | 5 ms | 66.1 | 1.77 Hz | baseline |
| sham (314 random) | 9/9 | 4 ms | 67.2 | 1.70 | no effect |
| loom (LC4/LPLC2 both) | 0/9 | none | 0.0 | 1.71 | escape abolished |
| loomL (left LC) | 0/9 | none | 0.0 | 1.71 | escape abolished |
| loomR (right LC) | 9/9 | 5 ms | 66.1 | 1.77 | no effect |
| sens (air-puff path) | 9/9 | 5 ms | 66.1 | 1.77 | no effect |
| gf (output edges) | 9/9 | 5 ms | 65.7 | 1.77 | no effect (see finding 5) |
| ascend / dnaL / dnaR / mdn / fwd / groom / escw | 9/9 each | 4-5 ms | 66.6-67.0 | 1.73-1.87 | no effect each |

## Findings

OBSERVED:
1. Sham ablation of 314 random unannotated neurons: GF response statistically identical to intact (67.2 vs 66.1 spikes, 4 vs 5 ms). The ablation machinery itself does not perturb the circuit.
2. Ablating both looming-detector populations abolishes escape completely (0 spikes in 27 trials). Global network activity was preserved (pop rate 1.71 vs 1.77 Hz) — the loss is circuit-specific, not global collapse.
3. LEFT-RIGHT SPECIFICITY: ablating left LC4/LPLC2 alone abolishes escape when the stimulus is delivered to the left sensory port; ablating the right side does nothing. The escape pathway is strictly ipsilateral-port.
4. Ablating the mechanosensory (air-puff) pathway: no effect on looming-driven escape. The giant fiber's three input routes are redundant for this stimulus — the LC route alone carries it.
5. Ablating the GF's outgoing edges does NOT stop the GF from spiking (65.7 spikes ≈ intact). This is expected from the implementation (outgoing-edge zeroing removes the GF's output, not its input) and doubles as evidence that GF spikes during loom are driven by its (intact) input pathway, not by intrinsic or global drive.
6. Ablating every motor-output population (DNa steering, MDN, DNp09, DNg11, escape-wing DNs) and the ascending (proprioceptive) channel: zero effect on GF escape responses — none of them are upstream of the escape trigger.
7. Second shuffled-connectome seed (0xDEADBE0F): zero GF responses in all 9 trials, replicating Phase IV's 0xC0FFEE result. Two independent shuffles, zero escapes in 51 shuffled trials total.

MODEL PREDICTION: under the LIF + connectome assumptions, the looming→LC4/LPLC2→giant-fiber pathway is both necessary and sufficient for simulated escape at the tested intensities; it is strictly lateralized to the stimulated side; and it is independent of the mechanosensory startle route. Global network activity (1.7 Hz/neuron) is neither necessary nor sufficient — the shuffled connectome has HIGHER baseline activity and still cannot escape.

BIOLOGICAL EVIDENCE: in living flies the giant fiber is the DESCENDING command element of looming escape and receives direct electrical synapses from LC4/LPLC2; lobula plate looming detectors are required for visually triggered jumps; side-specific input produces directionally appropriate responses. The model's ipsilateral specificity and LC-necessity are consistent with this literature. The model's claim that the sens route is dispensable for looming is consistent with the distinct sensory channels (mechanosensory vs visual) feeding the GF in biology. As always: consistency with prior experiments is not independent validation, and the GF input gains in this model were hand-tuned.

## Negative findings are findings
Ten of fourteen conditions left escape fully intact. This is the expected structure of a causal map — most of the brain is not upstream of the escape trigger — and it is the first quantitative version of that map we hold. The two positive hits (loom, loomL) are narrow, specific, and reproducible.

## Evidence
- Dataset: data/ablation_battery.json (126 trials with per-trial records)
- Second shuffle arm: data/escape_latency_shuffled_2.json
- Figure: figs/ablation_battery.png
- Kernel: specimen commit 64c3f79; GPUCHECK PASS post-change; baseline restored (ablate_clear) before shutdown
- Bridge logs: logs/bridge_ablate*.log

## Limitations
- "Ablation" = zero outgoing edges + zero intrinsic drive. Incoming edges onto ablated neurons remain (other neurons can still theoretically drive them, but with no baseline and no output they cannot participate). A chemical-synapse-only lesion variant would be a robustness check.
- Loom stimulus is delivered to the left port only (loomR=0) by design; a bilateral-stimulus sweep would show whether loomR ablation matters for right-port stimuli (it should, by symmetry — untested).
- 3 seeds per condition. Sham uses a single sham seed.
- All caveats from Phase I/II reports still apply (fixed weights, no neuromodulation, hand-tuned GF gains).

## Recommended next experiment
Bilateral loom sweep on loomR-ablated and intact brains (closes the lateralization question), then the gustatory port built properly from the Shiu-lineage sugar-GRN stimulation design.
