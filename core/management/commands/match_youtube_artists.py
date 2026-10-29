import datetime

from core.artist_evidence import shares_name
from core.artist_matching import normalize
from core.artist_names import event_artist_names
from core.job_runs import RecordedCommand
from core.lastfm import LastFm, LastFmError, LastFmStopped
from core.lastfm import api_key as lastfm_key
from core.models import AppleMusicArtistLink, SpotifyArtistLink, YouTubeArtistLink
from core.music_ids import MusicBrainzBusy, MusicIds, MusicIdsError
from core.spotify_links import rebake_events_naming, upcoming_music_events
from core.youtube import YouTubeClient, YouTubeError, YouTubeKeyRejected, YouTubeQuotaExceeded, api_key
from core.youtube_links import confirming_video
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

"""
links the artist names on upcoming events to their own youtube channel or video, for the
listing's youtube play buttons.

run as:

python manage.py match_youtube_artists [--names "Dinosaur Jr."] [--limit 90] [--dry-run]

only names already matched on spotify or apple music are considered, and each is matched
only on evidence that ties youtube to that artist (see core/youtube_links.py):
1. wikidata or musicbrainz links its spotify or apple music id to a youtube channel, which
   exists. sources that disagree make it ambiguous;
2. else, the most-played track on its last.fm page is on youtube from the artist's own or
   topic channel, unless the page says several acts share the name. apple music's terms
   (developer program license 3.3.6 d) and spotify's don't allow their songs to be used to
   find music elsewhere, so neither is asked.
anything else is recorded as not found. matches are re-checked after RECHECK_AFTER, as
youtube's policies ask: a video that's gone or can't be embedded anymore loses its button.
links for names no upcoming event has named for FORGET_AFTER are deleted.

needs YOUTUBE_API_KEY, and does nothing without it. a song search costs 101 of the 10,000
free daily units, so --limit (default 90) caps the searches; a spent quota stops the run,
keeping what it found, for the next run to carry on.
"""

RECHECK_AFTER = datetime.timedelta(days=30)
FORGET_AFTER = datetime.timedelta(days=30)
DEFAULT_LIMIT = 90
Status = YouTubeArtistLink.Status
Evidence = YouTubeArtistLink.Evidence
Source = YouTubeArtistLink.Source


SONG_EVIDENCE = {Evidence.TOPIC_SONG, Evidence.CHANNEL_SONG}


def needs_rematch(link):
    """an automatic song match found with apple music's top song: matched again from scratch"""
    return link.source == Source.AUTO and link.evidence in SONG_EVIDENCE and link.song_source == "apple"


def id_linked_channel(wikidata, musicbrainz):
    """
    (channel id, evidence) from the channels wikidata and musicbrainz link to the artist,
    "ambiguous" when they disagree, or None when neither links any. a channel both give
    stands even when either also gives others (an artist's second channel, say)
    """
    both = wikidata & musicbrainz
    if len(both) == 1:
        return both.pop(), "wikidata"
    found = wikidata | musicbrainz
    if len(found) > 1:
        return "ambiguous"
    if found:
        channel = found.pop()
        return channel, "wikidata" if channel in wikidata else "musicbrainz"
    return None


class Command(RecordedCommand, BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--names", help="comma-separated artist names to match, if due")
        parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="make at most this many song searches")
        parser.add_argument(
            "--dry-run", action="store_true", help="report what would be recorded, but save nothing"
        )

    def handle(self, *args, **options):
        key = api_key()
        if not key:
            self.stdout.write("youtube isn't configured (YOUTUBE_API_KEY): nothing to do")
            return
        self.dry_run = options["dry_run"]
        self.now = timezone.now()
        self.youtube = YouTubeClient(key)
        self.music_ids = MusicIds()
        self.lastfm = LastFm(lastfm_key()) if lastfm_key() else None
        self.lastfm_stopped = False
        self.counts = {
            "considered": 0, "searched": 0, "matched by wikidata": 0, "matched by musicbrainz": 0,
            "matched by topic song": 0, "matched by channel song": 0, "ambiguous": 0, "not found": 0,
            "refreshed": 0, "deleted": 0, "failed": 0, "left for the next run": 0,
        }

        events = [event for event in upcoming_music_events() if event.is_music_kind]
        names = {}
        for event in events:
            for name in event_artist_names(event):
                names.setdefault(normalize(name), name)
        links = {link.name_key: link for link in YouTubeArtistLink.objects.all()}
        if not self.dry_run:
            YouTubeArtistLink.objects.filter(name_key__in=names).update(last_seen_at=self.now)
        stale = [k for k, link in links.items() if k not in names and link.last_seen_at < self.now - FORGET_AFTER]
        self.changed = {k for k in stale if links[k].status == Status.MATCHED}
        if not self.dry_run:
            YouTubeArtistLink.objects.filter(name_key__in=stale).delete()
        self.counts["deleted"] = len(stale)

        spotify = dict(
            SpotifyArtistLink.objects.filter(name_key__in=names, status=SpotifyArtistLink.Status.MATCHED)
            .exclude(spotify_artist_id="")
            .values_list("name_key", "spotify_artist_id")
        )
        apple = dict(
            AppleMusicArtistLink.objects.filter(name_key__in=names, status=AppleMusicArtistLink.Status.MATCHED)
            .exclude(apple_artist_id="")
            .values_list("name_key", "apple_artist_id")
        )
        considered = {k for k in names if k in spotify or k in apple or k in links}
        due = [k for k in sorted(considered) if self.is_due(links.get(k))]
        if options["names"]:
            wanted = {normalize(name) for name in options["names"].split(",")}
            due = [k for k in due if k in wanted]
        self.counts["considered"] = len(due)

        heading = "would record" if self.dry_run else "recorded"
        self.stdout.write(self.style.MIGRATE_HEADING(f"{heading} ({len(due)} names due)"))
        to_match = [k for k in due if not self.refresh(k, names[k], links.get(k))] if due else []
        stopped = self.quota_spent
        if to_match and not stopped:
            wikidata = self.wikidata_channels(
                [spotify[k] for k in to_match if k in spotify], [apple[k] for k in to_match if k in apple]
            )
            searches_left = options["limit"]
            for index, k in enumerate(to_match):
                try:
                    by_id = id_linked_channel(
                        wikidata.get(("spotify", spotify.get(k)), set()) | wikidata.get(("apple", apple.get(k)), set()),
                        self.musicbrainz_channels(spotify.get(k)),
                    )
                    if by_id == "ambiguous":
                        self.record(k, names[k], Status.AMBIGUOUS, "", "", "", links.get(k))
                        continue
                    if by_id and self.youtube.channels([by_id[0]]):
                        channel, evidence = by_id
                        self.record(k, names[k], Status.MATCHED, evidence, channel, "", links.get(k))
                        continue
                    # the song comes from last.fm, never apple music or spotify: their terms
                    # don't allow their data to be used to find music elsewhere
                    try:
                        song = self.lastfm_song(names[k])
                    except LastFmStopped:
                        # left as it is, for the next run
                        self.counts["left for the next run"] += 1
                        continue
                    except LastFmError as e:
                        self.counts["failed"] += 1
                        self.stdout.write(self.style.WARNING(f"  {names[k]}: last.fm failed: {e}"))
                        continue
                    if not song or not song["name"]:
                        self.record(k, names[k], Status.NOT_FOUND, "", "", "", links.get(k))
                        continue
                    if searches_left <= 0:
                        self.counts["left for the next run"] += len(to_match) - index
                        break
                    searches_left -= 1
                    self.counts["searched"] += 1
                    found = self.search_song(k, names[k], song)
                except YouTubeQuotaExceeded as e:
                    self.counts["failed"] += 1
                    self.counts["left for the next run"] += len(to_match) - index
                    stopped = str(e)
                    self.stdout.write(self.style.WARNING(f"  {names[k]}: {e}; stopping this run"))
                    break
                except YouTubeKeyRejected as e:
                    self.counts["failed"] += 1
                    self.counts["left for the next run"] += len(to_match) - index
                    self.rejected = str(e)
                    break
                except (YouTubeError, MusicIdsError) as e:
                    self.counts["failed"] += 1
                    self.stdout.write(self.style.WARNING(f"  {names[k]}: failed: {e}"))
                    continue
                if found:
                    evidence, video, channel = found
                    self.record(k, names[k], Status.MATCHED, evidence, channel, video, links.get(k))
                else:
                    self.record(k, names[k], Status.NOT_FOUND, "", "", "", links.get(k))

        rebaked = 0 if self.dry_run else rebake_events_naming(self.changed, events)
        self.stdout.write(
            f"\ndeleted {len(stale)} links no upcoming event names; re-rendered {rebaked} events; "
            f"used about {self.youtube.units} youtube quota units"
        )
        self.job_summary = list(self.counts.items())
        if stopped:
            self.stdout.write(self.style.WARNING(f"stopped early, {self.counts['left for the next run']} names left: {stopped}"))
        if self.rejected:
            raise CommandError(f"stopped: {self.rejected}")

    quota_spent = ""
    rejected = ""

    def is_due(self, link):
        if link is None:
            return True
        if needs_rematch(link):
            return True
        if link.source == Source.EDITOR and link.status != Status.MATCHED:
            # an editor's "no youtube", or a match that went away: theirs to fix
            return False
        return link.checked_at < self.now - RECHECK_AFTER

    def refresh(self, k, name, link):
        """
        re-check a due match's video or channel; whether that settled the name. an automatic
        link whose video or channel is gone is matched again from scratch
        """
        if link is None or link.status != Status.MATCHED or needs_rematch(link):
            return False
        try:
            if link.video_id:
                video = self.youtube.videos([link.video_id]).get(link.video_id)
                alive = bool(video and video["embeddable"])
            else:
                alive = link.channel_id in self.youtube.channels([link.channel_id])
        except YouTubeQuotaExceeded as e:
            self.counts["failed"] += 1
            self.quota_spent = str(e)
            return True
        except YouTubeKeyRejected as e:
            self.counts["failed"] += 1
            self.rejected = self.quota_spent = str(e)
            return True
        except YouTubeError as e:
            self.counts["failed"] += 1
            self.stdout.write(self.style.WARNING(f"  {name}: re-check failed: {e}"))
            return True
        if self.quota_spent:
            return True
        if alive:
            self.counts["refreshed"] += 1
            self.stdout.write(f"  {name}: still {link.video_id or link.channel_id}")
            if not self.dry_run:
                YouTubeArtistLink.objects.filter(pk=link.pk).update(checked_at=self.now)
            return True
        if link.source == Source.EDITOR:
            self.stdout.write(f"  {name}: the editor's {link.video_id or link.channel_id} is gone; no button until it's fixed")
            self.changed.add(k)
            if not self.dry_run:
                YouTubeArtistLink.objects.filter(pk=link.pk).update(status=Status.NOT_FOUND, checked_at=self.now)
            return True
        return False

    def wikidata_channels(self, spotify_ids, apple_ids):
        try:
            return self.music_ids.wikidata_channels(spotify_ids, apple_ids)
        except MusicIdsError as e:
            # musicbrainz and the song search can still find them
            self.counts["failed"] += 1
            self.stdout.write(self.style.WARNING(f"  wikidata failed: {e}"))
            return {}

    musicbrainz_busy = False

    def musicbrainz_channels(self, spotify_id):
        if not spotify_id or self.musicbrainz_busy:
            return set()
        try:
            return self.music_ids.musicbrainz_channels(spotify_id)
        except MusicBrainzBusy as e:
            # it's down or throttling us: the rest of the run goes without it, on wikidata
            # and the song search, rather than failing every name
            self.musicbrainz_busy = True
            self.counts["failed"] += 1
            self.stdout.write(self.style.WARNING(f"  {e}; carrying on without musicbrainz this run"))
            return set()

    def lastfm_song(self, name):
        """
        {"name", "album_name"}: the most-played track on the name's last.fm page, and its
        album; None when there's no page, no tracks, or the page says several acts share the
        name, since its tracks could then be another act's. raises LastFmError when last.fm
        can't be asked, so the name is left as it is rather than recorded as not found
        """
        if self.lastfm is None:
            return None
        if self.lastfm_stopped:
            raise LastFmStopped("last.fm stopped earlier this run")
        try:
            info = self.lastfm.artist_info(name)
            if not info or shares_name(info["bio"]):
                return None
            track = self.lastfm.top_track(name)
        except LastFmStopped as e:
            # the rest of the run makes no song searches, only id-linked matches
            self.lastfm_stopped = True
            self.stdout.write(self.style.WARNING(f"  {e}; carrying on without last.fm this run"))
            raise
        return {"name": track["name"], "album_name": track["album"]} if track else None

    def search_song(self, k, name, song):
        ids = self.youtube.search_videos(f"{name} {song['name']}")
        videos = self.youtube.videos(ids) if ids else {}
        return confirming_video(ids, videos, k, song["name"], song["album_name"])

    def record(self, k, name, status, evidence, channel, video, old):
        label = {
            Status.MATCHED: f"matched by {evidence.replace('-', ' ')}",
            Status.AMBIGUOUS: "ambiguous",
            Status.NOT_FOUND: "not found",
        }[status]
        self.counts[label] += 1
        self.stdout.write(f"  {name}: {label}" + (f" -> {video or channel}" if status == Status.MATCHED else ""))
        values = {
            "status": status, "evidence": evidence, "channel_id": channel, "video_id": video,
            "checked_at": self.now, "last_seen_at": self.now,
        }
        if old is None or any(getattr(old, f) != values[f] for f in ("status", "channel_id", "video_id")):
            if status == Status.MATCHED or (old is not None and old.status == Status.MATCHED):
                self.changed.add(k)
        if not self.dry_run:
            song_source = "lastfm" if evidence in SONG_EVIDENCE else ""
            YouTubeArtistLink.objects.update_or_create(
                name_key=k, defaults={**values, "source": Source.AUTO, "song_source": song_source}
            )
