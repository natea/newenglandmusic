from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.functions import Upper
from django.urls import reverse
from django.utils import timezone
from ordered_model.models import OrderedModel
from solo.models import SingletonModel
from tinymce import models as tinymce_models

from core.artist_matching import normalize
from core.artists import MBID_PATTERN, validate_bandcamp_url
from core.utils_event_caching import bake_event_html
from core.utils_static_page import refresh_searchable_static_page_bits


class EventManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_approved=True)


class Event(models.Model):
    # the ORDER of these i.e. objects first, then all_objects, matters........!!!!!
    # I initially thought that overriding a manager meant
    # that the admin classes would need to have a custom get_queryset,
    # but it's trickier than that... yes, you CAN define a get_queryset for the admin
    # of a class with a custom manager, but that will break in very subtle ways --
    # for example, the `list_editable` property in the EventAdmin class which lets
    # us edit the `order` field directly in the list view will NOT take into account
    # the get_queryset... actually, I don't know what it takes into account...
    # it just DOESN'T WORK AT ALL....!!! is there an update_queryset...?? I didn't find
    # anything in the docs...... anyway, the admin class does take into the account the
    # first encountered manager in the model class i.e. here, i.e. Event. more info:
    # https://docs.djangoproject.com/en/4.2/topics/db/managers/#default-managers
    # (note, again, that somehow all_objects was interfering with list_editable regardless...)
    # ~
    # I ALSO found out that get_object_or_404 also uses the first-found-manager
    # which, if you use all_objects as the first manager (wanting to fix the admin
    # list_editable problem), you'll then have to manually change all of the
    # get_object_or_404 calls to be passed the .objects manager... and never forget to do
    # that anywhere else... extremely annoying.
    # ~
    # SO, in the end I decided to use the narrowed-manager .objects as the first (in order)
    # manager in both Event and Static AND to use a truly baroque AllEventProxy class
    # (see below) that is then used in the admin for all events... this makes it possible
    # to not have a get_queryset in the admin AND list_editable works...
    objects = EventManager()
    all_objects = models.Manager()

    # for convenience aka this won't be exposed in the admin or elsewhere,
    # but is useful to be able to sort events in the order that they were created
    created_at = models.DateTimeField(auto_now_add=True)

    # title and artists are separate fields
    # when both are present, title will be not bold and artists will be bold
    # when either are present, whichever is present will be shown in bold
    title = models.CharField(max_length=255, null=True, blank=True)
    artists = models.CharField(max_length=255, null=True, blank=True)

    # user-submitted events will not be included in the event calendar until
    # they are approved by an admin.
    user_submitted = models.BooleanField(default=False)
    # `is_approved` is set to false in the submission view
    is_approved = models.BooleanField(default=True)
    user_submission_email = models.EmailField(
        null=True,
        blank=True,
    )

    venue = models.ForeignKey("Venue", on_delete=models.SET_NULL, null=True, blank=True)
    venue_override = tinymce_models.HTMLField(
        null=True,
        blank=True,
    )

    starttime = models.DateTimeField("Start time", null=True, db_index=True)
    starttime_override = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    # `description` will be presented as a tinymce field in the admin
    # because we're overriding `formfield_for_dbfield` in `EventAdmin`.
    # could use HMTLField from tinymce here too, probably, but stick with TextField
    # which we know works.
    description = models.TextField(null=True, blank=True)
    hyperlink = models.CharField(max_length=255, null=True, blank=True)

    # some events override the venue's age policy
    age_policy_override = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    age_policy_emoji_override = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    # same as `description` - this will be rich text
    preface = models.TextField(
        null=True,
        blank=True,
    )

    # optional hyperlink to tickets, separate from event.hyperlink value
    ticket_hyperlink = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    PRICE_RANGE = [
        ("🌀 free", "🌀 free"),
        ("🌀 notaflof", "🌀 notaflof"),
        ("$", "$"),
        ("$$", "$$ ($30+)"),
        ("$$$", "$$$ ($50+)"),
        ("$$$$", "$$$$ ($75+ lol y)"),
    ]
    price = models.CharField(
        max_length=255,
        choices=PRICE_RANGE,
        null=True,
        blank=True,
    )

    # will strikethrough most of the event information, except for the preface
    # for events fetched from venue websites -- see the fetch_events command
    class Source(models.TextChoices):
        ICAL = "ical", "iCal feed"
        JSON_LD = "json-ld", "Structured data (JSON-LD)"
        TICKETING = "ticketing", "Ticketing platform"
        AI = "ai", "AI extraction"
        TICKETMASTER = "ticketmaster", "Ticketmaster Discovery API"
        EVENTBRITE = "eventbrite", "Eventbrite API"

    source = models.CharField(
        max_length=16, choices=Source.choices, blank=True, default=""
    )
    source_url = models.URLField(max_length=1000, blank=True, default="")
    # identifies the event at its source, so re-fetching updates it instead of duplicating it
    external_id = models.CharField(max_length=255, unique=True, null=True, blank=True)

    # what kind of event an imported event is, so the review list can leave out the
    # trivia nights and comedy shows venues also list. blank means not labelled yet
    class Kind(models.TextChoices):
        LIVE_MUSIC = "live_music", "Live music"
        DJ_DANCE = "dj_dance", "DJ / dance night"
        OPEN_MIC = "open_mic", "Open mic"
        KARAOKE = "karaoke", "Karaoke"
        COMEDY = "comedy", "Comedy"
        OTHER = "other", "Other (not music)"

    MUSIC_KINDS = {Kind.LIVE_MUSIC, Kind.DJ_DANCE, Kind.OPEN_MIC}

    class KindSetBy(models.TextChoices):
        AI = "ai", "AI"
        ADMIN = "admin", "Admin"

    kind = models.CharField(max_length=16, choices=Kind.choices, blank=True, default="")
    # an admin's label is never overwritten by an import
    kind_set_by = models.CharField(
        max_length=8, choices=KindSetBy.choices, blank=True, default=""
    )

    @property
    def is_music_kind(self):
        """unlabelled events count as music, so nothing is hidden without a label"""
        return not self.kind or self.kind in self.MUSIC_KINDS

    is_cancelled = models.BooleanField(default=False)

    same_time_order_override = models.IntegerField(verbose_name="Order", default=0)

    baked_html_template = models.TextField(null=True, blank=True)

    @property
    def get_baked_html(self):
        if not self.baked_html_template:
            self.rebake_html()
        return self.baked_html_template

    def rebake_html(self):
        self.baked_html_template = bake_event_html(self)
        self.save()

    def save(self, *args, **kwargs):
        # save contents - just to be sure that object data is not 'floating'
        # and is actually accessible by template rendering
        super().save(*args, **kwargs)

        # rebake html, store/save it.
        # the below is 10000000000000000000000000000000% not kosher, but
        # I couldn't immediately figure out how to call super().save() a second time
        # without the whole orm freaking out and saying (when an object was being created)
        # that a duplicate id was being inserted.
        # ((probably because the object is considered as being-created and has no pk,
        # and the second super().save call also tries to initialize the pk...?))
        # https://stackoverflow.com/questions/31187359/django-save-method-needs-to-update-model-instance-twice#comment50382190_31187599
        baked_html_template = bake_event_html(self)
        # all_objects: Event.objects hides unapproved events, which would skip them here
        Event.all_objects.filter(pk=self.pk).update(baked_html_template=baked_html_template)

    # make age policy attribute that attempts to fetch its own
    # age policy by default, then tries to get venue's age policy if a venue is set,
    # and otherwise returns none
    @property
    def age_policy(self):
        if self.age_policy_override:
            return self.age_policy_override
        if self.venue:
            return self.venue.age_policy
        # should not happen
        return ""

    @property
    def age_policy_emoji(self):
        # venues have no age emoji, so only events that set one show one
        return self.age_policy_emoji_override or ""

    @property
    def title_and_artists(self):
        if self.title and self.artists:
            return f"{self.title}: {self.artists}"
        if self.title:
            return self.title
        if self.artists:
            return self.artists
        # should not happen
        return ""

    @property
    def venue_name_and_address(self):
        if self.venue_override:
            return self.venue_override
        if self.venue:
            # venues have no street address -- "name, city, state" is enough
            # for calendar apps and maps to find them
            if self.venue.location:
                return f"{self.venue.name}, {self.venue.location}"
            return self.venue.name
        # should not happen
        return ""

    @property
    def calendar_name(self):
        """the event name to show on calendars"""
        return f"{self.title_and_artists} [New England Music]"

    def __str__(self):
        return self.title_and_artists


# this ONLY exists for admin purposes and dealing with the problem
# of the list_editable field `order` not working (i.e. changes to it not being saved)
# when using a custom manager on the Event class (i.e. all_objects & objects)
# AND using a get_queryset on the admin class to be able to edit all objects......!
# because that combo doesn't work, we use a proxy model class (AllEventProxy)
# and configure the admin class to use that instead of the original Event class.
# see https://stackoverflow.com/a/54471299
class AllEventProxy(Event):
    class Meta:
        verbose_name = Event._meta.verbose_name
        verbose_name_plural = Event._meta.verbose_name_plural
        proxy = True

    # this will be the 'default manager' used in the Admin, and elsewhere
    objects = models.Manager()


class Venue(models.Model):
    """
    a venue, as listed in the "Northeastern US Music Venues" google sheet.
    fields mirror the sheet's columns -- see the sync_venues_from_gsheets command.
    """

    class Meta:
        # declare default ordering to be case insensitive name ascending
        # case insensitive trick: https://stackoverflow.com/a/52501004
        ordering = [Upper("name")]

    class Size(models.TextChoices):
        SMALL = "small", "Small (<100)"
        MEDIUM = "medium", "Medium (<500)"
        LARGE = "large", "Large (500+)"

    # values come from the sheet's "New Booking Types" tab
    class BookingType(models.TextChoices):
        SUBMIT_ARTIST = "submit_artist", "Submit an Artist"
        SUBMIT_SHOW = "submit_show", "Submit a Show"
        LOCALS_ONLY = "locals_only", "Locals Only"
        DART_THROW = "dart_throw", "Dart Throw"
        TOURING_ONLY = "touring_only", "Touring Acts Only"
        MUST_INCLUDE_LOCAL = "must_include_local", "Must Include a Local"
        UNKNOWN = "unknown", "Unknown"

    # the sheet's Venue_ID column (e.g. V0042). this is what the sync matches on,
    # as venue names (and even name + city + state) are not unique in the sheet
    sheet_id = models.CharField(max_length=32, unique=True, null=True, blank=True)

    # not from the sheet: set by the match_ticketmaster_venues command or by hand, so
    # the venue's events can be fetched from the ticketmaster discovery api
    ticketmaster_venue_id = models.CharField(
        max_length=64, null=True, blank=True, db_index=True, verbose_name="Ticketmaster venue ID"
    )
    # not from the sheet either: set by the match_eventbrite_organizers command or by hand,
    # for venues that sell their own shows on eventbrite
    eventbrite_organizer_id = models.CharField(
        max_length=64, null=True, blank=True, db_index=True, verbose_name="Eventbrite organizer ID"
    )

    name = models.CharField(max_length=255)

    class PlaceLookupStatus(models.TextChoices):
        CONFIDENT = "confident", "Confident match"
        REVIEW = "review", "Needs review"
        NOT_FOUND = "not_found", "Not found"
        # set by an admin for a venue with no single place, such as a festival across a
        # town: no lookup searches for it, and it keeps the sheet's coordinates
        SKIPPED = "skipped", "Not looked up (no single place)"

    # not from the sheet: the venue as found on google places by the lookup_venue_places
    # command. the sheet's coordinates are only town centres, so these are used instead
    # when the match is confident (see exact_location). google's terms allow storing only
    # the place id (indefinitely) and its coordinates (for 30 days): place_looked_up_at
    # is when the coordinates were last fetched, and lookup_venue_places refreshes or
    # deletes them before then
    place_lookup_status = models.CharField(
        max_length=16, choices=PlaceLookupStatus.choices, blank=True, default=""
    )
    place_looked_up_at = models.DateTimeField(null=True, blank=True)
    place_id = models.CharField(
        max_length=255, blank=True, default="", verbose_name="Google place ID"
    )
    place_latitude = models.FloatField(null=True, blank=True)
    place_longitude = models.FloatField(null=True, blank=True)
    # why a match needs review: the checks the top result failed ("name", "state",
    # "distance"), our own judgment, not google's content (lookup_venue_places)
    place_review_reasons = ArrayField(models.CharField(max_length=8), blank=True, default=list)
    # how far the reviewed place is from the sheet's coordinates; it comes from google's
    # coordinates, so it's deleted with them after 30 days
    place_distance_km = models.FloatField(null=True, blank=True)

    # the neighborhood the venue is in, from openstreetmap (lookup_venue_neighborhoods), or an
    # editor's; storable under odbl, credited in the footer
    class NeighborhoodSource(models.TextChoices):
        ADDRESS = "address", "OpenStreetMap address"
        OVERPASS = "overpass", "Nearest OpenStreetMap neighborhood"
        EDITOR = "editor", "Editor"
        NONE = "none", "None found"

    neighborhood = models.CharField(max_length=128, blank=True, default="")
    neighborhood_source = models.CharField(max_length=8, choices=NeighborhoodSource.choices, blank=True, default="")
    neighborhood_checked_at = models.DateTimeField(null=True, blank=True)

    state = models.CharField(max_length=2, blank=True, default="")
    city_town = models.CharField(max_length=255, blank=True, default="")
    county = models.CharField(max_length=255, blank=True, default="")
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    # None means unknown (blank or "Maybe?" in the sheet)
    is_active = models.BooleanField(null=True, blank=True)
    venue_type = models.CharField(max_length=255, blank=True, default="")
    size = models.CharField(max_length=16, choices=Size.choices, blank=True, default="")

    genre_notes = models.TextField(blank=True, default="")
    # from the semicolon-separated Venue_Genre_Search column, e.g. ["Funk", "Jazz"] or ["ALL"]
    genres = ArrayField(models.CharField(max_length=255), blank=True, default=list)
    niche_notes = models.TextField(blank=True, default="")

    open_booking = models.BooleanField(null=True, blank=True)
    booking_type = models.CharField(
        max_length=32, choices=BookingType.choices, blank=True, default=""
    )
    open_mic = models.BooleanField(null=True, blank=True)

    website = models.URLField(max_length=1000, blank=True, default="")
    booking_url = models.URLField(max_length=1000, blank=True, default="")
    booking_notes = models.TextField(blank=True, default="")

    age_policy = models.CharField(max_length=255, blank=True, default="")
    accessibility_notes = models.TextField(blank=True, default="")
    family_friendly = models.BooleanField(null=True, blank=True)
    lgbtq_friendly = models.BooleanField(null=True, blank=True, verbose_name="LGBTQ+")
    diverse = models.BooleanField(null=True, blank=True)

    safety_flag = models.CharField(max_length=255, blank=True, default="")
    safety_url = models.URLField(max_length=1000, blank=True, default="")
    safety_notes = models.TextField(blank=True, default="")

    def save(self, *args, **kwargs):
        # actually save data to db
        super().save(*args, **kwargs)
        # for all related events, refresh their baked html
        for event in self.event_set.all():
            event.rebake_html()

    @property
    def location(self):
        """"Boston, MA", or "Boston (West End), MA" when its neighborhood is known"""
        town = f"{self.city_town} ({self.neighborhood})" if self.city_town and self.neighborhood else self.city_town
        return ", ".join(part for part in [town, self.state] if part)

    @property
    def has_confident_place(self):
        return self.place_lookup_status == self.PlaceLookupStatus.CONFIDENT

    @property
    def exact_location(self):
        """
        (latitude, longitude): where the venue is on google places when that match is
        confident, otherwise the sheet's coordinates (often just the town's centre)
        """
        if self.has_confident_place and None not in (self.place_latitude, self.place_longitude):
            return self.place_latitude, self.place_longitude
        return self.latitude, self.longitude

    @property
    def exact_latitude(self):
        return self.exact_location[0]

    @property
    def exact_longitude(self):
        return self.exact_location[1]

    @property
    def google_maps_link(self):
        latitude, longitude = self.exact_location
        if latitude is None or longitude is None:
            return ""
        link = f"https://www.google.com/maps/search/?api=1&query={latitude},{longitude}"
        # google's maps urls open the place itself when given its id
        if self.has_confident_place and self.place_id:
            link += f"&query_place_id={self.place_id}"
        return link

    def __str__(self):
        return self.name


# what check_event_sources last found for a venue: how its events can be fetched.
# kept in its own table so saving a result never calls Venue.save(), which would
# re-render every one of the venue's events (see core/event_sources.py)
class VenueEventSource(models.Model):
    class BestSource(models.TextChoices):
        ICAL = "ical"
        JSON_LD = "json-ld"
        TICKETING = "ticketing"
        AI_EXTRACTION = "ai-extraction"
        NO_WEBSITE = "no-website"
        SOCIAL_ONLY = "social-only"
        ROBOTS_BLOCKED = "robots-blocked"
        DEAD_DOMAIN = "dead-domain"
        BOT_BLOCKED = "bot-blocked"
        UNREACHABLE = "unreachable"
        CHECK_FAILED = "check-failed"

    venue = models.OneToOneField(Venue, on_delete=models.CASCADE, related_name="event_source")
    checked_at = models.DateTimeField()
    url = models.URLField(max_length=1000, blank=True, default="")
    events_page = models.URLField(max_length=1000, blank=True, default="")
    best_source = models.CharField(max_length=32, choices=BestSource.choices)
    json_ld_events = models.PositiveIntegerField(default=0)
    ical_url = models.URLField(max_length=1000, blank=True, default="")
    ical_events = models.PositiveIntegerField(null=True, blank=True)
    platforms = ArrayField(models.CharField(max_length=64), blank=True, default=list)
    js_heavy = models.BooleanField(default=False)
    error = models.TextField(blank=True, default="")

    def __str__(self):
        return f"{self.venue}: {self.best_source}"


# a region, state or metro area from the sheet's geo-filters_json tab.
# venues aren't linked to areas: membership is worked out from these rules at
# query time (see core/geo_filters.py), so it never goes stale.
class GeoArea(models.Model):
    class Meta:
        ordering = ["sort_order"]
        constraints = [
            models.UniqueConstraint(fields=["kind", "slug"], name="geoarea_kind_slug")
        ]

    class Kind(models.TextChoices):
        REGION = "region"
        STATE = "state"
        METRO = "metro"

    kind = models.CharField(max_length=16, choices=Kind.choices)
    sheet_id = models.CharField(max_length=255, unique=True)
    label = models.CharField(max_length=255)
    # the sheet's STATE column, used to group metros under their state
    home_state = models.CharField(max_length=2, blank=True, default="")
    slug = models.SlugField(max_length=255)
    sort_order = models.PositiveIntegerField(default=0)

    # the matching rules, lowercased: a venue belongs to the area when its state
    # is in states and, if either list is set, its county or city is in it
    states = ArrayField(models.CharField(max_length=2), blank=True, default=list)
    counties = ArrayField(models.CharField(max_length=255), blank=True, default=list)
    cities = ArrayField(models.CharField(max_length=255), blank=True, default=list)

    @property
    def short_label(self):
        # "MA: Boston Metro Region" -> "Boston Metro Region", for metros grouped by state
        prefix = f"{self.home_state}: "
        return self.label[len(prefix) :] if self.label.startswith(prefix) else self.label

    def __str__(self):
        return self.label


# custom manager that returns only public StaticPages by default
# so that most code (except for the admin) will do the right thing
# and show public pages only
class StaticPageManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_public=True)


class StaticPage(models.Model):
    # the ORDER of all_objects and THEN objects matters.
    # see larger discussion in the Event model class to see why/how.
    objects = StaticPageManager()
    all_objects = models.Manager()

    is_public = models.BooleanField(default=True)

    url_path = models.CharField(max_length=255, unique=True)
    title = models.CharField(max_length=255)
    content = tinymce_models.HTMLField(null=True, blank=True)

    def get_absolute_url(self):
        return reverse("static_page", kwargs={"url_path": self.url_path})

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        refresh_searchable_static_page_bits(
            self,
            delete_only=not self.is_public,
        )


# StaticPage's content fields are too long to be indexed by postgres,
# which leads to super slow search (which we had to remove after the site launch).
# SearchableStaticPageBit stores overlapping split up 'bits' of content
# which can be indexed and will relate back to the original static page they came from
class SearchableStaticPageBit(models.Model):
    # models.CASCADE takes care of deleting the searchable bits when a static page is deleted
    static_page = models.ForeignKey(StaticPage, on_delete=models.CASCADE)
    content_text_extract = models.TextField()
    # see https://stackoverflow.com/a/70812950
    search_vector = SearchVectorField(editable=False, null=True)

    class Meta:
        # The search index pointing to our actual search field.
        indexes = [GinIndex(fields=["search_vector"])]


class DateMessage(models.Model):
    date = models.DateField("Date", null=True)
    message = tinymce_models.HTMLField(null=True, blank=True)

    def __str__(self):
        return str(self.date)


class EmailSubscriber(models.Model):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email


# 'IndexPageMessages' is a misnomer, as this
# singleton Pre + Post cal messages appear on EVERY
# archive page i.e. not only the / page, but also
# on every /2025-02/ ie archive page.
# TODO rename this to .... PrePostCalMessage? or CalMessages?
class IndexPageMessages(SingletonModel):
    pre_cal_msg = tinymce_models.HTMLField(
        "Pre calendar message", null=True, blank=True
    )
    post_cal_msg = tinymce_models.HTMLField(
        "Post calendar message", null=True, blank=True
    )

    def __str__(self):
        return "Index Page Messages"

    class Meta:
        verbose_name = "Index Page Messages"


class MenuItem(OrderedModel):
    name = models.CharField(max_length=255)
    url = models.CharField(
        max_length=255,
        help_text="This can either be a full url like https://... OR if it links to an internal page i.e. the greg page, you should enter /greg with the slash!",
    )
    show_in_header = models.BooleanField(default=False)
    show_in_footer = models.BooleanField(default=False)

    def __str__(self):
        return self.name


# one run of a pipeline command (see core/job_runs.py), kept so scheduled runs can be
# reviewed in the admin after the host's own logs are gone
class JobRun(models.Model):
    class Status(models.TextChoices):
        RUNNING = "running"
        SUCCEEDED = "succeeded"
        FAILED = "failed"

    command = models.CharField(max_length=64, db_index=True)
    # the options given, minus django's standard ones
    arguments = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(db_index=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.RUNNING)
    dry_run = models.BooleanField(default=False)
    # [[label, count], ...], in the order the command gave them
    summary = models.JSONField(default=list, blank=True)
    output = models.TextField(blank=True, default="")
    error = models.TextField(blank=True, default="")
    # [{"venue_id", "sheet_id", "name", "problems": [...]}], for venues that had problems
    problems = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.command} {timezone.localtime(self.started_at):%Y-%m-%d %H:%M}"


# how fetch_events last went for a venue: when, from which source, what it found and what
# failed. like VenueEventSource, kept apart so saving it never calls Venue.save()
class VenueFetchStatus(models.Model):
    venue = models.OneToOneField(Venue, on_delete=models.CASCADE, related_name="fetch_status")
    fetched_at = models.DateTimeField()
    # ical, json-ld, ticketing, ai, ticketmaster or eventbrite
    source = models.CharField(max_length=32)
    found = models.PositiveIntegerField(default=0)
    upcoming = models.PositiveIntegerField(default=0)
    problems = models.JSONField(default=list, blank=True)
    # the run it came from; kept when old runs are pruned
    job_run = models.ForeignKey(JobRun, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        verbose_name_plural = "venue fetch statuses"

    def __str__(self):
        return f"{self.venue}: {self.source}"


# which spotify artist an artist name on our events is, for the listing's play buttons
# (see match_spotify_artists). keyed by the normalized name, so one search serves every
# event naming it. spotify's terms forbid keeping a database of its content, so only the
# id is kept, and only while an upcoming event names the artist
class SpotifyArtistLink(models.Model):
    class Status(models.TextChoices):
        MATCHED = "matched", "Matched"
        AMBIGUOUS = "ambiguous", "Several artists with this name"
        NOT_FOUND = "not_found", "No artist with this name"
        NONE = "none", "No Spotify artist"

    class Source(models.TextChoices):
        AUTO = "auto", "Automatic"
        EDITOR = "editor", "Editor"
        # settled on last.fm and musicbrainz evidence (resolve_artists_with_lastfm): kept like an editor's
        EVIDENCE = "evidence", "Last.fm and MusicBrainz evidence"

    # core.artist_matching.normalize() of the name as our events write it
    name_key = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=16, choices=Status.choices)
    spotify_artist_id = models.CharField(max_length=64, blank=True, default="")
    # an editor's choice is never searched again or overwritten by the command
    source = models.CharField(max_length=8, choices=Source.choices, default=Source.AUTO)
    checked_at = models.DateTimeField()
    # the last run that found the name on an upcoming event; links unseen for 30 days go
    last_seen_at = models.DateTimeField()
    # when resolve_artists_with_lastfm last looked at the link: it looks at each once a month
    evidence_checked_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name_key


# which apple music artist an artist name on our events is, and that artist's most popular
# song, for the listing's apple music play buttons (see match_apple_music_artists). like
# SpotifyArtistLink, keyed by the normalized name and kept only while events name it
class AppleMusicArtistLink(models.Model):
    class Status(models.TextChoices):
        MATCHED = "matched", "Matched"
        AMBIGUOUS = "ambiguous", "Several artists with this name"
        NOT_FOUND = "not_found", "No artist with this name"
        NONE = "none", "No Apple Music artist"

    class Source(models.TextChoices):
        AUTO = "auto", "Automatic"
        EDITOR = "editor", "Editor"
        # settled on last.fm and musicbrainz evidence (resolve_artists_with_lastfm): kept like an editor's
        EVIDENCE = "evidence", "Last.fm and MusicBrainz evidence"

    # core.artist_matching.normalize() of the name as our events write it
    name_key = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=16, choices=Status.choices)
    apple_artist_id = models.CharField(max_length=32, blank=True, default="")
    # the first of the artist's top songs, and its album: what the player opens
    top_song_id = models.CharField(max_length=32, blank=True, default="")
    top_album_id = models.CharField(max_length=32, blank=True, default="")
    # an editor's artist is never searched for or overwritten; its top song still refreshes
    source = models.CharField(max_length=8, choices=Source.choices, default=Source.AUTO)
    checked_at = models.DateTimeField()
    # the last run that found the name on an upcoming event; links unseen for 30 days go
    last_seen_at = models.DateTimeField()
    # when resolve_artists_with_lastfm last looked at the link: it looks at each once a month
    evidence_checked_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name_key


class YouTubeArtistLink(models.Model):
    """
    the youtube channel, and if found the video, that is an artist's own, for the listing's
    youtube play buttons (match_youtube_artists). only ids are kept: youtube's policies allow
    storing api data for 30 days, so every match is re-checked within that
    """

    class Status(models.TextChoices):
        MATCHED = "matched", "Matched"
        AMBIGUOUS = "ambiguous", "Sources disagree"
        NOT_FOUND = "not_found", "Not confirmed"
        NONE = "none", "No YouTube"

    class Evidence(models.TextChoices):
        WIKIDATA = "wikidata", "Wikidata links it to the Spotify or Apple Music artist"
        MUSICBRAINZ = "musicbrainz", "MusicBrainz links it to the Spotify artist"
        TOPIC_SONG = "topic-song", "The top song on the artist's Topic channel"
        CHANNEL_SONG = "channel-song", "The top song on the artist's channel"
        EDITOR = "editor", "Editor"

    class Source(models.TextChoices):
        AUTO = "auto", "Automatic"
        EDITOR = "editor", "Editor"

    # core.artist_matching.normalize() of the name as our events write it
    name_key = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=16, choices=Status.choices)
    evidence = models.CharField(max_length=16, choices=Evidence.choices, blank=True, default="")
    channel_id = models.CharField(max_length=32, blank=True, default="")
    # blank for a channel matched by id alone: its button plays the channel's uploads
    video_id = models.CharField(max_length=16, blank=True, default="")
    # which service gave the song a song match was found with: "lastfm", or "apple" for the
    # matches made before apple music's terms ruled its songs out (these get matched again)
    song_source = models.CharField(max_length=8, blank=True, default="")
    # an editor's link is never re-matched or overwritten; it's still re-checked
    source = models.CharField(max_length=8, choices=Source.choices, default=Source.AUTO)
    checked_at = models.DateTimeField()
    # the last run that found the name on an upcoming event; links unseen for 30 days go
    last_seen_at = models.DateTimeField()

    class Meta:
        verbose_name = "YouTube artist link"

    def __str__(self):
        return self.name_key


class CensusPlace(models.Model):
    """
    a zip code area or a town from the census bureau's gazetteer files (public domain), for
    turning what a visitor types into a location (core/location.py). loaded once a year by
    load_census_gazetteer
    """

    class Kind(models.TextChoices):
        ZIP = "zip", "ZIP code area"
        TOWN = "town", "Town"

    kind = models.CharField(max_length=4, choices=Kind.choices)
    # the zip code, or the town's name without its census suffix ("Somerville", not
    # "Somerville city")
    name = models.CharField(max_length=128)
    # the two-letter state code; blank for zip code areas, which the files don't place
    state = models.CharField(max_length=2, blank=True, default="")
    # core.artist_matching.normalize() of the name, which is how lookups compare
    search_key = models.CharField(max_length=128)
    latitude = models.FloatField()
    longitude = models.FloatField()

    class Meta:
        indexes = [models.Index(fields=["kind", "search_key"])]

    def __str__(self):
        return f"{self.name}, {self.state}" if self.state else self.name


class MusicAct(models.Model):
    """
    what an Artist and a Band share: who the act is, where it's from, its own links, and
    what musicbrainz says about it (enrich_artists_from_musicbrainz). admin-only for now:
    nothing here is shown to visitors, and events still name artists by text.

    musicbrainz's core data (artists, their areas and dates, relationships and urls) is
    public domain (cc0); its genre tags are supplementary data under cc by-nc-sa, kept with
    credit. nothing from last.fm or bandcamp is stored (see core/artists.py).
    """

    class MusicBrainzStatus(models.TextChoices):
        MATCHED = "matched", "Matched"
        AMBIGUOUS = "ambiguous", "Several MusicBrainz artists with this name"
        NOT_FOUND = "not_found", "Not on MusicBrainz"
        # an editor set the id: enrichment looks it up, and never replaces it
        EDITOR = "editor", "Set by an editor"

    name = models.CharField(max_length=255)
    # core.artist_matching.normalize() of the name, to match members and musicbrainz names
    name_key = models.CharField(max_length=255, db_index=True, editable=False)
    # the import's Act_ID; blank for acts made as members or by musicbrainz
    act_id = models.CharField(max_length=32, unique=True, null=True, blank=True)
    city_town = models.CharField(max_length=100, blank=True, default="")
    state = models.CharField(max_length=2, blank=True, default="")
    website = models.URLField(blank=True, default="")
    bandcamp_url = models.URLField(blank=True, default="", validators=[validate_bandcamp_url])
    notes = models.TextField(blank=True, default="")
    # who set each field, {"website": "editor"}: "import", "musicbrainz" or "editor". the
    # import writes only a field that's unset or its own, and musicbrainz fills the website
    # and bandcamp link only when they're empty, so neither overwrites an editor's
    field_sources = models.JSONField(blank=True, default=dict)

    musicbrainz_id = models.CharField(
        max_length=36, unique=True, null=True, blank=True,
        validators=[RegexValidator(MBID_PATTERN, "a MusicBrainz id, like 4fbf1a3d-a649-4f8e-9ddf-347f6ba2d307")],
    )
    musicbrainz_status = models.CharField(max_length=16, choices=MusicBrainzStatus.choices, blank=True, default="")
    musicbrainz_checked_at = models.DateTimeField(null=True, blank=True)
    # musicbrainz's type ("Person", "Group", "Orchestra"…), country code, area and its
    # partial dates ("1994", "1994-05")
    mb_type = models.CharField(max_length=32, blank=True, default="")
    country = models.CharField(max_length=2, blank=True, default="")
    area = models.CharField(max_length=255, blank=True, default="")
    begin_date = models.CharField(max_length=10, blank=True, default="")
    end_date = models.CharField(max_length=10, blank=True, default="")
    genres = ArrayField(models.CharField(max_length=100), blank=True, default=list)
    wikidata_id = models.CharField(max_length=16, blank=True, default="")
    discogs_url = models.URLField(blank=True, default="")
    # musicbrainz's short note telling same-named acts apart ("Boston indie rock band"), cc0
    disambiguation = models.CharField(max_length=255, blank=True, default="")
    # the opening paragraph of the act's english wikipedia article, found through its
    # wikidata id: cc by-sa 4.0, kept word for word and credited wherever it's shown, with
    # a link to the article and the licence (see core/wikipedia.py)
    wikipedia_extract = models.TextField(blank=True, default="")
    wikipedia_url = models.URLField(max_length=500, blank=True, default="")
    wikipedia_revision = models.CharField(max_length=32, blank=True, default="")
    wikipedia_fetched_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ("name",)

    def save(self, *args, **kwargs):
        self.name_key = normalize(self.name)
        if self.act_id == "":
            self.act_id = None
        if self.musicbrainz_id == "":
            self.musicbrainz_id = None
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Artist(MusicAct):
    """a person or solo act, who may be a member of bands"""


class Band(MusicAct):
    """a group, whose members are Artists"""

    members = models.ManyToManyField(Artist, through="BandMembership", related_name="bands")


class BandMembership(models.Model):
    class Source(models.TextChoices):
        IMPORT = "import", "Import"
        MUSICBRAINZ = "musicbrainz", "MusicBrainz"
        EDITOR = "editor", "Editor"

    band = models.ForeignKey(Band, on_delete=models.CASCADE, related_name="memberships")
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name="memberships")
    # free text, such as "bass, vocals": musicbrainz's instrument names fit it
    role = models.CharField(max_length=255, blank=True, default="")
    begin_year = models.PositiveSmallIntegerField(null=True, blank=True)
    end_year = models.PositiveSmallIntegerField(null=True, blank=True)
    source = models.CharField(max_length=16, choices=Source.choices, default=Source.EDITOR)

    class Meta:
        ordering = ("band", "begin_year", "artist__name")
        # one person can hold two roles in a band, but not the same one twice
        constraints = [models.UniqueConstraint(fields=["band", "artist", "role"], name="unique_band_member_role")]

    @property
    def is_former(self):
        return self.end_year is not None

    def __str__(self):
        role = f" ({self.role})" if self.role else ""
        return f"{self.artist} in {self.band}{role}"
