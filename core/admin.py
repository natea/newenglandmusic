import os
import re
from urllib.parse import unquote
from datetime import date

from dateutil import relativedelta
from django.contrib import admin
from django import forms
from django.contrib import messages
from django.contrib.admin import SimpleListFilter
from django.db.models import Q, URLField
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join, urlize
from django.utils.safestring import mark_safe
from ordered_model.admin import OrderedModelAdmin
from solo.admin import SingletonModelAdmin
from tinymce.widgets import TinyMCE

from .geo_filters import area_q, metro_fits_state, offered_areas, parse_geo_filter
from . import apple_music, youtube
from .places import PlacesClient, PlacesError
from .spotify import parse_artist_id
from .wikipedia import LICENSE_URL, commons_file_page, commons_thumbnail
from .event_performers import rebake
from .spotify_links import rebake_events_naming
from .artist_matching import normalize
from .job_runs import DIDNT_FINISH, STALE_AFTER, outcome
from .models import (
    AllEventProxy,
    AppleMusicArtistLink,
    Artist,
    Band,
    BandMembership,
    EventPerformer,
    MusicAct,
    YouTubeArtistLink,
    DateMessage,
    EmailSubscriber,
    Event,
    GeoArea,
    IndexPageMessages,
    JobRun,
    MenuItem,
    SpotifyArtistLink,
    StaticPage,
    Venue,
    VenueFetchStatus,
)
from .utils_datemath import (
    get_current_new_york_datetime,
    get_previous_current_next_month_start,
)

admin.site.site_title = "New England Music"
admin.site.site_header = "New England Music"

admin.site.register(IndexPageMessages, SingletonModelAdmin)


class GeoAreaListFilter(SimpleListFilter):
    """
    filters by a region, state or metro area from the venue sheet, with the same
    url parameters and rules as the public listing (see core/geo_filters.py)
    """

    kind = None
    # how the filtered model reaches the venue: "venue__" for events, "" for venues
    field_prefix = ""

    def lookups(self, request, model_admin):
        if self.kind == GeoArea.Kind.METRO:
            # only the chosen state's metros, like the site's metro list
            state = parse_geo_filter(request.GET).state
            areas = [metro for metro in offered_areas(self.kind) if metro_fits_state(metro, state)]
        else:
            areas = offered_areas(self.kind)
        return [(area.slug, area.label) for area in areas]

    def queryset(self, request, queryset):
        # self.value(), not the url: the sidebar's counts set it to each choice in turn
        params = request.GET.copy()
        params.pop(self.parameter_name, None)
        if self.value() is not None:
            params[self.parameter_name] = self.value()
        area = getattr(parse_geo_filter(params), self.parameter_name)
        if area is None:
            return queryset
        return queryset.filter(area_q(area, prefix=self.field_prefix))


def geo_area_list_filters(field_prefix):
    return [
        type(
            f"{kind.label}ListFilter",
            (GeoAreaListFilter,),
            {
                "kind": kind,
                "title": "metro area" if kind == GeoArea.Kind.METRO else kind.label.lower(),
                "parameter_name": kind.value,
                "field_prefix": field_prefix,
            },
        )
        for kind in GeoArea.Kind
    ]


class StartTimeListFilter(SimpleListFilter):
    title = "Start time"
    parameter_name = "starttime"

    def lookups(self, _request, _model_admin):
        return (
            (None, "Future"),
            ("last_month", "Last month"),
            ("this_month", "This month"),
            ("next_month", "Next month"),
            ("all", "All"),
        )

    def choices(self, changelist):
        for lookup, title in self.lookup_choices:
            yield {
                "selected": self.value() == lookup,
                "query_string": changelist.get_query_string(
                    {
                        self.parameter_name: lookup,
                    },
                    [],
                ),
                "display": title,
            }

    def queryset(self, request, queryset):
        (
            previous_month_start,
            current_month_start,
            next_month_start,
        ) = get_previous_current_next_month_start(get_current_new_york_datetime())
        next_next_month_start = next_month_start + relativedelta.relativedelta(months=1)

        if self.value() is None:
            # default is to show future only
            return queryset.filter(starttime__gte=get_current_new_york_datetime())
        if self.value() == "last_month":
            return queryset.filter(starttime__gte=previous_month_start).filter(
                starttime__lt=current_month_start
            )
        if self.value() == "next_month":
            return queryset.filter(starttime__gte=next_month_start).filter(
                starttime__lt=next_next_month_start
            )
        if self.value() == "this_month":
            return queryset.filter(
                starttime__gte=current_month_start, starttime__lt=next_month_start
            )
        # return all!
        return queryset


class KindListFilter(SimpleListFilter):
    """
    by default, leaves out events labelled as not music (trivia, comedy, karaoke, ...)
    -- unlabelled events are shown, so nothing is hidden without a label
    """

    title = "Kind"
    parameter_name = "kind"

    def lookups(self, _request, _model_admin):
        return (
            (None, "Music + unlabelled"),
            *Event.Kind.choices,
            ("unlabelled", "Unlabelled"),
            ("not_music", "All not music"),
            ("all", "All"),
        )

    def choices(self, changelist):
        for lookup, title in self.lookup_choices:
            yield {
                "selected": self.value() == lookup,
                "query_string": changelist.get_query_string({self.parameter_name: lookup}, []),
                "display": title,
            }

    def queryset(self, request, queryset):
        music_or_unlabelled = Q(kind__in=Event.MUSIC_KINDS) | Q(kind="")
        if self.value() is None:
            return queryset.filter(music_or_unlabelled)
        if self.value() == "unlabelled":
            return queryset.filter(kind="")
        if self.value() == "not_music":
            return queryset.exclude(music_or_unlabelled)
        if self.value() in Event.Kind.values:
            return queryset.filter(kind=self.value())
        return queryset


class EventPerformerInline(admin.TabularInline):
    """an event's artists and bands, in billing order (add-artists-from-events)"""

    model = EventPerformer
    extra = 0
    fields = ("order", "artist", "band", "source")
    readonly_fields = ("source",)
    autocomplete_fields = ("artist", "band")
    verbose_name = "performer"
    verbose_name_plural = "performers"


class EventAdmin(admin.ModelAdmin):
    inlines = [EventPerformerInline]

    def save_formset(self, request, form, formset, change):
        # a performer added here is the editor's, and stays when the text is linked again
        if formset.model is EventPerformer:
            # save(commit=False) gives the new and changed rows: an editor's now
            for performer in formset.save(commit=False):
                performer.source = EventPerformer.Source.EDITOR
                performer.save()
            for performer in formset.deleted_objects:
                performer.delete()
            # the listing links its performers' names, so it's rendered again
            rebake(formset.instance)
            return
        super().save_formset(request, form, formset, change)

    # links typed without a scheme get https, which django 6 makes the default
    formfield_overrides = {URLField: {"assume_scheme": "https"}}
    list_per_page = 500
    list_display = (
        "is_approved",
        "starttime",
        "same_time_order_override",
        "get_preface_as_text",
        "title",
        "artists",
        "get_venue_link",
        "kind",
        "get_description_as_text",
        "price",
        "is_cancelled",
    )
    autocomplete_fields = ("venue",)
    list_select_related = ("venue",)
    # define a custom order for the fields
    # TODO always keep in sync with the fields in the model..!
    fields = (
        "is_approved",
        "starttime",
        "starttime_override",
        "hyperlink",
        "title",
        "artists",
        "venue",
        "ticket_hyperlink",
        "description",
        "preface",
        "venue_override",
        "age_policy_override",
        "age_policy_emoji_override",
        "price",
        "is_cancelled",
        "kind",
        "same_time_order_override",
        "user_submitted",
        "user_submission_email",
        # where an imported event came from. a seatgeek page is shown only here, never on
        # the site: seatgeek resells tickets
        "source",
        "get_source_link",
        "external_id",
    )
    readonly_fields = ("user_submitted", "source", "get_source_link", "external_id")
    list_display_links = ("starttime",)
    # there are more save_* options that are being overriden
    # in templatetags/admin_save_buttons_override --
    # namely, the fact that both 'save as new' and 'save and add another' buttons
    # appear simultanously is not something that can be set using 'regular'
    # django admin options
    save_on_top = True
    search_fields = (
        "title",
        "artists",
        "venue__name",
        "description",
        "preface",
    )
    list_filter = [
        StartTimeListFilter,
        KindListFilter,
        *geo_area_list_filters(field_prefix="venue__"),
        "is_approved",
        "user_submitted",
        "source",
    ]
    list_editable = ("same_time_order_override",)
    actions = ["mark_as_approved", "mark_as_unapproved", "mark_as_live_music", "mark_as_not_music"]

    class Media:
        js = [
            "core/admin/time-shortcuts-override.js",
        ]
        css = {
            "all": ("core/admin/date-time-widget-fixes.css",),
        }

    def get_ordering(self, request):
        return ["starttime", "same_time_order_override"]

    # remove default bulk delete action - it's scary!
    def get_actions(self, request):
        actions = super().get_actions(request)
        if "delete_selected" in actions:
            del actions["delete_selected"]
        return actions

    # customizing the tinymce field is a painful/weird process.
    # changing the 'rows'/'cols' value (passing them as `attras`), as per the documentation,
    # does nothing... (it changes the <textarea>'s rows and cols attribute values, but that's
    # not taken into account by tinymce, which also receives a width/height value...)
    # TLDR: mce_attrs.height/width is where it's at!!
    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name in ["description", "preface", "venue_override"]:
            return db_field.formfield(
                widget=TinyMCE(
                    mce_attrs={
                        "height": "200" if db_field.name == "description" else "150"
                    }
                )
            )
        return super().formfield_for_dbfield(db_field, **kwargs)

    def get_preface_as_text(self, obj):
        return mark_safe(obj.preface) if obj.preface else ""

    get_preface_as_text.short_description = "Preface"

    def get_venue_link(self, obj):
        if obj.venue is None:
            return ""
        url = reverse("admin:core_venue_change", args=[obj.venue.pk])
        return format_html('<a href="{}">{}</a>', url, obj.venue.name)

    get_venue_link.short_description = "Venue"
    get_venue_link.admin_order_field = "venue__name"

    def get_source_link(self, obj):
        if not obj.source_url:
            return ""
        return format_html('<a href="{}" target="_blank" rel="noopener">{}</a>', obj.source_url, obj.source_url)

    get_source_link.short_description = "Source page"

    def get_description_as_text(self, obj):
        return mark_safe(obj.description) if obj.description else ""

    get_description_as_text.short_description = "Description"

    def save_model(self, request, obj, form, change):
        # a kind chosen in the form is an admin's label, which imports never overwrite
        if "kind" in form.changed_data:
            obj.kind_set_by = Event.KindSetBy.ADMIN if obj.kind else ""
        super().save_model(request, obj, form, change)

    @admin.action(description="Mark as approved")
    def mark_as_approved(self, request, queryset):
        queryset.update(is_approved=True)

    # takes events off the site. relabelling doesn't, so this is how to remove an
    # approved event that turns out not to be music
    @admin.action(description="Mark as unapproved")
    def mark_as_unapproved(self, request, queryset):
        queryset.update(is_approved=False)

    # an admin's label is never overwritten by later imports
    @admin.action(description="Mark as live music")
    def mark_as_live_music(self, request, queryset):
        queryset.update(kind=Event.Kind.LIVE_MUSIC, kind_set_by=Event.KindSetBy.ADMIN)

    @admin.action(description="Mark as not music (other)")
    def mark_as_not_music(self, request, queryset):
        queryset.update(kind=Event.Kind.OTHER, kind_set_by=Event.KindSetBy.ADMIN)

    # disable the "delete" button on the venue field
    # without implementing a whole `has_delete_permission` which always
    # returns False on all venue -- that would make it impossible
    # to delete a venue object
    # https://stackoverflow.com/a/62459642
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        field = form.base_fields["venue"]
        field.widget.can_delete_related = False
        return form


admin.site.register(AllEventProxy, EventAdmin)


class StaticPageAdmin(admin.ModelAdmin):
    list_display = ("url_path", "is_public", "title", "get_content_as_text")
    search_fields = ("url_path", "title", "content")
    ordering = ("url_path",)
    list_per_page = 500
    list_filter = ("is_public",)
    actions = ["make_page_public","make_page_non_public"]
    
    @admin.action(description="Make public")
    def make_page_public(self, request, queryset):
        queryset.update(is_public=True)
        
        
    @admin.action(description="Make non-public")
    def make_page_non_public(self, request, queryset):
        queryset.update(is_public=False)

    # use custom query set that returns all static pages, including
    # not public ones -- which are hidden by the default queryset
    # returned by `get_queryset`
    def get_queryset(self, request):
        return StaticPage.all_objects.all()

    def get_content_as_text(self, obj):
        # extract the first 100 characters, making
        # sure to skip tags
        # TODO nit - don't show ellipsis when text len is less than 100 chars; use + instead * in regex
        return re.sub(r"<[^>]*>", "", obj.content)[:100] + "..."

    get_content_as_text.short_description = "Content"


admin.site.register(StaticPage, StaticPageAdmin)


class LinkedToTicketmasterFilter(SimpleListFilter):
    title = "linked to Ticketmaster"
    parameter_name = "ticketmaster"
    field = "ticketmaster_venue_id"

    def lookups(self, request, model_admin):
        return (("yes", "Yes"), ("no", "No"))

    def queryset(self, request, queryset):
        linked = Q(**{f"{self.field}__isnull": False}) & ~Q(**{self.field: ""})
        if self.value() == "yes":
            return queryset.filter(linked)
        if self.value() == "no":
            return queryset.exclude(linked)
        return queryset


class LinkedToEventbriteFilter(LinkedToTicketmasterFilter):
    title = "linked to Eventbrite"
    parameter_name = "eventbrite"
    field = "eventbrite_organizer_id"


class LinkedToSeatGeekFilter(LinkedToTicketmasterFilter):
    title = "linked to SeatGeek"
    parameter_name = "seatgeek"
    field = "seatgeek_venue_id"


class FetchStatusFilter(SimpleListFilter):
    """how a venue's latest event fetch went (see VenueFetchStatus)"""

    title = "last fetch"
    parameter_name = "fetch"

    def lookups(self, request, model_admin):
        return (
            ("problems", "Problems"),
            ("nothing", "Nothing found"),
            ("ok", "OK"),
            ("never", "Never fetched"),
        )

    def queryset(self, request, queryset):
        no_problems = Q(fetch_status__problems=[])
        if self.value() == "problems":
            return queryset.filter(fetch_status__isnull=False).exclude(no_problems)
        if self.value() == "nothing":
            return queryset.filter(no_problems, fetch_status__upcoming=0)
        if self.value() == "ok":
            return queryset.filter(no_problems, fetch_status__upcoming__gt=0)
        if self.value() == "never":
            return queryset.filter(fetch_status__isnull=True)
        return queryset


REVIEW_REASON_WORDS = {
    "name": "name differs", "state": "in another state", "distance": "too far", "type": "not a venue",
}


def google_place_name(place_id):
    """
    a place's name on google right now, or why it couldn't be asked: shown to an admin
    judging a review match, never saved, since google's terms let us store only the id
    """
    api_key = os.environ.get("GOOGLE_PLACES_API_KEY")
    if not api_key:
        return "GOOGLE_PLACES_API_KEY isn't set"
    try:
        return PlacesClient(api_key).place_name(place_id) or "(no name on google)"
    except PlacesError as e:
        return f"couldn't ask google ({e})"


class PlaceReviewReasonFilter(SimpleListFilter):
    """why a venue's google match needs review (lookup_venue_places)"""

    title = "why review"
    parameter_name = "review_reason"

    def lookups(self, request, model_admin):
        return list(REVIEW_REASON_WORDS.items())

    def queryset(self, request, queryset):
        if self.value() in REVIEW_REASON_WORDS:
            return queryset.filter(
                place_lookup_status=Venue.PlaceLookupStatus.REVIEW, place_review_reasons__contains=[self.value()]
            )
        return queryset


class VenueAdminForm(forms.ModelForm):
    no_neighborhood = forms.BooleanField(
        required=False,
        help_text="this venue isn't in a neighborhood worth naming: later lookups leave it blank",
    )

    class Meta:
        model = Venue
        fields = "__all__"
        help_texts = {
            "neighborhood": "type one to set it by hand; later lookups keep an editor's neighborhood",
        }


class VenueAdmin(admin.ModelAdmin):
    form = VenueAdminForm
    # links typed without a scheme get https, which django 6 makes the default
    formfield_overrides = {URLField: {"assume_scheme": "https"}}
    list_display = (
        "name",
        "is_active",
        "city_town",
        "state",
        "venue_type",
        "size",
        "open_booking",
        "open_mic",
        "age_policy",
        "sheet_id",
        "last_fetch",
        "why_review",
        "google_name_link",
    )
    list_display_links = ("name",)
    list_filter = (
        "is_active",
        *geo_area_list_filters(field_prefix=""),
        "size",
        "open_booking",
        "open_mic",
        "booking_type",
        LinkedToTicketmasterFilter,
        LinkedToEventbriteFilter,
        LinkedToSeatGeekFilter,
        FetchStatusFilter,
        "place_lookup_status",
        PlaceReviewReasonFilter,
        "neighborhood_source",
    )
    search_fields = (
        "name",
        "city_town",
        "county",
        "venue_type",
        "sheet_id",
        "ticketmaster_venue_id",
        "eventbrite_organizer_id",
        "seatgeek_venue_id",
    )
    ordering = ("name",)
    save_on_top = True
    actions = [
        "mark_as_inactive",
        "mark_as_active",
        "mark_place_as_confident",
        "clear_place_lookup",
        "skip_place_lookup",
    ]
    fieldsets = (
        (None, {"fields": ("sheet_id", "name", "is_active", "venue_type", "size")}),
        (
            "Location",
            {"fields": ("state", "city_town", "county", "latitude", "longitude")},
        ),
        ("Music", {"fields": ("genres", "genre_notes", "niche_notes")}),
        (
            "Booking",
            {
                "fields": (
                    "open_booking",
                    "booking_type",
                    "open_mic",
                    "website",
                    "booking_url",
                    "booking_notes",
                )
            },
        ),
        (
            "Access",
            {
                "fields": (
                    "age_policy",
                    "accessibility_notes",
                    "family_friendly",
                    "lgbtq_friendly",
                    "diverse",
                )
            },
        ),
        ("Safety", {"fields": ("safety_flag", "safety_url", "safety_notes")}),
        # not synced from the sheet
        (
            "Place (from Google, not the sheet)",
            {
                "fields": (
                    "place_lookup_status",
                    "why_review",
                    "google_name",
                    "place_looked_up_at",
                    "place_id",
                    "place_on_google_maps",
                    "place_latitude",
                    "place_longitude",
                )
            },
        ),
        # from openstreetmap (lookup_venue_neighborhoods), or an editor's
        (
            "Neighborhood (from OpenStreetMap, not the sheet)",
            {"fields": ("neighborhood", "no_neighborhood", "neighborhood_source", "neighborhood_checked_at")},
        ),
        (
            "Event sources",
            {"fields": ("ticketmaster_venue_id", "eventbrite_organizer_id", "seatgeek_venue_id", "ticket_page_url")},
        ),
        ("Event fetching", {"fields": ("fetch_status_details",)}),
    )
    readonly_fields = (
        "fetch_status_details", "place_on_google_maps", "why_review", "google_name", "neighborhood_source",
        "neighborhood_checked_at",
    )

    class Media:
        js = ["core/admin/google-name.js"]

    def get_urls(self):
        name = f"{self.model._meta.app_label}_{self.model._meta.model_name}_google_name"
        return [
            path("<int:pk>/google-name/", self.admin_site.admin_view(self.google_name_view), name=name),
            *super().get_urls(),
        ]

    def google_name_view(self, request, pk):
        """a review venue's place name on google, asked for when an admin clicks for it"""
        venue = get_object_or_404(Venue, pk=pk)
        if not self.has_view_permission(request, venue):
            raise Http404
        if venue.place_lookup_status != Venue.PlaceLookupStatus.REVIEW or not venue.place_id:
            raise Http404("only a match needing review is looked up")
        response = HttpResponse(google_place_name(venue.place_id), content_type="text/plain; charset=utf-8")
        # google's content mustn't be kept, by a browser either
        response["Cache-Control"] = "no-store"
        return response

    def save_model(self, request, venue, form, change):
        """a neighborhood typed here, or "no neighborhood", is the editor's: lookups keep it"""
        if form.cleaned_data.get("no_neighborhood"):
            venue.neighborhood = ""
            venue.neighborhood_source = Venue.NeighborhoodSource.EDITOR
            venue.neighborhood_checked_at = timezone.now()
        elif "neighborhood" in form.changed_data:
            venue.neighborhood = venue.neighborhood.strip()
            venue.neighborhood_source = Venue.NeighborhoodSource.EDITOR if venue.neighborhood else ""
            venue.neighborhood_checked_at = timezone.now() if venue.neighborhood else None
        # save() re-renders the venue's events, whose stored html shows the neighborhood
        super().save_model(request, venue, form, change)

    # google's terms don't let us store a place's name or address, so this shows the live
    # place for judging a match
    @admin.display(description="why review")
    def why_review(self, venue):
        """the checks the match failed, in words: "name differs · 0.4 km away" """
        if venue.place_lookup_status != Venue.PlaceLookupStatus.REVIEW:
            return ""
        reasons = list(venue.place_review_reasons or [])
        if not reasons:
            return "not recorded (run lookup_venue_places --review)"
        words = [REVIEW_REASON_WORDS[r] for r in reasons if r in REVIEW_REASON_WORDS and r != "distance"]
        if venue.place_distance_km is not None:
            words.append(f"{venue.place_distance_km:g} km away" + (" (over 25)" if "distance" in reasons else ""))
        elif "distance" in reasons:
            words.append(REVIEW_REASON_WORDS["distance"])
        return " · ".join(words)

    @admin.display(description="google's name")
    def google_name(self, venue):
        """on the venue's page: asked for live, and only for a match needing review"""
        if venue.place_lookup_status != Venue.PlaceLookupStatus.REVIEW or not venue.place_id:
            return "-"
        return google_place_name(venue.place_id)

    @admin.display(description="google's place")
    def google_name_link(self, venue):
        """in the list: nothing is asked of google until the admin clicks, for that venue"""
        if venue.place_lookup_status != Venue.PlaceLookupStatus.REVIEW or not venue.place_id:
            return ""
        return format_html(
            '<a href="{}" data-google-name>show Google\'s name</a> · '
            '<a href="https://www.google.com/maps/place/?q=place_id:{}" target="_blank" rel="noopener">map</a>',
            reverse("admin:core_venue_google_name", args=[venue.pk]),
            venue.place_id,
        )

    @admin.display(description="on google maps")
    def place_on_google_maps(self, venue):
        if not venue.place_id:
            return "-"
        return format_html(
            '<a href="https://www.google.com/maps/place/?q=place_id:{}" target="_blank" '
            'rel="noopener">View on Google Maps</a>',
            venue.place_id,
        )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("fetch_status")

    @staticmethod
    def _fetch_status(venue):
        try:
            return venue.fetch_status
        except VenueFetchStatus.DoesNotExist:
            return None

    @admin.display(description="last fetch")
    def last_fetch(self, venue):
        status = self._fetch_status(venue)
        if status is None:
            return format_html('<span style="color: #6e7781">never fetched</span>')
        if status.problems:
            return format_html(
                '<strong style="color: #cf222e">problems ({})</strong>', len(status.problems)
            )
        if not status.upcoming:
            return format_html('<span style="color: #6e7781">nothing found</span>')
        return format_html(
            '<span style="color: #1a7f37">OK · {} upcoming</span>', status.upcoming
        )

    @admin.display(description="latest fetch")
    def fetch_status_details(self, venue):
        status = self._fetch_status(venue)
        if status is None:
            return "never fetched"
        run_link = (
            format_html(
                ' · <a href="{}">job run</a>',
                reverse("admin:core_jobrun_change", args=[status.job_run_id]),
            )
            if status.job_run_id
            else ""
        )
        problems = (
            format_html(
                '<strong style="color: #cf222e">problems</strong><ul>{}</ul>',
                format_html_join("", "<li>{}</li>", ((linked(p),) for p in status.problems)),
            )
            if status.problems
            else "no problems"
        )
        return format_html(
            "{} · {} · {} found, {} upcoming{}<br>{}",
            timezone.localtime(status.fetched_at).strftime("%b %-d, %Y %-I:%M %p"),
            status.source,
            status.found,
            status.upcoming,
            run_link,
            problems,
        )

    # remove default bulk delete action - it's scary!
    def get_actions(self, request):
        actions = super().get_actions(request)
        if "delete_selected" in actions:
            del actions["delete_selected"]
        return actions

    @admin.action(description="Mark as inactive")
    def mark_as_inactive(self, request, queryset):
        queryset.update(is_active=False)

    @admin.action(description="Mark as active")
    def mark_as_active(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description="Mark place match as confident")
    def mark_place_as_confident(self, request, queryset):
        # save() rather than update(), so events' baked html picks up the new location
        for venue in queryset.exclude(place_id=""):
            venue.place_lookup_status = Venue.PlaceLookupStatus.CONFIDENT
            venue.place_review_reasons = []
            venue.place_distance_km = None
            venue.save()

    @admin.action(description="Clear place lookup")
    def clear_place_lookup(self, request, queryset):
        for venue in queryset:
            venue.place_lookup_status = ""
            venue.place_looked_up_at = None
            venue.place_id = ""
            venue.place_latitude = venue.place_longitude = None
            venue.place_review_reasons = []
            venue.place_distance_km = None
            venue.save()

    @admin.action(description="Don't look up on Google (no single place, e.g. a festival)")
    def skip_place_lookup(self, request, queryset):
        """
        for a venue with no single place, such as a festival across a town: its matched place
        goes, as when clearing, and no lookup searches for it again. clearing undoes it
        """
        # the ids first: the queryset keeps the list's filters, and once cleared a venue no
        # longer matches "needs review"
        pks = list(queryset.values_list("pk", flat=True))
        self.clear_place_lookup(request, queryset)
        # update(): clearing just saved them, re-rendering their events with the sheet's pins
        count = Venue.objects.filter(pk__in=pks).update(place_lookup_status=Venue.PlaceLookupStatus.SKIPPED)
        venues = "1 venue" if count == 1 else f"{count} venues"
        self.message_user(request, f"{venues} won't be looked up on Google. Clear their lookup to undo.")


admin.site.register(Venue, VenueAdmin)


class DateMessageAdmin(admin.ModelAdmin):
    list_display = ("date", "message")
    ordering = ("-date",)

    class Media:
        css = {
            "all": ("core/admin/date-time-widget-fixes.css",),
        }


admin.site.register(DateMessage, DateMessageAdmin)


class EmailSubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "created_at")
    ordering = ("-created_at",)


admin.site.register(EmailSubscriber, EmailSubscriberAdmin)


class MenuItemAdmin(OrderedModelAdmin):
    list_display = ("name", "show_in_header", "show_in_footer", "move_up_down_links")


admin.site.register(MenuItem, MenuItemAdmin)


def linked(problem):
    """a problem message with its urls as links, to open the failing page in a new tab"""
    return mark_safe(
        urlize(problem, autoescape=True).replace("<a ", '<a target="_blank" rel="noopener" ')
    )


class JobRunOutcomeFilter(SimpleListFilter):
    title = "outcome"
    parameter_name = "outcome"

    def lookups(self, request, model_admin):
        return [*JobRun.Status.choices, (DIDNT_FINISH, "Didn't finish")]

    def queryset(self, request, queryset):
        stale = Q(status=JobRun.Status.RUNNING, started_at__lt=timezone.now() - STALE_AFTER)
        if self.value() == DIDNT_FINISH:
            return queryset.filter(stale)
        if self.value() == JobRun.Status.RUNNING:
            return queryset.filter(status=JobRun.Status.RUNNING).exclude(stale)
        if self.value():
            return queryset.filter(status=self.value())
        return queryset


# runs of the pipeline commands, recorded by core/job_runs.py; read-only
class JobRunAdmin(admin.ModelAdmin):
    list_display = (
        "command",
        "started_at",
        "duration",
        "outcome_label",
        "problem_count",
        "dry_run",
        "summary_text",
    )
    list_filter = ("command", JobRunOutcomeFilter, "dry_run")
    ordering = ("-started_at",)
    fields = (
        "command",
        "arguments",
        "started_at",
        "finished_at",
        "duration",
        "outcome_label",
        "dry_run",
        "summary_text",
        "error_text",
        "problems_table",
        "output_text",
    )
    readonly_fields = fields

    OUTCOME_COLOURS = {
        JobRun.Status.SUCCEEDED: "#1a7f37",
        JobRun.Status.RUNNING: "#9a6700",
        JobRun.Status.FAILED: "#cf222e",
        DIDNT_FINISH: "#cf222e",
    }

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description="outcome")
    def outcome_label(self, run):
        label = outcome(run)
        return format_html(
            '<strong style="color: {}">{}</strong>', self.OUTCOME_COLOURS[label], label
        )

    @admin.display(description="duration")
    def duration(self, run):
        if not run.finished_at:
            return "-"
        seconds = int((run.finished_at - run.started_at).total_seconds())
        return f"{seconds // 60}m {seconds % 60}s" if seconds >= 60 else f"{seconds}s"

    @admin.display(description="summary")
    def summary_text(self, run):
        return " · ".join(f"{label} {count}" for label, count in run.summary)

    @admin.display(description="problems")
    def problem_count(self, run):
        count = len(run.problems)
        if not count:
            return "0"
        return format_html('<strong style="color: #cf222e">{}</strong>', count)

    @admin.display(description="problems")
    def problems_table(self, run):
        if not run.problems:
            return "no problems"
        rows = format_html_join(
            "",
            '<tr><td style="white-space: nowrap; vertical-align: top">'
            '<a href="{}">{} {}</a></td><td><ul style="margin: 0">{}</ul></td></tr>',
            (
                (
                    reverse("admin:core_venue_change", args=[item["venue_id"]]),
                    item["sheet_id"],
                    item["name"],
                    format_html_join("", "<li>{}</li>", ((linked(p),) for p in item["problems"])),
                )
                for item in run.problems
            ),
        )
        return format_html(
            '<div style="border-left: 4px solid #cf222e; padding-left: 8px">'
            '<strong style="color: #cf222e">{} venues with problems</strong>'
            "<table>{}</table></div>",
            len(run.problems),
            rows,
        )

    @admin.display(description="error")
    def error_text(self, run):
        return format_html('<pre style="white-space: pre-wrap">{}</pre>', run.error) if run.error else "-"

    @admin.display(description="output")
    def output_text(self, run):
        return format_html('<pre style="white-space: pre-wrap">{}</pre>', run.output or "-")


admin.site.register(JobRun, JobRunAdmin)


class SpotifyArtistLinkForm(forms.ModelForm):
    spotify_link = forms.CharField(
        required=False,
        label="Spotify artist link",
        help_text="paste the artist's link from Spotify (Share > Copy link to artist), "
        "e.g. https://open.spotify.com/artist/... or spotify:artist:...",
    )
    no_spotify_artist = forms.BooleanField(
        required=False, help_text="this name has no artist on Spotify: show no play button"
    )

    class Meta:
        model = SpotifyArtistLink
        fields = ["name_key"]
        labels = {"name_key": "Artist name"}
        help_texts = {"name_key": "as an event writes it; it's stored normalized"}

    def clean_name_key(self):
        key = normalize(self.cleaned_data["name_key"])
        if not key:
            raise forms.ValidationError("enter the artist's name")
        return key

    def clean_spotify_link(self):
        link = self.cleaned_data["spotify_link"].strip()
        if link and not parse_artist_id(link):
            raise forms.ValidationError(
                "that isn't a Spotify artist link: it should look like "
                "https://open.spotify.com/artist/... or spotify:artist:..."
            )
        return link

    def clean(self):
        cleaned = super().clean()
        link, none = cleaned.get("spotify_link"), cleaned.get("no_spotify_artist")
        if link and none:
            raise forms.ValidationError("give a Spotify link or tick no Spotify artist, not both")
        if not link and not none and not self.instance.pk:
            raise forms.ValidationError("give a Spotify link, or tick no Spotify artist")
        return cleaned


class SpotifyArtistLinkAdmin(admin.ModelAdmin):
    form = SpotifyArtistLinkForm
    list_display = ["name_key", "status", "spotify_page", "source", "checked_at", "last_seen_at"]
    list_filter = ["status", "source"]
    search_fields = ["name_key"]
    readonly_fields = ["status", "spotify_page", "source", "checked_at", "last_seen_at"]
    actions = ["mark_no_spotify_artist"]

    @admin.display(description="Spotify")
    def spotify_page(self, link):
        if not link.spotify_artist_id:
            return "-"
        return format_html(
            '<a href="https://open.spotify.com/artist/{}" target="_blank">{}</a>',
            link.spotify_artist_id,
            link.spotify_artist_id,
        )

    def save_model(self, request, link, form, change):
        """an editor's choice: matched to the pasted artist, or no artist"""
        now = timezone.now()
        artist_id = parse_artist_id(form.cleaned_data.get("spotify_link"))
        if artist_id or form.cleaned_data.get("no_spotify_artist"):
            link.status = SpotifyArtistLink.Status.MATCHED if artist_id else SpotifyArtistLink.Status.NONE
            link.spotify_artist_id = artist_id or ""
            link.source = SpotifyArtistLink.Source.EDITOR
            link.checked_at = now
        if not link.last_seen_at:
            link.last_seen_at = now
        super().save_model(request, link, form, change)
        rebake_events_naming([link.name_key])

    @admin.action(description="Mark as no Spotify artist")
    def mark_no_spotify_artist(self, request, queryset):
        keys = list(queryset.values_list("name_key", flat=True))
        queryset.update(
            status=SpotifyArtistLink.Status.NONE,
            spotify_artist_id="",
            source=SpotifyArtistLink.Source.EDITOR,
            checked_at=timezone.now(),
        )
        rebake_events_naming(keys)


admin.site.register(SpotifyArtistLink, SpotifyArtistLinkAdmin)


class AppleMusicArtistLinkForm(forms.ModelForm):
    apple_music_link = forms.CharField(
        required=False,
        label="Apple Music artist link",
        help_text="paste the artist's page link from Apple Music, "
        "e.g. https://music.apple.com/us/artist/the-ballroom-thieves/489634654",
    )
    no_apple_music_artist = forms.BooleanField(
        required=False, help_text="this name has no artist on Apple Music: show no play button"
    )

    class Meta:
        model = AppleMusicArtistLink
        fields = ["name_key"]
        labels = {"name_key": "Artist name"}
        help_texts = {"name_key": "as an event writes it; it's stored normalized"}

    def clean_name_key(self):
        key = normalize(self.cleaned_data["name_key"])
        if not key:
            raise forms.ValidationError("enter the artist's name")
        return key

    def clean_apple_music_link(self):
        link = self.cleaned_data["apple_music_link"].strip()
        if link and not apple_music.parse_artist_id(link):
            raise forms.ValidationError(
                "that isn't an Apple Music artist link: it should look like "
                "https://music.apple.com/us/artist/<name>/<number>"
            )
        return link

    def clean(self):
        cleaned = super().clean()
        link, none = cleaned.get("apple_music_link"), cleaned.get("no_apple_music_artist")
        if link and none:
            raise forms.ValidationError("give an Apple Music link or tick no Apple Music artist, not both")
        if not link and not none and not self.instance.pk:
            raise forms.ValidationError("give an Apple Music link, or tick no Apple Music artist")
        return cleaned


class AppleMusicArtistLinkAdmin(admin.ModelAdmin):
    form = AppleMusicArtistLinkForm
    list_display = ["name_key", "status", "apple_music_page", "top_song", "source", "checked_at", "last_seen_at"]
    list_filter = ["status", "source"]
    search_fields = ["name_key"]
    readonly_fields = ["status", "apple_music_page", "top_song", "source", "checked_at", "last_seen_at"]
    actions = ["mark_no_apple_music_artist"]

    @admin.display(description="Apple Music")
    def apple_music_page(self, link):
        if not link.apple_artist_id:
            return "-"
        return format_html(
            '<a href="https://music.apple.com/us/artist/{}" target="_blank">{}</a>',
            link.apple_artist_id,
            link.apple_artist_id,
        )

    @admin.display(description="top song")
    def top_song(self, link):
        if not link.top_song_id:
            return "-"
        return format_html(
            '<a href="https://music.apple.com/us/album/{}?i={}" target="_blank">{}</a>',
            link.top_album_id,
            link.top_song_id,
            link.top_song_id,
        )

    def save_model(self, request, link, form, change):
        """an editor's choice: matched to the pasted artist (with its top song), or no artist"""
        now = timezone.now()
        artist_id = apple_music.parse_artist_id(form.cleaned_data.get("apple_music_link"))
        if artist_id or form.cleaned_data.get("no_apple_music_artist"):
            link.status = AppleMusicArtistLink.Status.MATCHED if artist_id else AppleMusicArtistLink.Status.NONE
            link.apple_artist_id = artist_id or ""
            link.top_song_id = link.top_album_id = ""
            link.source = AppleMusicArtistLink.Source.EDITOR
            link.checked_at = now
            if artist_id:
                self.look_up_top_song(request, link)
        if not link.last_seen_at:
            link.last_seen_at = now
        super().save_model(request, link, form, change)
        rebake_events_naming([link.name_key])

    def look_up_top_song(self, request, link):
        if not apple_music.credentials():
            messages.warning(request, "Apple Music isn't configured, so the artist's top song wasn't looked up.")
            return
        try:
            song = apple_music.client().top_song(link.apple_artist_id)
        except apple_music.AppleMusicError as e:
            messages.warning(request, f"The artist was saved, but its top song couldn't be looked up: {e}")
            return
        if song:
            link.top_song_id, link.top_album_id = song["song_id"], song["album_id"]
        else:
            messages.warning(request, "Apple Music lists no top songs for this artist, so no button will show.")

    @admin.action(description="Mark as no Apple Music artist")
    def mark_no_apple_music_artist(self, request, queryset):
        keys = list(queryset.values_list("name_key", flat=True))
        queryset.update(
            status=AppleMusicArtistLink.Status.NONE,
            apple_artist_id="",
            top_song_id="",
            top_album_id="",
            source=AppleMusicArtistLink.Source.EDITOR,
            checked_at=timezone.now(),
        )
        rebake_events_naming(keys)


admin.site.register(AppleMusicArtistLink, AppleMusicArtistLinkAdmin)


class YouTubeArtistLinkForm(forms.ModelForm):
    youtube_link = forms.CharField(
        required=False,
        label="YouTube channel or video link",
        help_text="paste the artist's channel link (https://www.youtube.com/channel/UC…) or one of "
        "their videos (https://www.youtube.com/watch?v=… or https://youtu.be/…)",
    )
    no_youtube = forms.BooleanField(required=False, help_text="this name has no YouTube: show no play button")

    class Meta:
        model = YouTubeArtistLink
        fields = ["name_key"]
        labels = {"name_key": "Artist name"}
        help_texts = {"name_key": "as an event writes it; it's stored normalized"}

    def clean_name_key(self):
        key = normalize(self.cleaned_data["name_key"])
        if not key:
            raise forms.ValidationError("enter the artist's name")
        return key

    def clean_youtube_link(self):
        link = self.cleaned_data["youtube_link"].strip()
        if link and not youtube.parse_link(link):
            raise forms.ValidationError(
                "that isn't a YouTube channel or video link: it should look like "
                "https://www.youtube.com/channel/UC…, https://www.youtube.com/watch?v=… or https://youtu.be/…"
            )
        return link

    def clean(self):
        cleaned = super().clean()
        link, none = cleaned.get("youtube_link"), cleaned.get("no_youtube")
        if link and none:
            raise forms.ValidationError("give a YouTube link or tick no YouTube, not both")
        if not link and not none and not self.instance.pk:
            raise forms.ValidationError("give a YouTube link, or tick no YouTube")
        return cleaned


class YouTubeArtistLinkAdmin(admin.ModelAdmin):
    form = YouTubeArtistLinkForm
    list_display = ["name_key", "status", "evidence", "youtube_page", "source", "checked_at", "last_seen_at"]
    list_filter = ["status", "evidence", "source"]
    search_fields = ["name_key"]
    readonly_fields = ["status", "evidence", "youtube_page", "source", "checked_at", "last_seen_at"]
    actions = ["mark_no_youtube"]

    @admin.display(description="YouTube")
    def youtube_page(self, link):
        if link.video_id:
            return format_html('<a href="https://www.youtube.com/watch?v={}" target="_blank">{}</a>', link.video_id, link.video_id)
        if link.channel_id:
            return format_html('<a href="https://www.youtube.com/channel/{}" target="_blank">{}</a>', link.channel_id, link.channel_id)
        return "-"

    def save_model(self, request, link, form, change):
        """an editor's choice: matched to the pasted channel or video, or no youtube"""
        now = timezone.now()
        found = youtube.parse_link(form.cleaned_data.get("youtube_link"))
        if found or form.cleaned_data.get("no_youtube"):
            kind, found_id = found or ("", "")
            link.status = YouTubeArtistLink.Status.MATCHED if found else YouTubeArtistLink.Status.NONE
            link.evidence = YouTubeArtistLink.Evidence.EDITOR
            link.channel_id = found_id if kind == "channel" else ""
            link.video_id = found_id if kind == "video" else ""
            link.source = YouTubeArtistLink.Source.EDITOR
            link.checked_at = now
            if kind == "video":
                self.look_up_channel(request, link)
        if not link.last_seen_at:
            link.last_seen_at = now
        super().save_model(request, link, form, change)
        rebake_events_naming([link.name_key])

    def look_up_channel(self, request, link):
        """the pasted video's channel, for the player's "More by …" link"""
        if not youtube.api_key():
            messages.warning(request, "YouTube isn't configured, so the video wasn't checked.")
            return
        try:
            video = youtube.client().videos([link.video_id]).get(link.video_id)
        except youtube.YouTubeError as e:
            messages.warning(request, f"The video was saved, but couldn't be checked: {e}")
            return
        if video is None:
            messages.warning(request, "YouTube has no such video, so no button will show until it's fixed.")
            link.status = YouTubeArtistLink.Status.NOT_FOUND
            return
        link.channel_id = video["channel_id"]
        if not video["embeddable"]:
            messages.warning(request, "That video can't be embedded, so no button will show until it's fixed.")
            link.status = YouTubeArtistLink.Status.NOT_FOUND

    @admin.action(description="Mark as no YouTube")
    def mark_no_youtube(self, request, queryset):
        keys = list(queryset.values_list("name_key", flat=True))
        queryset.update(
            status=YouTubeArtistLink.Status.NONE,
            evidence=YouTubeArtistLink.Evidence.EDITOR,
            channel_id="",
            video_id="",
            source=YouTubeArtistLink.Source.EDITOR,
            checked_at=timezone.now(),
        )
        rebake_events_naming(keys)


admin.site.register(YouTubeArtistLink, YouTubeArtistLinkAdmin)


# artists and bands (add-artists-and-bands): admin-only records, imported by import_artists
# and filled in by enrich_artists_from_musicbrainz

MUSICBRAINZ_FIELDS = (
    "mb_type", "country", "area", "begin_date", "end_date", "genres", "wikidata_id", "discogs_url",
    "disambiguation",
)
WIKIPEDIA_FIELDS = ("wikipedia_extract", "wikipedia_url", "wikipedia_revision", "wikipedia_fetched_at")


class BandMembershipInline(admin.TabularInline):
    model = BandMembership
    extra = 0
    fields = ("artist", "role", "begin_year", "end_year", "source")
    readonly_fields = ("source",)
    autocomplete_fields = ("artist",)


class ArtistMembershipInline(BandMembershipInline):
    """the bands an artist is in, on the artist's page"""

    fields = ("band", "role", "begin_year", "end_year", "source")
    autocomplete_fields = ("band",)
    verbose_name = "band"
    verbose_name_plural = "bands"


class MusicActAdmin(admin.ModelAdmin):
    list_display = ("name", "city_town", "state", "musicbrainz_status", "musicbrainz_page", "act_id")
    list_filter = ("state", "musicbrainz_status")
    search_fields = ("name", "act_id", "musicbrainz_id")
    actions = ["clear_musicbrainz_match"]
    readonly_fields = (
        "musicbrainz_status", "musicbrainz_checked_at", "musicbrainz_page", "genres_from_musicbrainz",
        *[f for f in MUSICBRAINZ_FIELDS if f != "genres"], "field_sources", "introduction_from_wikipedia",
        "photo_preview",
    )
    fieldsets = (
        (None, {"fields": ("name", "slug", "act_id", "city_town", "state", "notes")}),
        ("Links", {"fields": ("website", "bandcamp_url", "instagram_url", "youtube_url")}),
        (
            "Photo (Wikimedia Commons, free licence only)",
            {
                "description": "set a commons file name and its credit to choose the photo by hand; enrichment keeps an editor's",
                "fields": ("photo_preview", "photo_file", "photo_author", "photo_license", "photo_license_url"),
            },
        ),
        (
            "MusicBrainz",
            {
                "description": "set the MusicBrainz id to choose the artist by hand; enrichment then looks it up and never replaces it",
                "fields": (
                    "musicbrainz_id", "musicbrainz_status", "musicbrainz_checked_at", "musicbrainz_page", "mb_type",
                    "disambiguation", "country", "area", "begin_date", "end_date", "genres_from_musicbrainz",
                    "wikidata_id", "discogs_url",
                ),
            },
        ),
        ("Introduction", {"fields": ("introduction_from_wikipedia",)}),
        ("Who set what", {"fields": ("field_sources",), "classes": ("collapse",)}),
    )

    @admin.display(description="MusicBrainz")
    def musicbrainz_page(self, act):
        if not act.musicbrainz_id:
            return "-"
        return format_html(
            '<a href="https://musicbrainz.org/artist/{}" target="_blank" rel="noopener">{}</a>',
            act.musicbrainz_id, act.musicbrainz_id,
        )

    @admin.display(description="genres")
    def genres_from_musicbrainz(self, act):
        # musicbrainz's genre tags are supplementary data, cc by-nc-sa: credited where shown
        if not act.genres:
            return "-"
        return format_html(
            '{} <span class="help">(genres from <a href="https://musicbrainz.org/doc/About/Data_License">MusicBrainz</a>, CC BY-NC-SA)</span>',
            ", ".join(act.genres),
        )

    @admin.display(description="photo")
    def photo_preview(self, act):
        # commons' own thumbnail, as the public page shows it, so a wrong photo is obvious
        if not act.photo_file:
            return "-"
        return format_html(
            '<img src="{}" alt="" width="240" style="max-width:100%;height:auto"><br>'
            '<a href="{}" target="_blank" rel="noopener">on Wikimedia Commons</a>',
            commons_thumbnail(act.photo_file, 480), commons_file_page(act.photo_file),
        )

    @admin.display(description="from Wikipedia")
    def introduction_from_wikipedia(self, act):
        # cc by-sa 4.0: shown word for word, with a link to the article and the licence
        if not act.wikipedia_extract:
            return "-"
        return format_html(
            '<p>{}</p><p class="help">From the Wikipedia article <a href="{}" target="_blank" rel="noopener">{}</a>, '
            'under <a href="{}" target="_blank" rel="noopener">CC BY-SA 4.0</a> (fetched {})</p>',
            act.wikipedia_extract, act.wikipedia_url, unquote(act.wikipedia_url.rsplit("/", 1)[-1]).replace("_", " "),
            LICENSE_URL, act.wikipedia_fetched_at.date() if act.wikipedia_fetched_at else "",
        )

    def save_model(self, request, act, form, change):
        """what an editor changes is theirs: the import leaves it, and a musicbrainz id they
        set is looked up by the next enrichment and never replaced"""
        for name in form.changed_data:
            act.field_sources[name] = "editor"
        if "musicbrainz_id" in form.changed_data:
            if act.musicbrainz_id:
                act.musicbrainz_status = MusicAct.MusicBrainzStatus.EDITOR
                act.musicbrainz_checked_at = None
            else:
                clear_musicbrainz(act)
        super().save_model(request, act, form, change)

    def save_formset(self, request, form, formset, change):
        # a membership added here is the editor's
        for membership in formset.save(commit=False):
            if membership.pk is None:
                membership.source = BandMembership.Source.EDITOR
            membership.save()
        for membership in formset.deleted_objects:
            membership.delete()

    @admin.action(description="Clear MusicBrainz match (the next enrichment searches again)")
    def clear_musicbrainz_match(self, request, queryset):
        for act in queryset:
            clear_musicbrainz(act)
            act.save()


def clear_musicbrainz(act):
    """forget the musicbrainz match and what it filled in, so the next run searches again"""
    act.musicbrainz_id = None
    act.musicbrainz_status = ""
    act.musicbrainz_checked_at = None
    for name in MUSICBRAINZ_FIELDS:
        setattr(act, name, [] if name == "genres" else "")
    # found through musicbrainz's wikidata link, so it goes with it
    for name in WIKIPEDIA_FIELDS:
        setattr(act, name, None if name == "wikipedia_fetched_at" else "")
    for name in ("website", "bandcamp_url", "instagram_url", "youtube_url"):
        if act.field_sources.get(name) in ("musicbrainz", "wikidata"):
            setattr(act, name, "")
    # the photo came through musicbrainz's wikidata link too, unless an editor chose it
    if act.field_sources.get("photo_file") != "editor":
        for name in ("photo_file", "photo_author", "photo_license", "photo_license_url"):
            setattr(act, name, "")
    act.field_sources = {
        k: v for k, v in act.field_sources.items() if v not in ("musicbrainz", "wikidata") and k != "musicbrainz_id"
    }


class ArtistAdmin(MusicActAdmin):
    inlines = [ArtistMembershipInline]


class BandAdmin(MusicActAdmin):
    inlines = [BandMembershipInline]


admin.site.register(Artist, ArtistAdmin)
admin.site.register(Band, BandAdmin)
