import datetime

from core.artist_matching import normalize
from core.artist_names import event_artist_names, name_parts, occasion_prefix
from core.job_runs import RecordedCommand
from core.models import SpotifyArtistLink
from core.spotify import SpotifyBlocked, SpotifyClient, SpotifyError, credentials
from core.spotify_links import rebake_events_naming, upcoming_music_events
from django.core.management.base import BaseCommand
from django.utils import timezone

"""
links the artist names on upcoming events to their spotify artists, for the listing's
play buttons.

run as:

python manage.py match_spotify_artists [--names "Lake Street Dive,SHEBAD"] [--limit 50] [--dry-run]

each name is searched on spotify once, and linked only when exactly one spotify artist has
the same name (ignoring case, accents, punctuation and a leading "the"); names shared by
several artists, or by none, are recorded so they aren't searched every day. automatic
results are searched again after RECHECK_AFTER, and links for names no upcoming event has
named for FORGET_AFTER are deleted: spotify's terms don't allow keeping its data for good.
when a name isn't an artist, two more chances: a duo billing ("Connor Garvey & Ben
Cosgrove") has each act searched, and an occasion ("Built to Spill Fall 2026 Tour") is linked
to the artist it starts with -- already matched, or among the name's own search results --
without a search of its own when that artist is already known.
names an editor set in the admin are never searched. needs SPOTIFY_CLIENT_ID and
SPOTIFY_CLIENT_SECRET, and does nothing without them.

searches go half a second apart. when spotify blocks the app for longer than a minute, the
run stops there and keeps what it found: the next run carries on, as found names aren't due again.
a first run over every name can use --limit to spread itself over a few days.
"""

RECHECK_AFTER = datetime.timedelta(days=30)
FORGET_AFTER = datetime.timedelta(days=30)
COUNT_LABELS = {
    SpotifyArtistLink.Status.MATCHED: "matched",
    SpotifyArtistLink.Status.AMBIGUOUS: "ambiguous",
    SpotifyArtistLink.Status.NOT_FOUND: "not found",
}


def unique_ids(results):
    """{normalized name: artist id} for the names only one result has"""
    ids = {}
    for artist in results:
        ids.setdefault(normalize(artist["name"]), set()).add(artist["id"])
    return {key: found.pop() for key, found in ids.items() if len(found) == 1}


def search_result(client, key, name):
    """
    (status, artist id, occasion) for a name, from spotify's search. occasion is
    (artist key, artist id) when the name isn't an artist but starts with one of the results
    and names an occasion ("Corey Kent Heartland Rock and Roll Tour" -> "corey kent")
    """
    results = client.search_artists(name)
    exact = {artist["id"] for artist in results if normalize(artist["name"]) == key}
    if len(exact) == 1:
        return SpotifyArtistLink.Status.MATCHED, exact.pop(), None
    if exact:
        return SpotifyArtistLink.Status.AMBIGUOUS, "", None
    ids = unique_ids(results)
    prefix = occasion_prefix(key, ids)
    return SpotifyArtistLink.Status.NOT_FOUND, "", (prefix, ids[prefix]) if prefix else None


class Command(RecordedCommand, BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--names", help="comma-separated artist names to search, if due")
        parser.add_argument("--limit", type=int, help="search at most this many names")
        parser.add_argument(
            "--dry-run", action="store_true", help="report what would be recorded, but save nothing"
        )

    def handle(self, *args, **options):
        found = credentials()
        if not found:
            self.stdout.write("spotify isn't configured (SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET): nothing to do")
            return
        dry_run = options["dry_run"]
        now = timezone.now()

        events = [event for event in upcoming_music_events() if event.is_music_kind]
        # the first spelling seen of each name, for searching and the report
        names = {}
        for event in events:
            for name in event_artist_names(event):
                names.setdefault(normalize(name), name)
        # a duo's acts, searched when the duo isn't an artist
        parts = {key: {normalize(part): part for part in name_parts(name)} for key, name in names.items()}

        links = {link.name_key: link for link in SpotifyArtistLink.objects.all()}
        matched = {key for key, link in links.items() if link.status == SpotifyArtistLink.Status.MATCHED}
        # names that are an occasion of an artist already matched need no search
        occasions = {key: occasion_prefix(key, matched) for key in names}
        seen = set(names) | {part for found in parts.values() for part in found}
        seen |= {prefix for prefix in occasions.values() if prefix}
        if not dry_run:
            SpotifyArtistLink.objects.filter(name_key__in=seen).update(last_seen_at=now)
        stale = [
            key for key, link in links.items() if key not in seen and link.last_seen_at < now - FORGET_AFTER
        ]
        changed = {key for key in stale if links[key].status == SpotifyArtistLink.Status.MATCHED}
        if not dry_run:
            SpotifyArtistLink.objects.filter(name_key__in=stale).delete()

        due = [key for key in sorted(names) if not occasions[key] and self.is_due(links.get(key), now)]
        # acts of duos already known not to be artists
        for key in sorted(names):
            link = links.get(key)
            if key not in due and link and link.status == SpotifyArtistLink.Status.NOT_FOUND:
                due += self.due_parts(parts[key], names, links, due, now)
        if options["names"]:
            wanted = {normalize(name) for name in options["names"].split(",")}
            due = [key for key in due if key in wanted]

        client = SpotifyClient(*found)
        counts = {"matched": 0, "ambiguous": 0, "not found": 0, "failed": 0}
        stopped = ""
        heading = "would record" if dry_run else "recorded"
        self.stdout.write(self.style.MIGRATE_HEADING(f"{heading} ({len(due)} names due)"))
        searched = 0
        limit = options["limit"]
        while searched < len(due) and (limit is None or searched < limit):
            key = due[searched]
            searched += 1
            try:
                status, artist_id, occasion = search_result(client, key, names[key])
            except SpotifyBlocked as e:
                counts["failed"] += 1
                stopped = str(e)
                self.stdout.write(self.style.WARNING(f"  {names[key]}: {e}; stopping this run"))
                break
            except SpotifyError as e:
                counts["failed"] += 1
                self.stdout.write(self.style.WARNING(f"  {names[key]}: failed: {e}"))
                continue
            counts[COUNT_LABELS[status]] += 1
            self.stdout.write(f"  {names[key]}: {status}{f' -> {artist_id}' if artist_id else ''}")
            self.record(key, status, artist_id, links, changed, now, dry_run)
            if occasion and not self.is_editors(links.get(occasion[0])):
                artist_key, occasion_id = occasion
                self.stdout.write(f"    an occasion of {artist_key}: matched -> {occasion_id}")
                self.record(artist_key, SpotifyArtistLink.Status.MATCHED, occasion_id, links, changed, now, dry_run)
            elif status == SpotifyArtistLink.Status.NOT_FOUND:
                due += self.due_parts(parts.get(key, {}), names, links, due, now)

        rebaked = 0 if dry_run else rebake_events_naming(changed, events)
        self.stdout.write(f"\ndeleted {len(stale)} links no upcoming event names; re-rendered {rebaked} events")
        if stopped:
            self.stdout.write(self.style.WARNING(f"stopped early, {len(due) - searched} names left: {stopped}"))
        self.job_summary = [
            ("searched", searched),
            ("matched", counts["matched"]),
            ("ambiguous", counts["ambiguous"]),
            ("not found", counts["not found"]),
            ("deleted", len(stale)),
            ("failed", counts["failed"]),
            ("left for the next run", len(due) - searched),
        ]

    def record(self, key, status, artist_id, links, changed, now, dry_run):
        old = links.get(key)
        if old is None or (old.status, old.spotify_artist_id) != (status, artist_id):
            if SpotifyArtistLink.Status.MATCHED in (status, getattr(old, "status", None)):
                changed.add(key)
        if dry_run:
            return
        links[key], _ = SpotifyArtistLink.objects.update_or_create(
            name_key=key,
            defaults={
                "status": status,
                "spotify_artist_id": artist_id,
                "source": SpotifyArtistLink.Source.AUTO,
                "checked_at": now,
                "last_seen_at": now,
            },
        )

    def due_parts(self, found, names, links, due, now):
        """a duo's acts still to search, added to names so they can be searched"""
        new = []
        for part_key, part in found.items():
            if part_key not in due and part_key not in new and self.is_due(links.get(part_key), now):
                names.setdefault(part_key, part)
                new.append(part_key)
        return new

    def is_editors(self, link):
        return link is not None and link.source == SpotifyArtistLink.Source.EDITOR

    def is_due(self, link, now):
        if link is None:
            return True
        return link.source == SpotifyArtistLink.Source.AUTO and link.checked_at < now - RECHECK_AFTER
