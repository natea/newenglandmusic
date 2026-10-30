from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        from django.db.models.signals import post_migrate

        from core.admin_group import sync_admin_group
        from core.event_performers import connect_signals

        connect_signals()
        # after core's permissions exist: auth makes them in its own post_migrate handler
        post_migrate.connect(sync_admin_group, sender=self, dispatch_uid="sync-admin-group")
