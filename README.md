# Where LLM-assisted qualitative coding breaks

*[日本語の概要](README.ja.md)*

Seven failure modes in LLM-assisted coding of text corpora, each with a detection method and the cost of missing it.

They share one property: **a single coder plus human review cannot find any of them.** Not because the reviewer is careless — because each failure is internally consistent with the rules as written, so checking the output against the codebook returns "correct."

Every number below comes from one study: 163 coded units from Chinese-language government documents of a regulatory review process, September 2026, Claude as the production coder, ChatGPT (GPT-5.6) and Gemini (3.1 Pro) as independent validators. One corpus, one language, two vendors. Treat the numbers as existence proofs, not as effect sizes. Each section says how to test the claim in your own setting.

---

## 1. Your value domain is missing the cell for "no evidence either way"

A code's value set is usually written by imagining the cases you have seen. If your categories are `adopted / partially adopted / not adopted`, all three presuppose that the record says something. The common case in many corpora is that the record says nothing at all — the demand was raised, and the response simply does not mention it.

With no cell for that case, it collapses into the nearest one. Here it collapsed into `not adopted`, which is not a neutral error: it converts silence into refusal, and silence and refusal mean opposite things.

**Detection.** For each coded value, write the sentence "the evidence for this is ___." If one of your values completes that sentence with "there is none," it is doing double duty. Then count: of the units assigned the suspect value, how many have a quotable piece of evidence in the record?

**Observed.** Of 91 units coded `not adopted`, 22 (24%) carried explicit refusal with reasons. The other 69 (76%) had no trace of any kind. Adding `no traceable outcome` as a fourth value moved agreement with an independent coder from **8.7% to 90%**.

**Cost of missing it.** The original distribution supported the finding "76% of demands were rejected." That finding was an artifact of a missing cell.

---

## 2. A self-consistent error looks like a correct one

You write a codebook. You code with it. You review your own coding against it. Everything matches, because you are applying the same reading of the rules that produced the coding.

This is not a diligence problem and more review does not fix it. Human review detects *inconsistency* — the same situation coded two ways. It cannot detect a *consistent misreading*, because consistency is the only thing it checks.

**Detection.** One independent coder who did not help write the codebook, given the codebook text and nothing else. Not a second opinion from someone you briefed; the point is that they have access only to what a stranger would have.

**Observed.** Failure mode 1 sat undetected through the author's full review pass. It surfaced on the first run by a coder who had only the document.

**The distinction worth keeping.** A coder who helped write the manual encodes its *intent*. A coder holding only the text encodes its *letter*. The gap between them is the reproducibility of the manual — and reproducibility is a property of the letter, because the letter is all anyone else receives.

---

## 3. Running batches in one session changes the output

Split a corpus into batches and run them sequentially in one conversation, and the coder begins matching its own earlier output rather than re-reading the rules. Later batches show falling variance — which looks like the model settling down, and is in fact the model copying itself.

**Detection.** Re-run two batches from the middle and end of the sequence in fresh sessions. Compare each against a researcher-verified baseline. If the fresh runs disagree with the sequential runs, the sequential runs are path-dependent.

**Observed.** Same model, same prompt, same data; only the session differed.

| batch | same session | fresh session |
|---|---|---|
| 5 | 25% | 70% |
| 8 | **0%** | **100%** |

Batch 8 in the sequential run returned a single value 20 times out of 20, zero variance.

**Implication.** Per-batch isolation is a requirement, not a preference. This also means an API loop is methodologically *safer* than manual pasting, not just faster: each call is a cold context by construction.

---

## 4. Sampling audits cannot see systematic defects

A stratified sample is built to estimate a rate. Technical and consistency defects are not distributed at a rate — they cluster, in one file format, one document type, one node created late. Random sampling is at its weakest precisely where defects are concentrated.

**Detection.** Run both. A sampling audit for judgment, a full programmatic scan for anything a rule can express:

- does any quote contain a field delimiter from the source table?
- is every code in the permitted set?
- does any code have zero units?
- does every value that requires negative evidence have a non-empty evidence field?
- are there impossible combinations across dimensions?
- does any quote start mid-sentence or end without terminal punctuation?
- do any two units share an ID, or identical text?

**Observed.**

| defect class | total | found by 30% sample | found by full scan |
|---|---|---|---|
| quote contaminated by adjacent table cell | 14 | 6 | **14** |
| code misassignment | 5 | **0** | **5** |

**These two methods see different things and neither substitutes for the other.**

---

## 5. A quote that passed through the model is not a quote

If the coder outputs the quoted text, you cannot prove the text is verbatim. The model may silently normalize, truncate, or smooth it, and the failure is invisible — a plausible paraphrase reads exactly like an accurate quotation.

**The fix is structural, not a matter of instruction.** Have the model output only a *locator* — the first 15–30 characters, copied exactly. A program then finds that string in the source file and extracts the span by character offset, with the end determined by explicit boundary rules (terminal punctuation, enumeration markers, table delimiters).

The quoted text then never passes through the model at all. It is a slice of the file. Fidelity stops being a matter of trust.

**Detection, if you already have model-emitted quotes.** For each one, check that it occurs in the source file as an exact substring after whitespace normalization. Anything that fails is either a paraphrase or an extraction error; both matter.

**Observed.** Before the boundary rules, 23 of 163 evidence quotes contained a table field delimiter, meaning they had run past the cell boundary into an adjacent cell — in several cases absorbing the *next* unit's text into the current unit's evidence, which inflates how responsive the record appears. After: 0 of 163.

---

## 6. Validating a codebook on the data that shaped it measures nothing

Codebook revision is fitting. Each rule you add after seeing a disagreement fits the rule to that case. Measure agreement afterwards on the same material and you get a number that reflects the fitting, not the codebook.

Split the corpus before you begin: a development set you may revise against, and a held-out set you may not touch. Validate on the held-out set once.

**And then the hard part: do not fix what it reveals.** The moment you revise in response to held-out results, that set becomes a development set, and you have no clean sample left. The split is not recoverable — you cannot un-see it. Record the gaps as limitations and leave the criteria alone.

**Observed.** 100 units were used for revision; 63 were never touched. Measured on the 63:

| dimension | agreement |
|---|---|
| acknowledgement | 90.5% |
| category assignment | 71.4% |
| outcome | 69.8% |

Two of three fell below the thresholds set in advance. Three criterion gaps were identified. **None were fixed.** The version that followed changed no coding criterion; it added the limitations to the record.

**Why this is the right trade.** A codebook reported at 90% after fitting to all available data tells a reader nothing. One reported at 69.8% on data it never saw tells them exactly how much to trust it.

---

## 7. Two models agreeing is not intercoder reliability

The temptation is obvious: run two models from different vendors, compute kappa, report it as reliability. It does not hold, for three independent reasons.

**They are not independent.** Kappa assumes two independent judgments. Commercial LLMs share overwhelming training data and inherited conventions. Different vendors reduce the correlation; nothing available removes it.

**Agreement is not correctness.** Two models can converge on the same misreading of the same rule. A high agreement rate is then *bad* news, and harder to notice than disagreement would have been.

**Humans defer to consensus.** Where two models agree, a reviewer treats the item as settled and moves on. Shared blind spots become exactly the items nobody checks.

**What to do instead.** Name the roles by function, not by model count:

| role | definition |
|---|---|
| **production coder** | codes the full corpus; output enters the dataset |
| **auditor** | the researcher; stratified sample; final authority on every unit |
| **validation coder** | holds the codebook text only; output never enters the dataset, used solely to measure reproducibility |

Report two separate figures and never merge them: researcher-vs-production-coder disagreement (an audit statistic), and researcher-baseline-vs-validation-coder agreement (a reproducibility statistic). Neither is intercoder reliability. Say so.

**A related inference that does not hold.** "The researcher is accountable for the coding" does not entail "the researcher must code every unit by hand." The first is a claim about responsibility, the second about execution. Hand-coding at scale is not more consistent than a rule-following machine — it is less. Authority is exercised through the audit and the final judgment, not through volume.

---

## What this does not tell you

Everything above was observed in one corpus, one language, four document types, with models current in September 2026. The detection methods should transfer; the magnitudes should not be assumed to.

Three gaps were left open rather than papered over, and remain open: a criterion for distinguishing proposals from pure inquiries was applied inconsistently in both directions; the boundary between full and partial outcomes was never defined; and the basis for category assignment — by the action demanded, or by the topic discussed — was used consistently in practice but never written down. Each is visible in the section 6 numbers.

The thresholds used here were derived from this study's own audit data and are not transferable. Derive your own, from your own pilot, **before** you start — a threshold set after seeing results is not a threshold.
