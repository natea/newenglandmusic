"""
links an event to the artists and bands its Artists text names (EventPerformer), for
import_artists_from_events and fetch_events:

    records = names_to_records()          # once per run
    link_from_names(event, records)

a name links only when exactly one artist or band has it (compared normalized). the
event's links from names are replaced; an editor's are kept, and keep their order.
"""

from collections import defaultdict

from django.db import transaction

from core.artist_matching import normalize
from core.artist_names import is_placeholder, split_names
from core.models import Artist, Band, EventPerformer

Source = EventPerformer.Source


def names_to_records():
    """{name_key: the one artist or band with it}; a key two records share maps to none"""
    found = defaultdict(list)
    for model in (Artist, Band):
        for record in model.objects.only("pk", "name", "name_key"):
            found[record.name_key].append(record)
    return {key: records[0] for key, records in found.items() if len(records) == 1}


def performers_named(event, records):
    """the records the event's Artists text names, in order, without repeats"""
    named, seen = [], set()
    for name in split_names(event.artists):
        record = None if is_placeholder(name) else records.get(normalize(name))
        if record is not None and (type(record), record.pk) not in seen:
            seen.add((type(record), record.pk))
            named.append(record)
    return named


def link_from_names(event, records=None):
    """replaces the event's links from names; returns the records it's linked to"""
    records = names_to_records() if records is None else records
    named = performers_named(event, records)
    with transaction.atomic():
        event.performers.filter(source=Source.NAMES).delete()
        editors = {(p.artist_id, p.band_id) for p in event.performers.all()}
        linked = []
        for position, record in enumerate(named):
            key = (record.pk, None) if isinstance(record, Artist) else (None, record.pk)
            if key in editors:
                continue
            EventPerformer.objects.create(
                event=event, order=position, source=Source.NAMES,
                artist=record if isinstance(record, Artist) else None,
                band=record if isinstance(record, Band) else None,
            )
            linked.append(record)
    return linked
