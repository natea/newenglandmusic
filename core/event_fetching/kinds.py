"""
the kinds of event an imported event can be (see Event.Kind), and how they're described
to claude -- shared by ai extraction and batch labelling, so both label events the same way.
"""

KINDS = ["live_music", "dj_dance", "open_mic", "karaoke", "comedy", "other"]

KIND_DEFINITIONS = """\
Label each event with its kind:
- live_music: a performance by a band, solo artist, ensemble or tribute act, including \
concerts, album releases and music festivals.
- dj_dance: a DJ set or dance night built around DJs.
- open_mic: a music open mic, jam session or songwriter round.
- karaoke: karaoke.
- comedy: stand-up, improv or other comedy.
- other: anything else, e.g. trivia, games, classes, lessons, workshops, markets, \
screenings, talks, crafts, fitness, holiday or costume events.
A themed or holiday party (e.g. a Halloween party) is live_music or dj_dance only when \
a band, artist or DJ is named; otherwise it is other. A show whose title mentions a \
holiday but names a band (e.g. "Brass Against - Halloween Tour") is live_music."""
