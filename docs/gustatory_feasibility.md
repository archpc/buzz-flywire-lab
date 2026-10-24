# GUSTATORY INTERFACE — DESIGN & FEASIBILITY ASSESSMENT
Scope (19 Oct 2026): design and feasibility ONLY. No implementation, no feeding claims, no nutrition claims.

## 1. Gustatory receptor populations (identified)

Source: the Shiu-lineage benchmark suite (eonsystemspbc/fly-brain, code/benchmark.py, experiment `sugar`) defines the feeding-initiation stimulus used in the Shiu et al. 2024 Nature validation lineage: 21 sugar GRNs, stimulated at 200 Hz Poisson.

Verification performed (2026-10-19, parse of specimen/data via connectome.json manifest):
- All 21 FlyWire root IDs are PRESENT in siliconfly's bundled v783 connectome (21/21).
- Mapped siliconfly indices (first four): 69416, 98045, 123346, 124845 — role `other` (unannotated), predominantly side 1 (left).

## 2. Downstream wiring (exists in the graph)

- 1-hop targets of the 21 GRNs: 289 distinct neurons (top target weight 464 synapses).
- 2-hop reach: 2,337 neurons.
- The feeding circuit's wiring is present; nothing needs to be invented.

## 3. Readout problem (the honest gap)

- Shiu et al.'s feeding readout is MN9 (proboscis-extension motor neuron). MN9 is NOT tagged in siliconfly's cell-type string table (0/8,773 names match).
- The table DOES contain taste-peg GRN cell types (`claw_tpGRN`, `dorsal_tpGRN`) and 17 MN-family motor neuron types (MN10, MNx01, ...), so motor annotations exist in principle.
- Options to establish the readout, in order of preference:
  a. Import the MN9 root-ID set from the reference model repo (philshiu/Drosophila_brain_model) and map via rootId, exactly as done for the sugar GRNs. Highest fidelity, zero invention.
  b. Use the 2-hop downstream population response as a functional readout (feeding-pathway activation strength), clearly labeled as a proxy.
  c. Replicate Shiu's test protocol: sugar GRN stimulation → predicted downstream activation → compare against the paper's published optogenetic validation (the 91%-agreement experiment set includes feeding initiation).

## 4. What would constitute a measurable feeding-related response (MODEL PREDICTION criteria)

A response qualifies only if ALL of:
1. Stimulation is delivered AT the 21 sugar GRNs as Poisson drive (a real input port, not direct current injection into downstream neurons).
2. A pre-identified downstream readout population (option a: MN9) shows elevated activity correlated with stimulus rate.
3. Negative controls pass: shuffled connectome (does the feeding pathway survive random wiring? — this is exactly the class of question the escape circuit answered) and no-taste trials.
4. The result is labeled: OBSERVED in the model; consistent/not-consistent with Shiu's published biological validation; NOT nutrition.

## 5. Implementation sketch (not built)

Kernel: add `sugarDrive` input (0..1) routed to the 21 GRN indices (a `taste` inputKind alongside loom/sens), a `feed` readout group (MN9 indices once mapped), and a `taste_trial` primitive (settle → hold sugarDrive → post). Bridge: POST /taste. Estimated effort: ~1-2 kernel days + bridge/docs. Storage cost: negligible.

## 6. Explicit statement for the record

A simulated feeding response would demonstrate that the connectome's taste-to-feeding wiring, under the LIF model, transduces gustatory drive into downstream motor-neuron activation. It would NOT constitute nutrition, sustenance, or breakfast. The banana remains a supply-chain item, not a neuroscience item.
