"""
checks the event labelling against the real model -- run by hand, not part of the test
suite (it costs a cent or so and needs ANTHROPIC_API_KEY):

venv/bin/python core/tests/evals/music_filter_eval.py [--sample 30]

it labels the examples from the event-music-filter spec, whose expected kinds are known,
and prints any mismatches; then it labels a sample of real upcoming imported events and
prints them for a person to eyeball.
"""

import argparse
import os
import sys

import django

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nycnoise.settings.dev")
django.setup()

import anthropic  # noqa: E402
from core.event_fetching.classification import classify  # noqa: E402
from core.models import Event  # noqa: E402
from django.utils import timezone  # noqa: E402

MUSIC = {"live_music", "dj_dance", "open_mic"}

# (title, performers, expected kind -- or "not music" when any non-music kind will do)
EXAMPLES = [
    ("A Very Jerry Halloween with Rose Alley (Jerry Garcia Band Tribute)", "", "live_music"),
    ("Brass Against - Halloween Tour", "", "live_music"),
    ("Halloween Costume Party", "", "not music"),
    ("Trivia Night", "", "not music"),
    ("Nerd Night", "", "not music"),
    ("Clown Class", "", "not music"),
    ("Print Club", "", "not music"),
    ("Sunday Night Karaoke", "", "karaoke"),
    ("80s Dance Party with DJ Shakes", "", "dj_dance"),
    ("Tuesday Songwriter Open Mic", "", "open_mic"),
    ("IMPROV COMEDY: an evening of laughs", "", "comedy"),
    ("Breakfast with Santa", "", "not music"),
    ("Fiber Artists Meetup", "", "not music"),
    ("Swing Dance Lessons", "", "not music"),
    ("Samantha Fish", "Sgt. Splendor", "live_music"),
    ("World Class Music Live Presents Rumbo Tumba", "", "live_music"),
]


def matches(expected, kind):
    return kind not in MUSIC if expected == "not music" else kind == expected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=30)
    args = parser.parse_args()

    client = anthropic.Anthropic()
    items = [{"title": t, "artists": a, "description": "", "venue": ""} for t, a, _ in EXAMPLES]
    kinds, errors, tokens = classify(client, items)
    misses = [(t, e, k) for (t, _, e), k in zip(EXAMPLES, kinds) if not matches(e, k)]
    print(f"spec examples: {len(EXAMPLES) - len(misses)}/{len(EXAMPLES)} as expected")
    for title, expected, kind in misses:
        print(f"  MISMATCH {title!r}: expected {expected}, got {kind or 'unlabelled'}")

    events = list(
        Event.all_objects.filter(starttime__gte=timezone.now())
        .exclude(source="")
        .select_related("venue")
        .order_by("?")[: args.sample]
    )
    items = [
        {
            "title": e.title,
            "artists": e.artists,
            "description": e.description or "",
            "venue": f"{e.venue.name} ({e.venue.location})" if e.venue else "",
        }
        for e in events
    ]
    sample_kinds, sample_errors, sample_tokens = classify(client, items)
    print(f"\nsample of {len(events)} real events:")
    for event, kind in sorted(zip(events, sample_kinds), key=lambda pair: pair[1]):
        print(f"  {kind or 'unlabelled':11} {event.title[:70]}  [{event.source}]")

    for error in errors + sample_errors:
        print(f"error: {error}")
    print(f"\ntokens: {tokens[0] + sample_tokens[0]} input / {tokens[1] + sample_tokens[1]} output")


if __name__ == "__main__":
    main()
