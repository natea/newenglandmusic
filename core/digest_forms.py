"""
reads and saves the choices form shared by the signup and preferences pages
(add-weekly-email-digest). the form has:

    area         any of "region:slug", "state:slug", "metro:slug", or "all"
    metro_town   "metro-slug|Town, ST": narrows that metro to these towns. no longer offered (the
                 town inputs cover it), but still read from a form opened before it went
    near_q       a zip code or town, with near_miles; near_pick is one of its candidates
    town         followed towns, "Town, ST", one input each
    venue        followed venues, "Name (Town, ST)" or just the name, one input each

    result = read_choices(request.POST)
    if result.ok: save_choices(subscriber, result.specs)
"""

import re
from dataclasses import dataclass, field
from urllib.parse import urlencode

from django.db.models import Q
from django.http import QueryDict

from core import location
from core.digest import ALL_AREAS, MAX_CHOICES, area_filter
from core.geo_filters import GeoFilter, metro_groups, offered_areas, parse_geo_filter, town_label
from core.models import DigestChoice, GeoArea, Venue

MILES = (5, 10, 25, 50, 100)
DEFAULT_MILES = 25
MAX_LABEL = 100
MAX_SUGGESTIONS = 8
MAX_TEXT = 200
BLANK_INPUTS = 2
KIND = DigestChoice.Kind


@dataclass
class ChoiceResult:
    specs: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    # places a typed town name could mean, to choose from
    candidates: list = field(default_factory=list)

    @property
    def ok(self):
        return not self.errors and not self.candidates


def public_venues():
    return Venue.objects.exclude(is_active=False)


def venue_label(venue):
    town = ", ".join(part for part in (venue.city_town, venue.state) if part)
    return f"{venue.name} ({town})" if town else venue.name


def area_options():
    """
    what the area select offers: [(value, label)] for regions, states and metros, only those in
    new england, as the listing offers (the site lists nothing elsewhere)
    """
    options = [
        (f"{area.kind}:{area.slug}", area.label)
        for kind in ("region", "state")
        for area in offered_areas(kind, new_england_only=True)
    ]
    options += [(f"metro:{area.slug}", area.label) for _, metros in metro_groups() for area in metros]
    return options


def area_query_for(kind, slug, towns=()):
    """the canonical GeoFilter query string for one area (and some of a metro's towns), or None"""
    if kind not in ("region", "state", "metro") or not slug:
        return None
    query = QueryDict(mutable=True)
    query[kind] = slug
    if kind == "metro":
        query.setlist("town", list(towns))
    geo_filter = parse_geo_filter(query, new_england_only=True)
    # an unknown area, or a town that isn't the metro's, is dropped by the parse: refuse it
    if not geo_filter or geo_filter.query_string != urlencode(
        [(kind, slug)] + ([("town", town) for town in towns] if kind == "metro" else [])
    ):
        return None
    return geo_filter.query_string


def read_areas(data, result):
    towns_by_metro = {}
    for value in data.getlist("metro_town"):
        slug, _, town = value.partition("|")
        if slug and town:
            towns_by_metro.setdefault(slug, []).append(town)
    seen = set()
    wanted = [value for value in data.getlist("area") if value]
    if "all" in wanted:
        result.specs.append({"kind": KIND.AREA, "area_query": ALL_AREAS})
    pairs = [tuple(value.split(":", 1)) for value in wanted if ":" in value]
    pairs += [("metro", slug) for slug in towns_by_metro]
    for kind, slug in pairs:
        if (kind, slug) in seen:
            continue
        seen.add((kind, slug))
        query = area_query_for(kind, slug, towns_by_metro.get(slug, ()) if kind == "metro" else ())
        if query is None:
            result.errors.append("One of the areas you chose isn't offered. Choose it again from the list.")
        else:
            result.specs.append({"kind": KIND.AREA, "area_query": query})
    unattached = [value for value in wanted if value != "all" and ":" not in value]
    if unattached:
        result.errors.append("One of the areas you chose isn't offered. Choose it again from the list.")


def read_near(data, result):
    text = (data.get("near_pick") or data.get("near_q") or "").strip()
    if not text:
        return
    try:
        miles = int(data.get("near_miles") or DEFAULT_MILES)
    except ValueError:
        miles = None
    if miles not in MILES:
        result.errors.append("Choose how far from the place: " + ", ".join(map(str, MILES)) + " miles.")
        return
    found = location.resolve(text[:MAX_TEXT])
    if found is None:
        result.errors.append(f"We couldn't find “{text[:MAX_LABEL]}”. Try a ZIP code, or a town such as “Somerville, MA”.")
    elif isinstance(found, list):
        result.candidates.append((text[:MAX_LABEL], [place.label for place in found]))
    else:
        # the lookup's point is rounded already: nothing finer than that is kept
        result.specs.append(
            {"kind": KIND.NEAR, "label": found.label[:MAX_LABEL], "latitude": found.latitude, "longitude": found.longitude, "miles": miles}
        )


def read_towns(data, result):
    known = {}
    for town, state in public_venues().exclude(city_town="").values_list("city_town", "state"):
        known.setdefault((town.strip().casefold(), state), town.strip())
    seen = set()
    for text in (value.strip() for value in data.getlist("town")):
        if not text:
            continue
        name, _, state = text[:MAX_TEXT].rpartition(",")
        code = location.state_code(state) if name else None
        if code and (name.strip().casefold(), code) in known:
            key = (name.strip().casefold(), code)
            if key not in seen:
                seen.add(key)
                result.specs.append({"kind": KIND.TOWN, "town": known[key], "state": code, "label": town_label(known[key], code)})
            continue
        if not name:
            same = sorted({town_label(t, s) for (k, s), t in known.items() if k == text.casefold()})
            if len(same) > 1:
                result.candidates.append((text[:MAX_LABEL], same))
                continue
            if same:
                town, _, code = same[0].rpartition(", ")
                if (town.casefold(), code) not in seen:
                    seen.add((town.casefold(), code))
                    result.specs.append({"kind": KIND.TOWN, "town": town, "state": code, "label": same[0]})
                continue
        result.errors.append(f"We don't list a town called “{text[:MAX_LABEL]}”. Try “Somerville, MA”.")


LABEL = re.compile(r"^(?P<name>.+?)\s*\((?P<town>[^()]*)\)\s*$")


def read_venues(data, result):
    seen = set()
    for text in (value.strip() for value in data.getlist("venue")):
        if not text:
            continue
        text = text[:MAX_TEXT]
        matches = public_venues().filter(name__iexact=text)
        labelled = LABEL.match(text)
        if not matches and labelled:
            town, _, state = labelled["town"].rpartition(",")
            matches = public_venues().filter(
                name__iexact=labelled["name"], city_town__iexact=town.strip(), state=location.state_code(state) or ""
            )
        if len(matches) > 1:
            result.candidates.append((text[:MAX_LABEL], [venue_label(venue) for venue in matches]))
        elif not matches:
            result.errors.append(f"We don't list a venue called “{text[:MAX_LABEL]}”.")
        elif matches[0].pk not in seen:
            seen.add(matches[0].pk)
            result.specs.append({"kind": KIND.VENUE, "venue": matches[0], "label": matches[0].name[:MAX_LABEL]})


def read_choices(data):
    """the choices in a submitted form, with what's wrong with it and the places to choose from"""
    result = ChoiceResult()
    read_areas(data, result)
    read_near(data, result)
    read_towns(data, result)
    read_venues(data, result)
    if result.ok and not result.specs:
        result.errors.append("Choose at least one: an area, a place to be near, or a town or venue to follow.")
    if len(result.specs) > MAX_CHOICES:
        result.errors.append(f"Choose at most {MAX_CHOICES} things. You chose {len(result.specs)}.")
    return result


def save_choices(subscriber, specs):
    """replaces the subscriber's choices with specs"""
    subscriber.choices.all().delete()
    DigestChoice.objects.bulk_create([DigestChoice(subscriber=subscriber, **spec) for spec in specs])


def initial_from_filter(geo_filter):
    """
    (area boxes ticked, towns filled in) from a remembered listing filter: a metro narrowed to
    towns fills in those towns, as the form's town inputs; neighborhoods are dropped (not offered)
    """
    if geo_filter.metro and geo_filter.towns:
        return set(), geo_filter.town_labels
    if geo_filter.metro:
        # a metro is narrower than the state or region it sits in
        return {f"metro:{geo_filter.metro.slug}"}, []
    if geo_filter.state:
        return {f"state:{geo_filter.state.slug}"}, []
    if geo_filter.region:
        return {f"region:{geo_filter.region.slug}"}, []
    return set(), []


def form_context(*, ticked=(), near_label="", near_miles=DEFAULT_MILES, towns=(), venues=()):
    """what the template needs to draw the form, with these things ticked or filled in"""
    return {
        "area_options": area_options(),
        "ticked": set(ticked),
        # blank on a fresh form; the dev settings would otherwise print a missing-variable marker
        "email": "",
        "near_label": near_label,
        "near_miles": near_miles,
        "miles_options": MILES,
        "towns": list(towns) + [""] * BLANK_INPUTS,
        "venues": list(venues) + [""] * BLANK_INPUTS,
    }


def context_from_post(data):
    return form_context(
        ticked=set(data.getlist("area")),
        near_label=(data.get("near_pick") or data.get("near_q") or "").strip()[:MAX_LABEL],
        near_miles=_int(data.get("near_miles"), DEFAULT_MILES),
        towns=[v.strip() for v in data.getlist("town") if v.strip()],
        venues=[v.strip() for v in data.getlist("venue") if v.strip()],
    )


def _int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def context_from_choices(subscriber):
    """the form as the subscriber's stored choices fill it in"""
    ticked, near, towns, venues = set(), None, [], []
    for choice in subscriber.choices.select_related("venue"):
        if choice.kind == KIND.AREA and choice.area_query == ALL_AREAS:
            ticked.add("all")
        elif choice.kind == KIND.AREA:
            geo_filter = area_filter(choice)
            if geo_filter and geo_filter.towns:
                # a metro narrowed to towns (saved before the form offered only town inputs) shows
                # as those towns, which select the same shows
                towns += geo_filter.town_labels
            elif geo_filter:
                for area in geo_filter.areas:
                    ticked.add(f"{area.kind}:{area.slug}")
        elif choice.kind == KIND.NEAR:
            near = choice
        elif choice.kind == KIND.TOWN:
            towns.append(town_label(choice.town, choice.state))
        elif choice.kind == KIND.VENUE and choice.venue:
            venues.append(venue_label(choice.venue))
    return form_context(
        ticked=ticked,
        near_label=near.label if near else "",
        near_miles=near.miles if near else DEFAULT_MILES,
        towns=towns,
        venues=venues,
    )
