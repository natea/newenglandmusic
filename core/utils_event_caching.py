from django.template.loader import get_template


def bake_event_html(event):
    # imported here: core.models imports this module
    from core.artist_previews import event_artist_previews

    template = get_template("core/event.html")
    return template.render(
        {
            "event": event,
            "artist_previews": event_artist_previews(event),
        }
    )
