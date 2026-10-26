import re
from datetime import date

from dateutil import relativedelta
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.db.models import Q, URLField
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from ordered_model.admin import OrderedModelAdmin
from solo.admin import SingletonModelAdmin
from tinymce.widgets import TinyMCE

from .geo_filters import area_q, metro_fits_state, offered_areas, parse_geo_filter
from .job_runs import DIDNT_FINISH, STALE_AFTER, outcome
from .models import (
    AllEventProxy,
    DateMessage,
    EmailSubscriber,
    Event,
    GeoArea,
    IndexPageMessages,
    JobRun,
    MenuItem,
    StaticPage,
    Venue,
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
        area = getattr(parse_geo_filter(request.GET), self.parameter_name)
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


class EventAdmin(admin.ModelAdmin):
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
    )
    readonly_fields = ("user_submitted",)
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
    ]
    list_editable = ("same_time_order_override",)
    actions = ["mark_as_approved", "mark_as_live_music", "mark_as_not_music"]

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

    def lookups(self, request, model_admin):
        return (("yes", "Yes"), ("no", "No"))

    def queryset(self, request, queryset):
        linked = Q(ticketmaster_venue_id__isnull=False) & ~Q(ticketmaster_venue_id="")
        if self.value() == "yes":
            return queryset.filter(linked)
        if self.value() == "no":
            return queryset.exclude(linked)
        return queryset


class VenueAdmin(admin.ModelAdmin):
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
        "place_lookup_status",
        "place_business_status",
    )
    search_fields = (
        "name",
        "city_town",
        "county",
        "venue_type",
        "sheet_id",
        "ticketmaster_venue_id",
    )
    ordering = ("name",)
    save_on_top = True
    actions = [
        "mark_as_inactive",
        "mark_as_active",
        "mark_place_as_confident",
        "clear_place_lookup",
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
                    "place_looked_up_at",
                    "place_id",
                    "place_name",
                    "place_address",
                    "place_latitude",
                    "place_longitude",
                    "place_business_status",
                    "place_maps_url",
                    "place_website",
                    "place_phone",
                )
            },
        ),
        ("Event sources", {"fields": ("ticketmaster_venue_id",)}),
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
            venue.save()

    @admin.action(description="Clear place lookup")
    def clear_place_lookup(self, request, queryset):
        for venue in queryset:
            venue.place_lookup_status = ""
            venue.place_looked_up_at = None
            venue.place_id = venue.place_name = venue.place_address = ""
            venue.place_latitude = venue.place_longitude = None
            venue.place_business_status = venue.place_maps_url = ""
            venue.place_website = venue.place_phone = ""
            venue.save()


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
    list_display = ("command", "started_at", "duration", "outcome_label", "dry_run", "summary_text")
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

    @admin.display(description="error")
    def error_text(self, run):
        return format_html('<pre style="white-space: pre-wrap">{}</pre>', run.error) if run.error else "-"

    @admin.display(description="output")
    def output_text(self, run):
        return format_html('<pre style="white-space: pre-wrap">{}</pre>', run.output or "-")


admin.site.register(JobRun, JobRunAdmin)
