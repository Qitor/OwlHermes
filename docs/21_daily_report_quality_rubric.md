# R1-11: Daily Report Quality Rubric

## A. Product Mission

The daily report is an **AI risk intelligence briefing** — not a news digest, not a tool-call log, not a raw source summary, not a list of model/product announcements, and not a translation of English news.

It is produced for:

- **AI safety researchers** who need to know when capability thresholds, safety methods, or evaluation frameworks have changed.
- **AI governance/policy analysts** who need to know when regulatory actions, policy commitments, or industry self-regulation has substantively advanced.
- **Frontier lab safety teams** who need to know when competitors' or peers' safety actions have shifted the risk landscape.
- **Chinese-speaking researchers tracking frontier AI risk** who need concise, evidence-backed judgment in their working language.

The report should identify **public signals that change risk understanding**.

## B. What Counts as a Signal

A signal should involve at least one of:

- **Frontier model capability change** — new model, capability jump, threshold crossed
- **Evaluation or benchmark result** — new eval result, benchmark score, methodology change
- **New risk framework or policy threshold** — RSP update, preparedness framework, policy threshold shift
- **Deployment or misuse risk** — deployment incident, misuse pattern, misuse potential confirmed
- **Cyber/bio/autonomy/scheming/agentic risk** — evidence of specific risk category escalation
- **International governance or consensus shift** — treaty, summit outcome, regulatory action, enforcement
- **Lab safety commitment or RSP/preparedness/framework update** — new commitment, RSP change, framework revision
- **Incident, abuse pattern, vulnerability, or failure mode** — confirmed incident, abuse pattern, vulnerability disclosure
- **Credible expert claim that changes interpretation of risk** — new research result, expert testimony, policy analysis that shifts risk understanding

A signal is not just "something happened." It is "something happened that changes risk judgment."

## C. What Should Be Filtered Out

These should not automatically become signals:

- **Ordinary product announcements** — new product launch, feature update, pricing change without risk dimension
- **Marketing posts** — promotional content, partnership announcements without substantive risk content
- **Generic AI business news** — funding rounds, executive hires, market analysis without risk angle
- **Conference announcements without substantive new claims** — conference being held, agenda published, no new statement/commitment/framework
- **Podcast episodes without concrete new claims** — episode released but no transcript or verifiable claim extracted
- **arXiv papers that are merely adjacent but not risk-relevant** — AI-adjacent but no direct risk implication
- **Duplicated coverage of the same event** — same event reported by multiple sources without new angle
- **Weak speculation without evidence** — prediction or opinion without supporting evidence or credible source

These may be stored as raw items or candidates, but should not be promoted to signals unless risk relevance is established.

## D. Signal Evaluation Dimensions

For each candidate signal, evaluate:

| Dimension | Question |
|-----------|----------|
| **Novelty** | Is this genuinely new, or have we seen this before? |
| **Risk relevance** | Does this directly affect a risk judgment? |
| **Evidence quality** | Is there a primary source? Is the evidence verifiable? |
| **Source authority** | Is the source credible and authoritative for this claim? |
| **Severity** | How significant is the potential risk impact? (1-5) |
| **Confidence** | How confident are we in this signal? (1-5) |
| **Uncertainty** | What is unknown? What could change this judgment? |
| **Relation to prior signals** | Does this update, contradict, or extend a prior signal? |
| **Follow-up value** | Is there a specific next observation point? |

## E. Required Report Sections

The Chinese report must include:

1. **Non-production/local label** — when applicable, clearly label as non-production
2. **今日一句话总览** — one-sentence overview of the most significant risk landscape change
3. **Top Signals** — each signal must include:
   - 标题 (title)
   - 什么改变了 (what changed)
   - 为什么影响风险判断 (why it affects risk judgment)
   - 接下来关注什么 (what to watch next)
   - 证据 (evidence: primary source URL)
   - 置信度 (confidence: high/medium/low + reason)
4. **候选但未升级为信号的条目** — items that were considered but did not meet the signal bar, with brief reason
5. **来源覆盖与遗漏** — which sources were checked, what was missed
6. **证据和不确定性** — evidence gaps, unverified claims, low-confidence areas
7. **需要后续跟进的问题** — follow-up items, source reliability issues, suggested deep-dives
8. **Helper/Scrapling 使用情况** — only if helpers were actually used in this run

If no high-confidence signals were found, the report must explicitly state this and explain why (e.g., "今日扫描 X 个来源，未发现改变风险判断的高置信度信号" with supporting evidence from source checks).

## F. Style Guide

- **Write in Chinese** for serious research readers — not because of translation, but because the audience thinks in Chinese
- **Avoid hype** — no "revolutionary," "groundbreaking," "unprecedented" without evidence
- **Avoid AGI sensationalism** — do not amplify speculation about AGI timelines unless backed by credible evidence
- **Avoid filler** — every sentence should carry information
- **Prefer concise, evidence-backed judgment** — "X announced Y, which changes Z risk assessment because W" over "X made an interesting announcement"
- **Explain technical/policy context** when needed — do not assume the reader knows every acronym
- **Do not mechanically translate English titles** — restate in Chinese with added risk context
- **Do not list every raw item** — the report is not a dump of all discovered items
- **Do not include tool-call logs** — the reader cares about judgment, not process
- **0 high-confidence signals is acceptable** — no signal is itself information; do not inflate to fill the report
- **Prioritize quality over quantity** — 2 well-justified signals beat 10 loosely-justified ones
