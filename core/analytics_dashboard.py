"""
the posthog dashboard of how the site is used (add-analytics-dashboard): its charts, each with a
stable key, a name, the question it answers, and the posthog query it runs. sync_posthog_dashboard
makes posthog's dashboard match this file; change a chart here and rerun it:

    venv/bin/python manage.py sync_posthog_dashboard --dry-run
    venv/bin/python manage.py sync_posthog_dashboard

charts use only the events the site sends (core/static/core/js/analytics.js) and posthog's own
pageview and geoip properties. the query shapes are posthog's (an InsightVizNode wrapping a
TrendsQuery or FunnelsQuery), checked against insights read back from posthog (design.md).
"""

DASHBOARD = {
    "name": "StageHopper: how the site is used",
    "description": "Who visits and from where, what they search for and find, which acts draw visits, "
    "and whether visits become saves, plays and ticket clicks. Defined in core/analytics_dashboard.py; "
    "changes made here in PostHog are overwritten by sync_posthog_dashboard.",
}

# the wizard's dashboard of server-side events the site doesn't send; the sync deletes it
WIZARD_DASHBOARD = "Analytics basics (wizard)"

# the events the site sends (site-analytics) and posthog's own; charts may name only these
SITE_EVENTS = {
    "search", "search_suggestion_chosen", "search_results_viewed", "act_page_viewed", "show_saved",
    "show_unsaved", "preview_played", "ticket_link_opened", "show_added_to_calendar",
    "calendar_feed_subscribed", "deck_act_passed", "deck_shows_saved",
}
POSTHOG_EVENTS = {"$pageview", "$pageleave"}

NEW_ENGLAND = ["Massachusetts", "Connecticut", "Rhode Island", "New Hampshire", "Maine", "Vermont"]
LAST_30_DAYS = {"date_from": "-30d"}


def series(event, math="total", label=None, math_property=None):
    node = {"kind": "EventsNode", "event": event, "name": event, "math": math}
    if label:
        node["custom_name"] = label
    if math_property:
        node["math_property"] = math_property
    return node


def where(key, value, operator="exact"):
    return {"key": key, "value": value, "operator": operator, "type": "event"}


def trend(nodes, breakdown=None, display="ActionsLineGraph", properties=None, interval="day", limit=None):
    query = {
        "kind": "TrendsQuery",
        "series": nodes,
        "interval": interval,
        "dateRange": LAST_30_DAYS,
        "trendsFilter": {"display": display},
    }
    if breakdown:
        query["breakdownFilter"] = {"breakdown": breakdown, "breakdown_type": "event"}
        if limit:
            query["breakdownFilter"]["breakdown_limit"] = limit
    if properties:
        query["properties"] = properties
    return {"kind": "InsightVizNode", "source": query}


def funnel(nodes, window_days=1):
    return {
        "kind": "InsightVizNode",
        "source": {
            "kind": "FunnelsQuery",
            "series": nodes,
            "dateRange": LAST_30_DAYS,
            "funnelsFilter": {"funnelWindowInterval": window_days, "funnelWindowIntervalUnit": "day"},
        },
    }


def table(event, breakdown, properties=None, limit=25, math="total"):
    return trend([series(event, math=math)], breakdown=breakdown, display="ActionsTable", properties=properties, limit=limit)


CHARTS = [
    # audience
    {
        "key": "visitors",
        "name": "Visitors and pageviews",
        "description": "Is the site growing? Unique visitors and pageviews by day.",
        "query": trend([series("$pageview", "dau", "Visitors"), series("$pageview", "total", "Pageviews")]),
    },
    {
        "key": "states",
        "name": "Where visitors are",
        "description": "Which states we reach: visitors by state, in the US.",
        "query": trend(
            [series("$pageview", "dau", "Visitors")], breakdown="$geoip_subdivision_1_name", display="ActionsBarValue",
            properties=[where("$geoip_country_code", "US")],
        ),
    },
    {
        "key": "towns",
        "name": "New England towns",
        "description": "Which parts of New England visitors come from: visitors by city, top 25.",
        "query": table("$pageview", "$geoip_city_name", properties=[where("$geoip_subdivision_1_name", NEW_ENGLAND)], math="dau"),
    },
    {
        "key": "referrers",
        "name": "How they arrive",
        "description": "Search engines, social media, links from venues? Pageviews by referring site.",
        "query": table("$pageview", "$referring_domain", limit=10),
    },
    {
        "key": "devices",
        "name": "Phone or computer",
        "description": "How much of the site is used on phones: pageviews by device type.",
        "query": trend([series("$pageview")], breakdown="$device_type", display="ActionsPie"),
    },
    # search
    {
        "key": "searches",
        "name": "Searches",
        "description": "How much search is used, and how often a suggestion is picked instead of a full search.",
        "query": trend([series("search", label="Full searches"), series("search_suggestion_chosen", label="Suggestions chosen")]),
    },
    {
        "key": "top-searches",
        "name": "Top searches",
        "description": "What people look for: the 25 most searched words.",
        "query": table("search_results_viewed", "query"),
    },
    {
        "key": "empty-searches",
        "name": "Searches that found nothing",
        "description": "Acts and venues people want that the site lacks: searches with no results.",
        "query": table("search_results_viewed", "query", properties=[where("total", 0)]),
    },
    {
        "key": "suggestion-kinds",
        "name": "Suggestions by kind",
        "description": "Do people look for bands, artists, venues or shows?",
        "query": trend([series("search_suggestion_chosen")], breakdown="kind", display="ActionsBarValue"),
    },
    # acts
    {
        "key": "top-acts",
        "name": "Most-viewed acts",
        "description": "Which acts draw visits: act pages viewed, by act, top 25.",
        "query": table("act_page_viewed", "name"),
    },
    {
        "key": "acts-with-shows",
        "name": "Act pages with and without a show",
        "description": "Do people visit acts with nothing coming up?",
        "query": trend([series("act_page_viewed")], breakdown="has_upcoming_show", display="ActionsPie"),
    },
    {
        "key": "search-to-tickets",
        "name": "From search to tickets",
        "description": "Does finding an act lead to a ticket click? Suggestion chosen, act page, ticket link, within a day.",
        "query": funnel([series("search_suggestion_chosen"), series("act_page_viewed"), series("ticket_link_opened")]),
    },
    # shows
    {
        "key": "intent",
        "name": "Saves, plays and ticket clicks",
        "description": "The actions that mean someone plans to go, by day.",
        "query": trend([series("show_saved"), series("preview_played"), series("ticket_link_opened")]),
    },
    {
        "key": "top-shows",
        "name": "Most-clicked shows",
        "description": "Which shows people go on to buy: ticket links followed, by show, top 25.",
        "query": table("ticket_link_opened", "show"),
    },
    {
        "key": "players",
        "name": "Plays by service",
        "description": "Which players people use: Spotify, Apple Music or YouTube.",
        "query": trend([series("preview_played")], breakdown="service", display="ActionsBarValue"),
    },
    {
        "key": "calendars",
        "name": "Calendars",
        "description": "Do people take shows into their calendars, and subscribe to feeds?",
        "query": trend(
            [series("show_added_to_calendar", label="Shows added"), series("calendar_feed_subscribed", label="Feeds subscribed")],
            display="ActionsBarValue",
        ),
    },
    # the discovery deck
    {
        "key": "deck",
        "name": "The discovery deck",
        "description": "Is the deck used, and does it lead to saved shows? Acts passed and shows saved, by day.",
        "query": trend([
            series("deck_act_passed", label="Acts passed"),
            series("deck_shows_saved", math="sum", math_property="count", label="Shows saved"),
        ]),
    },
]


def chart_events(chart):
    """every event a chart's query names"""
    return {node["event"] for node in chart["query"]["source"]["series"]}
