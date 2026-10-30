from django.template.loader import get_template


def bake_event_html(event):
    # imported here: core.models imports this module
    from core.artist_previews import event_artist_previews
    from core.event_performers import listing_parts

    template = get_template("core/event.html")
    title_parts, artist_parts = listing_parts(event)
    return template.render(
        {
            "event": event,
            "artist_previews": event_artist_previews(event),
            "title_parts": title_parts,
            "artist_parts": artist_parts,
        }
    )
