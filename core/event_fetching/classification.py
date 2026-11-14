"""
labels imported events with what kind of event they are (see Event.Kind), so the review
list can leave out trivia nights, comedy shows, classes and the like that venues also
list. events from ai extraction are labelled in the extraction itself; events from feeds,
structured data, ticketing pages and ticketmaster are labelled here, in batches.
"""

import json

import anthropic

from core.event_fetching.ai_extraction import MODEL, MODELS_WITH_FALLBACKS
from core.event_fetching.kinds import KIND_DEFINITIONS, KINDS

BATCH_SIZE = 50
MAX_DESCRIPTION_LENGTH = 300
SYSTEM_PROMPT = f"""\
You label events at music venues in the northeastern US, for a calendar of live music.

{KIND_DEFINITIONS}

Use the title, the performers, the description and the venue. Return one label for \
every numbered event."""

LABELS_SCHEMA = {
    "type": "object",
    "properties": {
        "labels": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "kind": {"type": "string", "enum": KINDS},
                },
                "required": ["index", "kind"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["labels"],
    "additionalProperties": False,
}


def describe(index, item):
    lines = [f"[{index}] {item['title']}"]
    if item.get("artists"):
        lines.append(f"    performers: {item['artists']}")
    if item.get("venue"):
        lines.append(f"    venue: {item['venue']}")
    description = " ".join((item.get("description") or "").split())
    if description:
        lines.append(f"    description: {description[:MAX_DESCRIPTION_LENGTH]}")
    return "\n".join(lines)


def classify_batch(client, items, model):
    fallback_options = {}
    if model in MODELS_WITH_FALLBACKS:
        fallback_options = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}
    response = client.beta.messages.create(
        model=model,
        max_tokens=4000,
        **fallback_options,
        output_config={
            "effort": "low",
            "format": {"type": "json_schema", "schema": LABELS_SCHEMA},
        },
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": "\n".join(describe(i, item) for i, item in enumerate(items)),
            }
        ],
    )
    if response.stop_reason != "end_turn":
        raise ValueError(f"stopped with {response.stop_reason}")
    text = next(block.text for block in response.content if block.type == "text")
    kinds = [""] * len(items)
    for label in json.loads(text)["labels"]:
        index, kind = label.get("index"), label.get("kind")
        if isinstance(index, int) and 0 <= index < len(items) and kind in KINDS:
            kinds[index] = kind
    return kinds, response.usage


def classify(client, items, model=MODEL):
    """
    labels items -- dicts with title, artists, description and venue -- in batches.
    returns (a kind per item, "" when unlabelled; a list of error messages; input and
    output token totals). a failed batch leaves only its own items unlabelled
    """
    kinds, errors = [], []
    input_tokens = output_tokens = 0
    for start in range(0, len(items), BATCH_SIZE):
        batch = items[start : start + BATCH_SIZE]
        try:
            batch_kinds, usage = classify_batch(client, batch, model)
        except (anthropic.APIError, ValueError, KeyError, StopIteration) as e:
            errors.append(f"labelling events {start + 1}-{start + len(batch)} failed: {e}"[:200])
            kinds += [""] * len(batch)
            continue
        kinds += batch_kinds
        input_tokens += usage.input_tokens
        output_tokens += usage.output_tokens
    return kinds, errors, (input_tokens, output_tokens)
