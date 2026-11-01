"""
the curated lists acts come from (MusicAct.sources), by their short key: what the admin's
source filter and column show. add a list here before importing it with import_act_list.
"""

SOURCES = {
    "ohb": "Oh Hello Boston",
}


def label(key):
    return SOURCES.get(key, key)
