# Signal Rubric

## What Counts as a Signal

A signal is not "something happened" — it is "something happened that changes risk judgment."

Every signal must answer three questions:

1. **What changed?** — Not "company X posted news" but "a parameter on a risk curve shifted"
2. **Why does it matter?** — Which risk (capability, alignment, governance, proliferation) became more or less likely?
3. **What should we watch next?** — What is the next observation point?

If a candidate cannot answer all three, it should remain a candidate, not be promoted to signal.

## Signal Categories

- Frontier model capability changes (new model, capability jump, threshold breakthrough)
- Evaluation or benchmark results (new eval, benchmark score, methodology change)
- New risk frameworks or policy thresholds (RSP update, preparedness framework, policy threshold shift)
- Deployment or misuse risks (deployment event, misuse pattern, misuse potential confirmation)
- Cyber/bio/autonomy/deception/agency risks (specific risk category escalation evidence)
- International governance or consensus shifts (treaty, summit outcome, regulatory action, enforcement)
- Lab safety commitments or RSP/preparedness/framework updates
- Events, misuse patterns, vulnerabilities, or failure modes
- Credible expert claims that change risk interpretation

## What Should NOT Automatically Become a Signal

- Generic product launch announcements (no safety/risk/governance dimension)
- Marketing posts, partnership announcements (no substantive risk content)
- Generic AI business news (funding, executive changes, market analysis, no risk angle)
- Conference announcements (no new statement/commitment/framework)
- Podcast episodes (no transcript or unconfirmed core claim)
- arXiv papers (AI-related but no direct risk implication)
- Repeated coverage of the same event (no new angle)
- Unsubstantiated weak speculation

## Signal vs Candidate

| Signal | Candidate |
|--------|-----------|
| Changes risk judgment | Interesting but no risk judgment change |
| Has evidence URL | May lack primary evidence |
| Answers all 3 questions | May not answer all 3 |
| Stored via `owl_risk_state(action="store_signal")` | Stored via `owl_risk_state(action="store_raw_item")` |

## Quality Rules

- **0 high-confidence signals is acceptable** — no new signals itself is information
- **Quality over quantity** — 2 well-reasoned signals > 10 weakly-reasoned ones
- **Avoid hype** — no "revolutionary", "breakthrough", "unprecedented" without evidence
- **Avoid AGI doomerism** — don't amplify AGI timeline speculation without credible evidence
- **Generic product launches are not signals** — unless clear risk dimension argued
