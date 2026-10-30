"""
the "admin" group: staff in it run the site's own records in the django admin (events,
venues, artists, bands, job runs and the rest of core) but not its accounts, groups or
sites, so they can't add people or raise anyone's access, their own included.

the group is kept in step with core's models after every migrate (CoreConfig.ready), so a
new model's permissions join it when the model ships, and render's build creates it.

to give someone an account: in the admin's users page, add them with "Staff status" ticked
and "Superuser status" left off, and choose the admin group.
"""

GROUP_NAME = "admin"


def sync_admin_group(**kwargs):
    """every permission on core's models, and nothing else"""
    from django.contrib.auth.models import Group, Permission

    group, _ = Group.objects.get_or_create(name=GROUP_NAME)
    group.permissions.set(Permission.objects.filter(content_type__app_label="core"))
