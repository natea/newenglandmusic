"""
every region, state and metro area the location filter offers, in display order. a migrate
makes GeoArea match this file (core/geo_area_sync.py), so an area is changed by editing it here
and deploying; nothing else loads areas.

each area's key is stored in GeoArea.sheet_id (the keys the venue sheet gave them, kept so
nothing else moves). its matching lists are lowercase, and venues are compared to them
case-insensitively (core/geo_filters.py):

- states: the venue's state must be one of them;
- counties, cities: if either is set, the venue's county or town must be in one;
- massachusetts's sub-regions instead place each venue in exactly one of them: by its town in
  cities, by boston plus its neighborhood in neighborhoods, or else by its county's default.

the regions, states and other states' metros are copied as they were from the sheet; the
massachusetts sub-regions are the editors' list (add-massachusetts-regions).
"""


def area(kind, key, label, home_state, states, counties=(), cities=(), group="", neighborhoods=(), default_counties=()):
    return {
        "key": key,
        "kind": kind,
        "label": label,
        "home_state": home_state,
        "group": group,
        "states": list(states),
        "counties": list(counties),
        "cities": list(cities),
        "neighborhoods": list(neighborhoods),
        "default_counties": list(default_counties),
    }


def metro(*args, **kwargs):
    return area("metro", *args, **kwargs)


def region(*args, **kwargs):
    return area("region", *args, **kwargs)


def state(*args, **kwargs):
    return area("state", *args, **kwargs)


def sub_region(key, group, name, towns, neighborhoods=(), default_counties=()):
    """a massachusetts sub-region, labelled "MA: <name>" so its url value is ma-<name>"""
    return metro(
        key, f"MA: {name}", "MA", ["ma"], cities=towns, group=group, neighborhoods=neighborhoods,
        default_counties=default_counties,
    )


WESTERN = "Western Massachusetts"
CENTRAL = "Central Massachusetts"
METROWEST = "MetroWest"
GREATER_BOSTON = "Greater Boston"
NORTHEAST = "Northeast Massachusetts"
SOUTHEAST = "South of Boston & Southeast"
CAPE_AND_ISLANDS = "Cape Cod & the Islands"

# where a name the editors wrote with an alternative ("Allston-Brighton", "Barnstable/Hyannis")
# is split, both names are listed; boston neighborhoods that venues give as their town (as
# "Allston", not "Boston") are listed as towns as well as neighborhoods
MASSACHUSETTS = [
    # western massachusetts
    sub_region(
        "metro_MA_The_Berkshires", WESTERN, "The Berkshires",
        ["pittsfield", "north adams", "williamstown", "lenox", "stockbridge", "great barrington", "lee", "adams"],
        default_counties=["berkshire"],
    ),
    sub_region(
        "metro_MA_The_Hilltowns", WESTERN, "The Hilltowns",
        # shelburne falls is a village of shelburne (and buckland), and venues give it as their town
        ["chesterfield", "cummington", "worthington", "huntington", "blandford", "shelburne", "shelburne falls",
         "ashfield"],
    ),
    sub_region(
        "metro_MA_Pioneer_Valley", WESTERN, "Pioneer Valley / Connecticut River Valley",
        # florence is a village of northampton
        ["springfield", "holyoke", "chicopee", "northampton", "florence", "amherst", "easthampton", "greenfield",
         "deerfield"],
        default_counties=["franklin", "hampshire", "hampden"],
    ),
    sub_region(
        "metro_MA_Quabbin", WESTERN, "Quabbin / Swift River Valley",
        ["belchertown", "ware", "pelham", "shutesbury", "new salem", "petersham", "hardwick"],
    ),
    # central massachusetts
    sub_region(
        "metro_MA_Greater_Worcester", CENTRAL, "Greater Worcester",
        ["worcester", "shrewsbury", "holden", "auburn", "westborough", "boylston", "paxton", "leicester"],
        default_counties=["worcester"],
    ),
    sub_region(
        "metro_MA_Montachusett", CENTRAL, "Montachusett / North County",
        ["fitchburg", "leominster", "gardner", "lunenburg", "westminster", "ashburnham", "winchendon", "athol"],
    ),
    sub_region(
        "metro_MA_Blackstone_Valley", CENTRAL, "Blackstone Valley",
        ["millbury", "grafton", "sutton", "northbridge", "uxbridge", "douglas", "blackstone", "mendon"],
    ),
    sub_region(
        "metro_MA_South_County", CENTRAL, "South County / Sturbridge Area",
        ["sturbridge", "southbridge", "webster", "charlton", "oxford", "dudley", "brookfield"],
    ),
    # metrowest
    sub_region(
        "metro_MA_MetroWest", METROWEST, "MetroWest",
        ["framingham", "natick", "marlborough", "sudbury", "wayland", "wellesley", "weston", "ashland", "hopkinton",
         "holliston"],
        default_counties=["middlesex"],
    ),
    sub_region(
        "metro_MA_Nashoba_Valley", METROWEST, "Nashoba Valley",
        ["concord", "acton", "maynard", "stow", "littleton", "boxborough", "harvard", "groton", "pepperell", "ayer"],
    ),
    # greater boston: boston's venues give boston as their town with a neighborhood
    # (lookup_venue_neighborhoods), or give the neighborhood itself as their town
    sub_region(
        "metro_MA_Downtown_Central_Boston", GREATER_BOSTON, "Downtown & Central Boston",
        [],
        # openstreetmap's names beside the editors': fenway-kenmore, downtown crossing
        ["back bay", "beacon hill", "south end", "north end", "fenway", "fenway-kenmore", "downtown",
         "downtown crossing", "west end"],
        # a boston venue with no neighborhood, or one no sub-region lists
        default_counties=["suffolk"],
    ),
    sub_region(
        "metro_MA_East_Boston_Charlestown_South_Boston", GREATER_BOSTON, "East Boston, Charlestown & South Boston",
        ["east boston", "charlestown", "south boston"],
        ["east boston", "charlestown", "south boston", "seaport"],
    ),
    sub_region(
        "metro_MA_Boston_Neighborhoods", GREATER_BOSTON, "Boston Neighborhoods",
        ["jamaica plain", "dorchester", "roxbury", "allston", "brighton", "roslindale", "west roxbury", "hyde park",
         "mattapan"],
        ["jamaica plain", "dorchester", "roxbury", "allston", "brighton", "roslindale", "west roxbury", "hyde park",
         "mattapan"],
    ),
    sub_region(
        "metro_MA_North_of_the_Charles", GREATER_BOSTON, "North of the Charles",
        ["cambridge", "somerville", "medford", "malden", "everett", "chelsea", "revere", "winthrop"],
    ),
    sub_region(
        "metro_MA_Inner_West_Suburbs", GREATER_BOSTON, "Inner West Suburbs",
        ["brookline", "newton", "watertown", "arlington", "belmont", "waltham"],
    ),
    # northeast massachusetts
    sub_region(
        "metro_MA_North_Shore", NORTHEAST, "North Shore",
        ["salem", "beverly", "marblehead", "swampscott", "lynn", "peabody", "danvers", "ipswich", "newburyport",
         "amesbury"],
        default_counties=["essex"],
    ),
    sub_region(
        "metro_MA_Cape_Ann", NORTHEAST, "Cape Ann",
        ["gloucester", "rockport", "manchester-by-the-sea", "manchester", "essex"],
    ),
    sub_region(
        "metro_MA_Merrimack_Valley", NORTHEAST, "Merrimack Valley / Greater Lowell",
        ["lowell", "lawrence", "haverhill", "methuen", "andover", "north andover", "chelmsford", "billerica",
         "tewksbury"],
    ),
    # south of boston and the southeast
    sub_region(
        "metro_MA_South_Shore", SOUTHEAST, "South Shore",
        ["quincy", "braintree", "weymouth", "hingham", "cohasset", "scituate", "marshfield", "duxbury", "kingston",
         "plymouth"],
        default_counties=["plymouth"],
    ),
    sub_region(
        "metro_MA_Metro_South", SOUTHEAST, "Metro South / Greater Brockton",
        ["brockton", "bridgewater", "easton", "stoughton", "canton", "sharon", "mansfield", "foxborough", "taunton",
         "raynham"],
        default_counties=["norfolk"],
    ),
    sub_region(
        "metro_MA_South_Coast", SOUTHEAST, "South Coast",
        ["new bedford", "fall river", "dartmouth", "fairhaven", "westport", "mattapoisett", "marion", "wareham"],
        default_counties=["bristol"],
    ),
    # cape cod and the islands
    sub_region(
        "metro_MA_Upper_Cape", CAPE_AND_ISLANDS, "Upper Cape",
        ["bourne", "sandwich", "falmouth", "mashpee"],
    ),
    sub_region(
        "metro_MA_Mid-Cape", CAPE_AND_ISLANDS, "Mid-Cape",
        ["barnstable", "hyannis", "yarmouth", "dennis"],
        default_counties=["barnstable"],
    ),
    sub_region(
        "metro_MA_Lower_Cape", CAPE_AND_ISLANDS, "Lower Cape",
        ["harwich", "brewster", "chatham", "orleans"],
    ),
    sub_region(
        "metro_MA_Outer_Cape", CAPE_AND_ISLANDS, "Outer Cape",
        ["eastham", "wellfleet", "truro", "provincetown"],
    ),
    sub_region(
        "metro_MA_Marthas_Vineyard", CAPE_AND_ISLANDS, "Martha's Vineyard",
        ["edgartown", "oak bluffs", "tisbury", "vineyard haven", "west tisbury", "chilmark", "aquinnah"],
        default_counties=["dukes"],
    ),
    sub_region(
        "metro_MA_Nantucket", CAPE_AND_ISLANDS, "Nantucket",
        ["nantucket", "siasconset", "madaket"],
        default_counties=["nantucket"],
    ),
    sub_region(
        "metro_MA_Elizabeth_Islands", CAPE_AND_ISLANDS, "Elizabeth Islands",
        ["gosnold", "cuttyhunk"],
    ),
]

# the url values of the metros massachusetts had before its sub-regions; saved filters, links
# and subscribed calendar feeds that name one cover all of massachusetts instead. ma-north-shore
# isn't here: the new north shore has the same address, and takes the old one's essex county
OLD_METRO_SLUGS = {
    "ma-berkshires",
    "ma-boston",
    "ma-boston-metro-region",
    "ma-cape-cod",
    "ma-central",
    "ma-south-shore-coast",
}

AREAS = [
    metro("metro_CT_Coast", "CT: Coast", "CT", ["ct"], counties=["fairfield", "middlesex", "new haven", "new london"]),
    metro("metro_CT_North", "CT: North", "CT", ["ct"], counties=["hartford", "litchfield", "tolland"]),
    metro(
        "metro_DC_Washington_Beltway", "DC: Washington Beltway", "DC", ["dc", "md"],
        counties=["district of columbia", "montgomery", "prince george's"],
    ),
    *MASSACHUSETTS,
    metro("metro_MD_Baltimore", "MD: Baltimore", "MD", ["md"], cities=["baltimore"]),
    metro(
        "metro_ME_Coast", "ME: Coast", "ME", ["me"],
        counties=[
            "androscoggin", "cumberland", "hancock", "kennebec", "knox", "lincoln", "sagadahoc", "waldo", "washington",
            "york",
        ],
    ),
    metro(
        "metro_ME_North", "ME: North", "ME", ["me"],
        counties=["aroostook", "franklin", "oxford", "penobscot", "piscataquis", "somerset"],
    ),
    metro("metro_NH_North", "NH: North", "NH", ["nh"], counties=["belknap", "carroll", "coös", "grafton"]),
    metro(
        "metro_NH_South", "NH: South", "NH", ["nh"],
        counties=["cheshire", "hillsborough", "merrimack", "rockingham", "strafford", "sullivan"],
    ),
    metro(
        "metro_NJ_Central", "NJ: Central", "NJ", ["nj"],
        counties=["hunterdon", "mercer", "middlesex", "monmouth", "somerset"],
    ),
    metro(
        "metro_NJ_North", "NJ: North", "NJ", ["nj"],
        counties=["bergen", "essex", "hudson", "morris", "passaic", "sussex", "union", "warren"],
    ),
    metro(
        "metro_NJ_South", "NJ: South", "NJ", ["nj"],
        counties=["atlantic", "burlington", "camden", "cape may", "cumberland", "gloucester", "ocean", "salem"],
    ),
    metro(
        "metro_NY_Central", "NY: Central", "NY", ["ny"],
        counties=[
            "broome", "broome / delaware", "cayuga", "chenango", "chenango / madison", "cortland", "delaware", "fulton",
            "herkimer", "herkimer / fulton", "madison", "montgomery", "oneida", "onondaga", "oswego", "otsego",
            "schoharie", "tioga", "tompkins",
        ],
    ),
    metro(
        "metro_NY_Hudson_Valley", "NY: Hudson Valley", "NY", ["ny"],
        counties=[
            "albany", "columbia", "dutchess", "greene", "orange", "putnam", "rensselaer", "rockland", "saratoga",
            "schenectady", "sullivan", "ulster", "warren", "washington", "westchester",
        ],
    ),
    metro("metro_NY_Long_Island", "NY: Long Island", "NY", ["ny"], counties=["nassau", "suffolk"]),
    metro(
        "metro_NY_North", "NY: North", "NY", ["ny"],
        counties=["clinton", "essex", "essex / franklin", "franklin", "hamilton", "jefferson", "lewis", "st. lawrence"],
    ),
    metro(
        "metro_NY_NYC", "NY: NYC", "NY", ["ny"],
        counties=["bronx", "bronx / kings / new york / queens / richmond", "kings", "new york", "queens", "richmond"],
    ),
    metro(
        "metro_NY_NYC_Metro_Region", "NY: NYC Metro Region", "", ["ny", "nj"],
        counties=[
            "bergen", "bronx", "bronx / kings / new york / queens / richmond", "essex", "fairfield", "hudson", "kings",
            "nassau", "new york", "passaic", "queens", "richmond", "rockland", "union", "westchester",
        ],
    ),
    metro(
        "metro_NY_West", "NY: West", "NY", ["ny"],
        counties=[
            "allegany", "allegany / steuben", "cattaraugus", "chautauqua", "chemung", "erie", "erie / cattaraugus",
            "livingston", "monroe", "niagara", "ontario", "ontario / seneca", "orleans", "schuyler", "seneca",
            "steuben", "wayne", "wyoming", "wyoming / genesse", "yates", "yates / ontario",
        ],
    ),
    metro(
        "metro_PA_Central", "PA: Central", "PA", ["pa"],
        counties=[
            "adams", "bedford", "blair", "bradford", "cambria", "cambria / blair", "cameron", "centre", "clearfield",
            "clinton", "columbia", "cumberland", "cumberland / franklin", "dauphin", "elk", "franklin", "fulton",
            "huntingdon", "juniata", "lancaster", "lancaster / berks", "lebanon", "lycoming", "mckean", "mifflin",
            "montour", "northampton / lehigh", "northumberland", "perry", "potter", "schuylkill",
            "schuylkill / columbia", "snyder", "somerset", "sullivan", "tioga", "union", "york",
        ],
    ),
    metro(
        "metro_PA_East", "PA: East", "PA", ["pa"],
        counties=[
            "berks", "bucks", "carbon", "chester", "delaware", "lackawanna", "lehigh", "luzerne", "monroe",
            "montgomery", "montgomery / bucks", "northampton", "northampton / lehigh", "philadelphia", "pike",
            "susquehanna", "wayne", "wyoming",
        ],
    ),
    metro("metro_PA_Philadelphia", "PA: Philadelphia", "PA", []),
    metro("metro_PA_Philly_Metro_Region", "PA: Philly Metro Region", "PA", []),
    metro("metro_PA_Pitt_Metro_Region", "PA: Pitt Metro Region", "PA", []),
    metro("metro_PA_Pittsburgh", "PA: Pittsburgh", "PA", []),
    metro(
        "metro_PA_West", "PA: West", "PA", ["pa"],
        counties=[
            "allegheny", "armstrong", "beaver", "butler", "clarion", "crawford", "erie", "fayette",
            "fayette / somerset", "forest", "greene", "indiana", "jefferson", "jefferson / clearfield", "lawrence",
            "lawrence / beaver", "mercer", "venango", "venango / clarion", "warren", "washington",
            "washington / allegheny", "westmoreland", "westmoreland / allegheny",
        ],
    ),
    metro(
        "metro_VT_North", "VT: North", "VT", ["vt"],
        counties=[
            "addison", "caledonia", "chittenden", "essex", "franklin", "grand isle", "lamoille", "orange", "orleans",
            "washington",
        ],
    ),
    metro("metro_VT_South", "VT: South", "VT", ["vt"], counties=["bennington", "rutland", "windham", "windsor"]),
    region("region_Chesapeake_Bay", "Chesapeake Bay", "", ["dc", "de", "md"]),
    region("region_Mid-Atlantic", "Mid-Atlantic", "", ["dc", "de", "md", "nj", "ny", "pa"]),
    region("region_New_England", "New England", "", ["ct", "ma", "me", "nh", "ri", "vt"]),
    region("region_New_England_North", "New England: North", "", ["me", "nh", "vt"]),
    region("region_New_England_South", "New England: South", "", ["ct", "ma", "ri"]),
    region("region_Northeast_Corridor", "Northeast Corridor", "", []),
    region("region_Tri-State", "Tri-State", "", ["ct", "nj", "ny"]),
    state("state_Connecticut", "Connecticut", "CT", ["ct"]),
    state("state_DC", "DC", "DC", ["dc"]),
    state("state_Delaware", "Delaware", "DE", ["de"]),
    state("state_Maine", "Maine", "ME", ["me"]),
    state("state_Maryland", "Maryland", "MD", ["md"]),
    state("state_Massachusetts", "Massachusetts", "MA", ["ma"]),
    state("state_New_Hampshire", "New Hampshire", "NH", ["nh"]),
    state("state_New_Jersey", "New Jersey", "NJ", ["nj"]),
    state("state_New_York", "New York", "NY", ["ny"]),
    state("state_Pennsylvania", "Pennsylvania", "PA", ["pa"]),
    state("state_Rhode_Island", "Rhode Island", "RI", ["ri"]),
    state("state_Vermont", "Vermont", "VT", ["vt"]),
]
