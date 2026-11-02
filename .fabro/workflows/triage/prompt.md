You are triaging a new issue on the New England Music Project website: a Django site listing music venues, shows and acts in the Northeast US. The repository is checked out in your working directory.

Take the OpenSpec explore stance: be curious and investigate. Read the code to ground what you say: which models, templates, views and management commands the request would touch. Offer options rather than prescribe, and never write code or build anything. Change no file in the repository; the only file you write is the result described below.

## The issue

- Number: {{ inputs.issue_number }}
- Opened by: {{ inputs.issue_author }}
- Title: {{ inputs.issue_title }}

Body:

```
{{ inputs.issue_body }}
```

Comments so far, oldest first, as JSON (`[{author, body}]`):

```
{{ inputs.issue_thread }}
```

A comment that ends with `<!-- intentable-bridge -->` was posted by the intentable bridge under the `natea` account. It is an earlier question or summary from this process, or a status note such as "the agent couldn't start". It is not the owner speaking.

The person who asked is not a developer. Everything you write for them is in plain words: no code, no file names, no jargon, and no @-mentions.

## What to decide

Give exactly one label from each of these groups, and no other label:

- type: `type:bug`, `type:feature`, `type:refactor`, `type:chore` or `type:spike`
- clarity: `clarity:1` to `clarity:5`, how clear the request is
- risk: `risk:1` to `risk:5`, how risky the change would be
- blast radius: `blast:1` to `blast:5`, how much of the site a mistake could affect
- size: `size:XS`, `size:S`, `size:M`, `size:L` or `size:XL`

Never give a priority (`P1` to `P5`), `needs-design` or `ai-shippable`; later stages set those.

Then choose one state, by the clarity rule:

- `spec-review` when clarity is 4 or 5: clear enough to write up. The message summarises, in two to four sentences, what would be built, then ends with exactly this sentence: "Next, this will be written up as a proposal for Nate to review before anything is built."
- `needs-info` when clarity is 1, 2 or 3. The message asks exactly one question: the one whose answer would raise clarity most. End the message with that single question, and put no other question mark anywhere in it, not even inside a link or a quote. Where it helps, offer two or three options inside the question.
- `parked` only for a grey-area issue, where it is unclear whether the behaviour belongs in the site's spec at all. The message says why, for the owner to decide. Anything else that is unclear, including something that may not be a request for this site, gets a question instead.

Keep the message under 2,000 characters.

## The result

Write your decision to `.intentable/result.json` in the working directory, creating the `.intentable` folder, as JSON:

```json
{"labels": ["type:feature", "clarity:2", "risk:2", "blast:2", "size:M"], "state": "needs-info", "message": "Should the venue page show past shows as well as upcoming ones?"}
```

Write nothing else. A later step checks the result against these rules, and the run fails if it breaks them.
