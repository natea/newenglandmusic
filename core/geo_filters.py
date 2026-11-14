"""
filters venues and events by the regions, states and metro areas of core/geo_areas.py
(loaded into GeoArea on every migrate).

a venue belongs to an area when its state is in the area's states and, if the area lists
counties or cities, its county or its city is one of them; massachusetts's sub-regions have
their own rules (sub_region_q), which put each venue in exactly one:

    Event.objects.filter(area_q(area, prefix="venue__"))

the listing pages and the admin both take the same url parameters:

    /?region=new-england&state=massachusetts&metro=ma-north-of-the-charles

a metro can be narrowed to some of its towns, by the venues' own town and state (not the
sheet's metro city lists, so this keeps working if the areas move out of the sheet):

    /?metro=ma-north-of-the-charles&town=Somerville, MA&town=Cambridge, MA
"""

from dataclasses import dataclass, field
from urllib.parse import urlencode

from django.db.models import Q
from django.http import QueryDict

from core.geo_areas import OLD_METRO_SLUGS
from core.models import GeoArea

FILTER_PARAMS = ("region", "state", "metro")

# the states whose venues' events the public site lists, and whose areas it offers; widen
# the site's scope by changing this list alone
NEW_ENGLAND_STATES = ["MA", "CT", "RI", "NH", "ME", "VT"]


def new_england_q(prefix=""):
    """the events (or venues, with no prefix) in New England; no venue, or no state, is out"""
    return Q(**{f"{prefix}state__in": NEW_ENGLAND_STATES})


def any_iexact(field, values):
    """the field is one of values, whatever its case (venues' spelling and case vary)"""
    q = Q(pk__in=[])
    for value in values:
        q |= Q(**{f"{field}__iexact": value})
    return q


def area_q(area, prefix=""):
    q = Q(**{f"{prefix}state__in": [state.upper() for state in area.states]})
    if area.group:
        return q & sub_region_q(area, prefix)
    if not area.counties and not area.cities:
        return q
    return q & (any_iexact(f"{prefix}county", area.counties) | any_iexact(f"{prefix}city_town", area.cities))


def boston_neighborhood_q(neighborhoods, prefix=""):
    return Q(**{f"{prefix}city_town__iexact": "boston"}) & any_iexact(f"{prefix}neighborhood", neighborhoods)


def sub_region_q(area, prefix=""):
    """
    a massachusetts sub-region (core/geo_areas.py) holds the venues in its towns, the boston
    venues in its neighborhoods, and, in its default counties, the venues no sub-region's town
    or neighborhood placed, so each venue is in exactly one sub-region
    """
    q = any_iexact(f"{prefix}city_town", area.cities) | boston_neighborhood_q(area.neighborhoods, prefix)
    if not area.default_counties:
        return q
    sub_regions = GeoArea.objects.exclude(group="")
    all_towns = [town for towns in sub_regions.values_list("cities", flat=True) for town in towns]
    all_neighborhoods = [name for names in sub_regions.values_list("neighborhoods", flat=True) for name in names]
    placed = any_iexact(f"{prefix}city_town", all_towns) | boston_neighborhood_q(all_neighborhoods, prefix)
    return q | (any_iexact(f"{prefix}county", area.default_counties) & ~placed)


def offered_areas(kind, new_england_only=False):
    # an area with no states can't match anything (e.g. "Northeast Corridor"
    # before the sheet gives it states), so it isn't worth offering
    areas = GeoArea.objects.filter(kind=kind).exclude(states=[])
    if not new_england_only:
        return areas
    # the site offers only areas wholly inside New England; the sheet stores states lowercase
    allowed = {state.lower() for state in NEW_ENGLAND_STATES}
    return [area for area in areas if {state.lower() for state in area.states} <= allowed]


@dataclass
class GeoFilter:
    region: GeoArea | None = None
    state: GeoArea | None = None
    metro: GeoArea | None = None
    # (town, state code) pairs within the metro, in the venues' own spelling
    towns: list = field(default_factory=list)
    # (neighborhood, town, state code) within the chosen towns (lookup_venue_neighborhoods)
    neighborhoods: list = field(default_factory=list)
    # the towns whose neighborhoods are offered: the chosen ones, or a one-town metro's town
    neighborhood_towns: list = field(default_factory=list)

    @property
    def areas(self):
        return [area for area in (self.region, self.state, self.metro) if area]

    def __bool__(self):
        return bool(self.areas)

    def q(self, prefix=""):
        q = Q()
        for area in self.areas:
            q &= area_q(area, prefix=prefix)
        if self.towns:
            towns_q = Q()
            for town, state in self.towns:
                towns_q |= Q(**{f"{prefix}city_town__iexact": town, f"{prefix}state": state})
            q &= towns_q
        if self.neighborhoods:
            neighborhoods_q = Q()
            for neighborhood, town, state in self.neighborhoods:
                neighborhoods_q |= Q(
                    **{
                        f"{prefix}neighborhood__iexact": neighborhood,
                        f"{prefix}city_town__iexact": town,
                        f"{prefix}state": state,
                    }
                )
            q &= neighborhoods_q
        return q

    @property
    def neighborhood_labels(self):
        return [neighborhood_label(*triple) for triple in self.neighborhoods]

    @property
    def town_labels(self):
        return [town_label(town, state) for town, state in self.towns]

    @property
    def query_string(self):
        return urlencode(
            [(param, getattr(self, param).slug) for param in FILTER_PARAMS if getattr(self, param)]
            + [("town", label) for label in self.town_labels]
            + [("neighborhood", label) for label in self.neighborhood_labels]
        )


def town_label(town, state):
    return f"{town}, {state}"


def metro_towns(metro):
    """the (town, state) of the metro's venues, one per town whatever its case, sorted"""
    from core.models import Venue

    towns = {}
    rows = Venue.objects.filter(area_q(metro)).exclude(city_town="").values_list("city_town", "state")
    for town, state in rows:
        key, spelling = (town.strip().casefold(), state), town.strip()
        # the sheet sometimes has "cambridge" beside "Cambridge": show the capitalized one
        if key not in towns or (spelling[:1].isupper() and not towns[key][0][:1].isupper()):
            towns[key] = (spelling, state)
    return sorted(towns.values(), key=lambda pair: (pair[0].casefold(), pair[1]))


def neighborhood_label(neighborhood, town, state):
    return f"{neighborhood}, {town}, {state}"


def town_neighborhoods(towns, metro=None):
    """
    the (neighborhood, town, state) of the venues in these (town, state) pairs, sorted; only
    the metro's venues, when one is given, since boston is split among several sub-regions
    """
    from core.models import Venue

    if not towns:
        return []
    towns_q = Q()
    for town, state in towns:
        towns_q |= Q(city_town__iexact=town, state=state)
    found = {}
    venues = Venue.objects.filter(towns_q)
    if metro:
        venues = venues.filter(area_q(metro))
    rows = venues.exclude(neighborhood="").values_list("neighborhood", "city_town", "state")
    spelling = {(t.casefold(), s): t for t, s in towns}
    for neighborhood, town, state in rows:
        town = spelling.get((town.strip().casefold(), state), town.strip())
        found.setdefault((neighborhood.casefold(), town.casefold(), state), (neighborhood, town, state))
    return sorted(found.values(), key=lambda triple: (triple[0].casefold(), triple[1].casefold()))


def metro_fits_state(metro, state):
    return state is None or metro.home_state == state.home_state


def parse_geo_filter(querydict, new_england_only=False):
    """
    resolves the region, state and metro slugs in querydict to offered areas.
    unknown slugs are dropped, as is a metro from a different state than the
    chosen one, so a stale or hand-edited url just filters less. new_england_only is the
    site's view: an area outside New England is unknown to it, though the admin resolves it.
    """
    geo_filter = GeoFilter()
    for param in FILTER_PARAMS:
        slug = querydict.get(param, "").strip()
        if slug:
            areas = offered_areas(param, new_england_only)
            setattr(geo_filter, param, next((area for area in areas if area.slug == slug), None))
    old_metro = querydict.get("metro", "").strip() in OLD_METRO_SLUGS
    if old_metro and not geo_filter.metro and not geo_filter.state:
        # a link, cookie or feed from before massachusetts's sub-regions covers the whole state
        states = offered_areas(GeoArea.Kind.STATE, new_england_only)
        geo_filter.state = next((area for area in states if area.home_state == "MA"), None)
    if geo_filter.metro and not metro_fits_state(geo_filter.metro, geo_filter.state):
        geo_filter.metro = None
    towns = metro_towns(geo_filter.metro) if geo_filter.metro else []
    wanted = [value.strip() for value in querydict.getlist("town") if value.strip()] if hasattr(querydict, "getlist") else []
    if len(towns) > 1 and wanted:
        # only the metro's own towns: a town from elsewhere, or a metro that changed, drops it
        known = {town_label(town, state).casefold(): (town, state) for town, state in towns}
        geo_filter.towns = [known[label.casefold()] for label in dict.fromkeys(wanted) if label.casefold() in known]
    # a metro with one town (downtown & central boston is all boston) offers no town filter, so
    # its neighborhoods come straight after it
    geo_filter.neighborhood_towns = geo_filter.towns or (towns if len(towns) == 1 else [])
    wanted = [value.strip() for value in querydict.getlist("neighborhood") if value.strip()] if hasattr(querydict, "getlist") else []
    if geo_filter.neighborhood_towns and wanted:
        # only those towns' neighborhoods: one from another town, or a town dropped, drops it
        known = {
            neighborhood_label(*triple).casefold(): triple
            for triple in town_neighborhoods(geo_filter.neighborhood_towns, geo_filter.metro)
        }
        geo_filter.neighborhoods = [known[label.casefold()] for label in dict.fromkeys(wanted) if label.casefold() in known]
    return geo_filter


# the visitor's last filter, so a return visit opens on the same area
COOKIE_NAME = "geo_filter"
COOKIE_MAX_AGE = 365 * 24 * 60 * 60


class CookieAction:
    SET = "set"
    CLEAR = "clear"
    REDIRECT = "redirect"


def geo_filter_for_request(request):
    """
    works out the listing's filter and what to do with the cookie, as
    (geo_filter, cookie_action) where cookie_action is a CookieAction or None.

    the url always wins: a page with no filter in it redirects to the
    remembered one (REDIRECT) instead of filtering silently, so the address
    bar, and any link copied from it, shows what's being filtered.
    """
    params = request.GET
    given = [param for param in (*FILTER_PARAMS, "town", "neighborhood") if param in params]
    # "clear" is the show-all link; all-empty values are the form set to "All"
    if "clear" in params or (given and not any(params[param].strip() for param in given)):
        return GeoFilter(), CookieAction.CLEAR
    if given:
        geo_filter = parse_geo_filter(params, new_england_only=True)
        return geo_filter, CookieAction.SET if geo_filter else None

    cookie = request.COOKIES.get(COOKIE_NAME)
    if not cookie:
        return GeoFilter(), None
    geo_filter = parse_geo_filter(QueryDict(cookie), new_england_only=True)
    # a cookie naming only areas that are gone from the sheet is just stale
    return geo_filter, CookieAction.REDIRECT if geo_filter else CookieAction.CLEAR


def apply_cookie_action(request, response, geo_filter, cookie_action):
    if cookie_action == CookieAction.SET:
        response.set_cookie(
            COOKIE_NAME,
            geo_filter.query_string,
            max_age=COOKIE_MAX_AGE,
            samesite="Lax",
            httponly=True,
            secure=request.is_secure(),
        )
    elif cookie_action == CookieAction.CLEAR and COOKIE_NAME in request.COOKIES:
        response.delete_cookie(COOKIE_NAME, samesite="Lax")
    return response


def metro_groups(state=None):
    """
    offered metros as [(heading, [metros])], in the areas' order, for <optgroup>s: grouped by
    state, except massachusetts's sub-regions, which are grouped by their own groups
    """
    state_labels = {area.home_state: area.label for area in offered_areas(GeoArea.Kind.STATE, new_england_only=True)}
    groups = {}
    for metro in offered_areas(GeoArea.Kind.METRO, new_england_only=True):
        if metro_fits_state(metro, state):
            heading = metro.group or state_labels.get(metro.home_state, metro.home_state)
            groups.setdefault(heading, []).append(metro)
    return list(groups.items())


def metro_town_options(metro):
    """the town filter's options: none for a metro with one town, which there's no narrowing"""
    towns = metro_towns(metro) if metro else []
    return [town_label(town, state) for town, state in towns] if len(towns) > 1 else []


def geo_filter_context(geo_filter):
    """
    what core/geo_filter_form.html needs, for the listing and the discovery deck alike: the
    state options, the metros of the chosen state, and the chosen metro's towns
    and the chosen towns' neighborhoods
    """
    return {
        "geo_filter": geo_filter,
        # the site lists new england only, so it offers only new england's areas; no regions,
        # which are few, so a state is simpler to pick
        "state_options": offered_areas(GeoArea.Kind.STATE, new_england_only=True),
        "metro_groups": metro_groups(geo_filter.state),
        "metro_towns": metro_town_options(geo_filter.metro),
        "town_neighborhoods": [
            neighborhood_label(*triple) for triple in town_neighborhoods(geo_filter.neighborhood_towns, geo_filter.metro)
        ],
    }
