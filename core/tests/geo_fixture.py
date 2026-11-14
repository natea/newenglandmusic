def load_geo_fixture():
    """the site's own areas (core/geo_areas.py), as every migrate loads them"""
    from core.geo_area_sync import sync_geo_areas

    sync_geo_areas()
