from django.template.loader import get_template


def bake_event_html(event):
    # imported here: core.models imports this module
    from core.spotify_links import event_spotify_artists

    template = get_template("core/event.html")
    return template.render(
        {
            "event": event,
            "spotify_artists": event_spotify_artists(event),
        }
    )
