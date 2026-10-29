"""
filters venues and events by the regions, states and metro areas of the venue
sheet's geo-filters_json tab (synced into GeoArea by sync_venues_from_gsheets).

a venue belongs to an area when its state is in the area's states and, if the
area lists counties or cities, its county or its city is one of them:

    Event.objects.filter(area_q(area, prefix="venue__"))

the listing pages and the admin both take the same url parameters:

    /?region=new-england&state=massachusetts&metro=ma-boston-metro-region

a metro can be narrowed to some of its towns, by the venues' own town and state (not the
sheet's metro city lists, so this keeps working if the areas move out of the sheet):

    /?metro=ma-boston-metro-region&town=Somerville, MA&town=Cambridge, MA
"""

from dataclasses import dataclass, field
from urllib.parse import urlencode

from django.db.models import Q
from django.http import QueryDict

from core.models import GeoArea

FILTER_PARAMS = ("region", "state", "metro")


def area_q(area, prefix=""):
    q = Q(**{f"{prefix}state__in": [state.upper() for state in area.states]})
    if not area.counties and not area.cities:
        return q
    # the sheet's spelling and case vary, so compare each value case-insensitively
    place_q = Q()
    for county in area.counties:
        place_q |= Q(**{f"{prefix}county__iexact": county})
    for city in area.cities:
        place_q |= Q(**{f"{prefix}city_town__iexact": city})
    return q & place_q


def offered_areas(kind):
    # an area with no states can't match anything (e.g. "Northeast Corridor"
    # before the sheet gives it states), so it isn't worth offering
    return GeoArea.objects.filter(kind=kind).exclude(states=[])


@dataclass
class GeoFilter:
    region: GeoArea | None = None
    state: GeoArea | None = None
    metro: GeoArea | None = None
    # (town, state code) pairs within the metro, in the venues' own spelling
    towns: list = field(default_factory=list)
    # (neighborhood, town, state code) within the chosen towns (lookup_venue_neighborhoods)
    neighborhoods: list = field(default_factory=list)

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


def town_neighborhoods(towns):
    """the (neighborhood, town, state) of the venues in these (town, state) pairs, sorted"""
    from core.models import Venue

    if not towns:
        return []
    towns_q = Q()
    for town, state in towns:
        towns_q |= Q(city_town__iexact=town, state=state)
    found = {}
    rows = Venue.objects.filter(towns_q).exclude(neighborhood="").values_list("neighborhood", "city_town", "state")
    spelling = {(t.casefold(), s): t for t, s in towns}
    for neighborhood, town, state in rows:
        town = spelling.get((town.strip().casefold(), state), town.strip())
        found.setdefault((neighborhood.casefold(), town.casefold(), state), (neighborhood, town, state))
    return sorted(found.values(), key=lambda triple: (triple[0].casefold(), triple[1].casefold()))


def metro_fits_state(metro, state):
    return state is None or metro.home_state == state.home_state


def parse_geo_filter(querydict):
    """
    resolves the region, state and metro slugs in querydict to offered areas.
    unknown slugs are dropped, as is a metro from a different state than the
    chosen one, so a stale or hand-edited url just filters less.
    """
    geo_filter = GeoFilter()
    for param in FILTER_PARAMS:
        slug = querydict.get(param, "").strip()
        if slug:
            setattr(geo_filter, param, offered_areas(param).filter(slug=slug).first())
    if geo_filter.metro and not metro_fits_state(geo_filter.metro, geo_filter.state):
        geo_filter.metro = None
    wanted = [value.strip() for value in querydict.getlist("town") if value.strip()] if hasattr(querydict, "getlist") else []
    if geo_filter.metro and wanted:
        # only the metro's own towns: a town from elsewhere, or a metro that changed, drops it
        known = {town_label(town, state).casefold(): (town, state) for town, state in metro_towns(geo_filter.metro)}
        geo_filter.towns = [known[label.casefold()] for label in dict.fromkeys(wanted) if label.casefold() in known]
    wanted = [value.strip() for value in querydict.getlist("neighborhood") if value.strip()] if hasattr(querydict, "getlist") else []
    if geo_filter.towns and wanted:
        # only the chosen towns' neighborhoods: one from another town, or a town dropped, drops it
        known = {neighborhood_label(*triple).casefold(): triple for triple in town_neighborhoods(geo_filter.towns)}
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
        geo_filter = parse_geo_filter(params)
        return geo_filter, CookieAction.SET if geo_filter else None

    cookie = request.COOKIES.get(COOKIE_NAME)
    if not cookie:
        return GeoFilter(), None
    geo_filter = parse_geo_filter(QueryDict(cookie))
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
    """offered metros as [(state label, [metros])], in sheet order, for <optgroup>s"""
    state_labels = {area.home_state: area.label for area in offered_areas(GeoArea.Kind.STATE)}
    groups = {}
    for metro in offered_areas(GeoArea.Kind.METRO):
        if metro_fits_state(metro, state):
            groups.setdefault(metro.home_state, []).append(metro)
    return [
        (state_labels.get(home_state, home_state), metros) for home_state, metros in groups.items()
    ]
