"""
what a pull request's preview may hold of the live site's data (preview-environments).

every table is on exactly one list, and a test fails while a table is on none, so a new table
can't reach previews unconsidered:

    COPIED     copied as it is
    LEFT_OUT   its rows are never copied: people's data, and the live site's accounts
    CLEANED    copied, then these columns are emptied

the nightly copy dumps the live database without the LEFT_OUT tables' rows, and
`scrub_preview_data` then empties the CLEANED columns, before anything is loaded where previews
are.
"""

from urllib.parse import urlsplit

PREVIEW_SETTINGS = "nycnoise.settings.preview"
PREVIEW_ADMIN = "preview-admin"

LEFT_OUT = (
    # people who asked for email, and what they chose
    "core_subscriber",
    "core_emailsubscriber",
    "core_signincode",
    "core_digestchoice",
    "core_mailrequest",
    # who is signed in, and what admins changed: its entries name subscribers by email
    "django_session",
    "django_admin_log",
    # the live site's accounts; a preview has only its own admin
    "auth_user",
    "auth_user_groups",
    "auth_user_user_permissions",
)

# table -> {column: the value that replaces it}
CLEANED = {
    "core_event": {"user_submission_email": None},
    # production tracebacks; the rows stay, since a venue's fetch status points at them
    "core_jobrun": {"output": "", "error": ""},
}

COPIED = (
    "auth_group",
    "auth_group_permissions",
    "auth_permission",
    "core_applemusicartistlink",
    "core_artist",
    "core_band",
    "core_bandmembership",
    "core_censusplace",
    "core_datemessage",
    "core_eventperformer",
    "core_geoarea",
    "core_indexpagemessages",
    "core_menuitem",
    "core_searchablestaticpagebit",
    "core_spotifyartistlink",
    "core_staticpage",
    "core_venue",
    "core_venueeventsource",
    "core_venuefetchstatus",
    "core_youtubeartistlink",
    "django_content_type",
    "django_migrations",
    "django_site",
)


def classified():
    return set(LEFT_OUT) | set(CLEANED) | set(COPIED)


def unclassified(tables):
    """the tables on no list, sorted"""
    return sorted(set(tables) - classified())


def dump_exclusions():
    """pg_dump's arguments that leave the LEFT_OUT tables' rows behind"""
    return [f"--exclude-table-data=public.{table}" for table in LEFT_OUT]


def refusal(settings_module, database_host):
    """why the scrub and the preview admin may not run here, or None when they may"""
    if settings_module != PREVIEW_SETTINGS:
        return f"this only runs under {PREVIEW_SETTINGS}, not {settings_module}"
    host = (database_host or "").lower()
    if host not in ("", "localhost", "127.0.0.1", "::1", "postgres") and not host.endswith(".neon.tech"):
        return f"this only runs against a local or Neon database, not {host}"
    return None


def database_host(url):
    return urlsplit(url or "").hostname or ""


def scrub(connection):
    """empties the LEFT_OUT tables and the CLEANED columns; returns [(what, rows)]"""
    done = []
    quote = connection.ops.quote_name
    with connection.cursor() as cursor:
        existing = set(connection.introspection.table_names(cursor))
        left_out = [table for table in LEFT_OUT if table in existing]
        if left_out:
            counts = {}
            for table in left_out:
                cursor.execute(f"SELECT count(*) FROM {quote(table)}")
                counts[table] = cursor.fetchone()[0]
            # together and without CASCADE: a copied table pointing at one of these fails loudly
            cursor.execute("TRUNCATE " + ", ".join(quote(table) for table in left_out) + " RESTART IDENTITY")
            done += [(table, counts[table]) for table in left_out]
        for table, columns in CLEANED.items():
            if table not in existing:
                continue
            assignments = ", ".join(f"{quote(column)} = %s" for column in columns)
            cursor.execute(f"UPDATE {quote(table)} SET {assignments}", list(columns.values()))
            done.append((f"{table}: {', '.join(columns)}", cursor.rowcount))
    return done
