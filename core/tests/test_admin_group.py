from core.admin_group import GROUP_NAME, sync_admin_group
from django.contrib.auth.models import Group, Permission, User
from django.test import TestCase


def codenames(group):
    return {f"{p.content_type.app_label}.{p.codename}" for p in group.permissions.select_related("content_type")}


class AdminGroupTestCase(TestCase):
    """the admin group runs the site's records, not its accounts, groups or sites"""

    def setUp(self):
        self.editor = User.objects.create_user("sooz", password="pw", is_staff=True)
        self.editor.groups.add(Group.objects.get(name=GROUP_NAME))
        self.client.force_login(self.editor)

    def test_made_by_migrate_with_core_permissions_only(self):
        perms = codenames(Group.objects.get(name=GROUP_NAME))
        for perm in ("core.change_venue", "core.add_event", "core.delete_band", "core.view_jobrun"):
            self.assertIn(perm, perms)
        self.assertFalse({p for p in perms if not p.startswith("core.")})

    def test_kept_in_step_with_new_permissions(self):
        group = Group.objects.get(name=GROUP_NAME)
        group.permissions.clear()
        sync_admin_group()
        self.assertEqual(group.permissions.count(), Permission.objects.filter(content_type__app_label="core").count())

    def test_edits_the_sites_records(self):
        for path in ("/admin/", "/admin/core/venue/", "/admin/core/alleventproxy/", "/admin/core/band/add/"):
            self.assertEqual(self.client.get(path).status_code, 200, path)

    def test_cant_manage_accounts_groups_or_sites(self):
        for path in (
            "/admin/auth/user/", "/admin/auth/user/add/", f"/admin/auth/user/{self.editor.pk}/change/",
            "/admin/auth/group/add/", "/admin/sites/site/",
        ):
            self.assertEqual(self.client.get(path).status_code, 403, path)

    def test_the_admin_index_leaves_accounts_out(self):
        html = self.client.get("/admin/").content.decode()
        self.assertIn("/admin/core/venue/", html)
        self.assertNotIn("/admin/auth/user/", html)
        self.assertNotIn("/admin/sites/site/", html)

    def test_not_staff_no_admin(self):
        self.editor.is_staff = False
        self.editor.save()
        self.assertEqual(self.client.get("/admin/core/venue/").status_code, 302)
