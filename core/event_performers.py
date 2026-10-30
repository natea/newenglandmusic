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

import re

from core.artist_matching import normalize
from core.artist_names import SEPARATOR_RE, clean_name, is_placeholder, split_names
from core.models import Artist, Band, Event, EventPerformer

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


def performer_keys(event):
    return {(p.artist_id, p.band_id) for p in event.performers.all()}


def artist_parts(event):
    """
    the event's artists text as [(text, url or None)], separators and all, each name that's
    one of its performers carrying that act's page, for the listing (core/event.html)
    """
    text = str(event.artists or "")
    if not text or not event.pk:
        return []
    pages = {
        p.act.name_key: p.act.get_absolute_url()
        for p in event.performers.select_related("artist", "band")
    }
    if not pages:
        return []
    parts = []
    for piece in re.split(f"({SEPARATOR_RE.pattern})", text, flags=re.IGNORECASE):
        if piece:
            parts.append((piece, pages.get(normalize(clean_name(piece))) if piece.strip() else None))
    return parts


def rebake(event):
    """the event's stored listing, rendered again with its performers' links"""
    from core.utils_event_caching import bake_event_html

    Event.all_objects.filter(pk=event.pk).update(baked_html_template=bake_event_html(event))


def link_from_names(event, records=None):
    """
    replaces the event's links from names, re-rendering its listing when they change;
    returns the records it's linked to
    """
    records = names_to_records() if records is None else records
    named = performers_named(event, records)
    before = performer_keys(event)
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
    if performer_keys(event) != before:
        rebake(event)
    return linked


def remember_events(sender, instance, **kwargs):
    """before an artist or band is deleted, the events whose listings link to it"""
    instance._performed_event_ids = list(instance.performances.values_list("event_id", flat=True))


def rebake_remembered_events(sender, instance, **kwargs):
    """after the deletion, those listings without the dead link"""
    for event in Event.all_objects.filter(pk__in=getattr(instance, "_performed_event_ids", [])):
        rebake(event)


def connect_signals():
    """called from CoreConfig.ready: deleting an act, one or many, re-renders its events"""
    from django.db.models.signals import post_delete, pre_delete

    for model in (Artist, Band):
        pre_delete.connect(remember_events, sender=model, dispatch_uid=f"remember-events-{model.__name__}")
        post_delete.connect(rebake_remembered_events, sender=model, dispatch_uid=f"rebake-events-{model.__name__}")
