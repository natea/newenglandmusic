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
from core.artist_names import SEPARATOR_RE, TITLE_PREFIX_RE, clean_name, event_artist_names, name_parts, occasion_prefix
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
    """
    the records the event names, in order, without repeats: its title's names first (where
    every source puts the headliner, leaving it out of the artists text), then its artists
    text's, as the spotify matching reads them (core/artist_names.event_artist_names)
    """
    named, seen = [], set()
    for name in event_artist_names(event):
        for record in records_named(name, records):
            if (type(record), record.pk) not in seen:
                seen.add((type(record), record.pk))
                named.append(record)
    return named


def records_named(name, records):
    """
    the records one name is: itself; a known name then words naming an occasion ("Built to
    Spill Fall 2026 Tour"); or, when it's neither, the acts of a duo billing ("Louis Cole &
    Chiquita Magic"), those that are records
    """
    key = normalize(name)
    record = records.get(key) or records.get(occasion_prefix(key, records) or "")
    if record is not None:
        return [record]
    return [records[normalize(part)] for part in name_parts(name) if normalize(part) in records]


def performer_keys(event):
    return {(p.artist_id, p.band_id) for p in event.performers.all()}


def link_piece(piece, pages):
    """
    [(text, url or None)] for one name-sized piece of text: the name it is, when that's a
    performer's ("Pixies (DJ Set)"), or the performer's name it starts with ("Built to Spill
    Fall 2026 Tour"), linked; the rest plain
    """
    clean = clean_name(piece)
    start = piece.find(clean) if clean else -1
    if start < 0:
        return [(piece, None)]
    key = normalize(clean)
    url = pages.get(key)
    if url is None:
        prefix = occasion_prefix(key, pages)
        words = clean.split(" ")
        for n in range(1, len(words)) if prefix else ():
            if normalize(" ".join(words[:n])) == prefix:
                clean, url = " ".join(words[:n]), pages[prefix]
                break
    if url is None:
        return duo_parts(piece, clean, start, pages)
    end = start + len(clean)
    return [part for part in ((piece[:start], None), (piece[start:end], url), (piece[end:], None)) if part[0]]


def duo_parts(piece, clean, start, pages):
    """"Louis Cole & Chiquita Magic": each act of a duo billing linked, when it's a performer"""
    parts, cursor = [], start
    for part in name_parts(clean):
        at = piece.find(part, cursor)
        url = pages.get(normalize(part))
        if at < 0 or url is None:
            continue
        parts += [(piece[cursor:at], None), (part, url)]
        cursor = at + len(part)
    if not parts:
        return [(piece, None)]
    return [part for part in [(piece[:start], None), *parts, (piece[cursor:], None)] if part[0]]


def linked_parts(text, pages, title=False):
    """text as [(text, url or None)], separators and all, each performer's name linked"""
    text, parts = str(text or ""), []
    if title:
        # "State Theatre Presents: The Ballroom Thieves": the presenter isn't a name
        prefix = TITLE_PREFIX_RE.match(text)
        if prefix:
            parts.append((prefix.group(0), None))
            text = text[prefix.end():]
    for piece in re.split(f"({SEPARATOR_RE.pattern})", text, flags=re.IGNORECASE):
        if not piece:
            continue
        if not piece.strip() or SEPARATOR_RE.fullmatch(piece):
            parts.append((piece, None))
        else:
            parts.extend(link_piece(piece, pages))
    return parts


def performer_pages(event):
    """{name_key: page} for the event's performers, or {} for an unsaved event"""
    if not event.pk:
        return {}
    return {p.act.name_key: p.act.get_absolute_url() for p in event.performers.select_related("artist", "band")}


def listing_parts(event):
    """
    (title parts, artists parts) for the event's listing (core/event.html), each performer's
    name linked to its page; ([], []) when it has no performers, and its listing is as before
    """
    pages = performer_pages(event)
    if not pages:
        return [], []
    return linked_parts(event.title, pages, title=True), linked_parts(event.artists, pages)


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
