from meta.views import Meta
from django.templatetags.static import static
from typing import Optional

DEFAULT_TITLE = "New England Music"
DEFAULT_DESCRIPTION = (
    "Live music calendar for New England and the Northeast: concerts, DJ nights"
    " and open mics at venues across the region."
)


def get_meta(
    url=None,
    title=DEFAULT_TITLE,
    description: Optional[str] = DEFAULT_DESCRIPTION,
    redirect=None,
    redirect_time=0,
):
    """
    Generate Meta tags for pages.

    Args:
        url (str, optional): The base URL for the page. Defaults to None.
        title (str, optional): The title of the page. Defaults to "New England Music".
        description (str, optional): A brief description of the page content.
            Defaults to a description of the New England music calendar.
        redirect (str): If provided, sets up a page redirect to the specified URL.
        redirect_time (int): Sets the delay (in seconds) before redirect occurs.
            Defaults to 0 seconds if not specified.
    """
    meta = Meta(
        title=title,
        url=f"{url or ''}/",
        description=description,
        image=static("core/images/share-preview.png"),
    )

    if redirect:
        meta.extra_custom_props = [
            ("http-equiv", "refresh", f"{redirect_time}; url={redirect}")
        ]

    return meta
