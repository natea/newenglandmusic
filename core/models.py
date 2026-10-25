from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.db.models.functions import Upper
from django.urls import reverse
from ordered_model.models import OrderedModel
from solo.models import SingletonModel
from tinymce import models as tinymce_models

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

    name = models.CharField(max_length=255)

    class PlaceLookupStatus(models.TextChoices):
        CONFIDENT = "confident", "Confident match"
        REVIEW = "review", "Needs review"
        NOT_FOUND = "not_found", "Not found"

    # not from the sheet: the venue as found on google places by the lookup_venue_places
    # command. the sheet's coordinates are only town centres, so these are used instead
    # when the match is confident (see exact_location)
    place_lookup_status = models.CharField(
        max_length=16, choices=PlaceLookupStatus.choices, blank=True, default=""
    )
    place_looked_up_at = models.DateTimeField(null=True, blank=True)
    place_id = models.CharField(
        max_length=255, blank=True, default="", verbose_name="Google place ID"
    )
    place_name = models.CharField(max_length=255, blank=True, default="")
    place_address = models.CharField(max_length=500, blank=True, default="")
    place_latitude = models.FloatField(null=True, blank=True)
    place_longitude = models.FloatField(null=True, blank=True)
    place_business_status = models.CharField(max_length=32, blank=True, default="")
    place_maps_url = models.URLField(
        max_length=1000, blank=True, default="", verbose_name="Google Maps link"
    )
    place_website = models.URLField(max_length=1000, blank=True, default="")
    place_phone = models.CharField(max_length=64, blank=True, default="")

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
        return ", ".join(part for part in [self.city_town, self.state] if part)

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
        if self.has_confident_place and self.place_maps_url:
            return self.place_maps_url
        latitude, longitude = self.exact_location
        if latitude is None or longitude is None:
            return ""
        return f"https://www.google.com/maps/search/?api=1&query={latitude},{longitude}"

    def __str__(self):
        return self.name


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
