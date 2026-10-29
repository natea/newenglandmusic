import datetime

from core.apple_music import (
    AppleMusicAuthError,
    AppleMusicBlocked,
    AppleMusicClient,
    AppleMusicError,
    credentials,
)
from core.artist_matching import normalize
from core.artist_names import event_artist_names
from core.job_runs import RecordedCommand
from core.models import AppleMusicArtistLink
from core.spotify_links import rebake_events_naming, upcoming_music_events
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

"""
links the artist names on upcoming events to their apple music artists, and each artist's
most popular song, for the listing's apple music play buttons.

run as:

python manage.py match_apple_music_artists [--names "Lake Street Dive,SHEBAD"] [--limit 50] [--dry-run]

each name is searched in the apple music catalog once, and linked only when exactly one
artist has the same name (ignoring case, accents, punctuation and a leading "the"); names
shared by several artists, or by none, are recorded so they aren't searched every day. a
matched artist's top song is the first of apple's top-songs view, which apple documents as
ordered by popularity. automatic results are searched again after RECHECK_AFTER; every
match's top song is refreshed then too, an editor's included, though an editor's artist is
never changed. links for names no upcoming event has named for FORGET_AFTER are deleted.

needs APPLE_MUSIC_TEAM_ID, APPLE_MUSIC_KEY_ID and APPLE_MUSIC_PRIVATE_KEY, and does nothing
without them. rejected credentials stop the run with an error; a long rate-limit block stops
it keeping what it found, for the next run to carry on.
"""

RECHECK_AFTER = datetime.timedelta(days=30)
FORGET_AFTER = datetime.timedelta(days=30)
Status = AppleMusicArtistLink.Status
Source = AppleMusicArtistLink.Source
COUNT_LABELS = {Status.MATCHED: "matched", Status.AMBIGUOUS: "ambiguous", Status.NOT_FOUND: "not found"}


def search_result(client, key, name):
    """(status, artist id) for a name, from the apple music catalog's search"""
    ids = {artist["id"] for artist in client.search_artists(name) if normalize(artist["name"]) == key}
    if len(ids) == 1:
        return Status.MATCHED, ids.pop()
    if ids:
        return Status.AMBIGUOUS, ""
    return Status.NOT_FOUND, ""


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
            self.stdout.write(
                "apple music isn't configured (APPLE_MUSIC_TEAM_ID, APPLE_MUSIC_KEY_ID, "
                "APPLE_MUSIC_PRIVATE_KEY): nothing to do"
            )
            return
        dry_run = options["dry_run"]
        now = timezone.now()

        events = [event for event in upcoming_music_events() if event.is_music_kind]
        # the first spelling seen of each name, for searching and the report
        names = {}
        for event in events:
            for name in event_artist_names(event):
                names.setdefault(normalize(name), name)

        links = {link.name_key: link for link in AppleMusicArtistLink.objects.all()}
        if not dry_run:
            AppleMusicArtistLink.objects.filter(name_key__in=names).update(last_seen_at=now)
        stale = [key for key, link in links.items() if key not in names and link.last_seen_at < now - FORGET_AFTER]
        changed = {key for key in stale if links[key].status == Status.MATCHED}
        if not dry_run:
            AppleMusicArtistLink.objects.filter(name_key__in=stale).delete()

        due = [key for key in sorted(names) if self.is_due(links.get(key), now)]
        if options["names"]:
            wanted = {normalize(name) for name in options["names"].split(",")}
            due = [key for key in due if key in wanted]
        limit = options["limit"]
        if limit is not None:
            due = due[:limit]

        client = AppleMusicClient(*found)
        counts = {"matched": 0, "ambiguous": 0, "not found": 0, "failed": 0}
        stopped = rejected = ""
        heading = "would record" if dry_run else "recorded"
        self.stdout.write(self.style.MIGRATE_HEADING(f"{heading} ({len(due)} names due)"))
        done = 0
        for key in due:
            done += 1
            link = links.get(key)
            try:
                if link is not None and link.source in (Source.EDITOR, Source.EVIDENCE):
                    # an editor's artist stands, as does one settled on last.fm evidence
                    # (resolve_artists_with_lastfm); only its top song is refreshed
                    status, artist_id = link.status, link.apple_artist_id
                else:
                    status, artist_id = search_result(client, key, names[key])
                song = client.top_song(artist_id) if status == Status.MATCHED and artist_id else None
            except AppleMusicAuthError as e:
                counts["failed"] += 1
                rejected = str(e)
                break
            except AppleMusicBlocked as e:
                counts["failed"] += 1
                stopped = str(e)
                self.stdout.write(self.style.WARNING(f"  {names[key]}: {e}; stopping this run"))
                break
            except AppleMusicError as e:
                counts["failed"] += 1
                self.stdout.write(self.style.WARNING(f"  {names[key]}: failed: {e}"))
                continue
            counts[COUNT_LABELS.get(status, "matched")] += 1
            song = song or {"song_id": "", "album_id": ""}
            self.stdout.write(
                f"  {names[key]}: {status}"
                + (f" -> {artist_id}" if artist_id else "")
                + (f", top song {song['song_id']} on album {song['album_id']}" if song["song_id"] else "")
            )
            self.record(key, status, artist_id, song, link, changed, now, dry_run)

        rebaked = 0 if dry_run else rebake_events_naming(changed, events)
        self.stdout.write(f"\ndeleted {len(stale)} links no upcoming event names; re-rendered {rebaked} events")
        self.job_summary = [
            ("searched", done),
            ("matched", counts["matched"]),
            ("ambiguous", counts["ambiguous"]),
            ("not found", counts["not found"]),
            ("deleted", len(stale)),
            ("failed", counts["failed"]),
            ("left for the next run", len(due) - done),
        ]
        if stopped:
            self.stdout.write(self.style.WARNING(f"stopped early, {len(due) - done} names left: {stopped}"))
        if rejected:
            raise CommandError(f"stopped: the apple music credentials were rejected. {rejected}")

    def record(self, key, status, artist_id, song, old, changed, now, dry_run):
        values = {
            "status": status,
            "apple_artist_id": artist_id,
            "top_song_id": song["song_id"],
            "top_album_id": song["album_id"],
            "checked_at": now,
            "last_seen_at": now,
        }
        if old is None or any(
            getattr(old, field) != values[field] for field in ("status", "apple_artist_id", "top_song_id", "top_album_id")
        ):
            changed.add(key)
        if not dry_run:
            # an editor's link stays the editor's
            values["source"] = old.source if old is not None else Source.AUTO
            AppleMusicArtistLink.objects.update_or_create(name_key=key, defaults=values)

    def is_due(self, link, now):
        if link is None:
            return True
        if link.checked_at >= now - RECHECK_AFTER:
            return False
        # an editor's link is refreshed only for its top song, and only when it's matched
        return link.source == Source.AUTO or link.status == Status.MATCHED
