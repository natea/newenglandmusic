from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        from django.conf import settings
        from django.contrib.auth.signals import user_logged_in
        from django.db.models.signals import post_migrate

        from core.admin_group import sync_admin_group
        from core.event_performers import connect_signals
        from core.site_record import sync_site_record

        connect_signals()
        # after core's permissions exist: auth makes them in its own post_migrate handler
        post_migrate.connect(sync_admin_group, sender=self, dispatch_uid="sync-admin-group")
        # after the sites app has made its example.com record, which runs first (INSTALLED_APPS order)
        post_migrate.connect(sync_site_record, sender=self, dispatch_uid="sync-site-record")

        if settings.POSTHOG_MW_CLIENT:

            def identify_posthog_user(sender, request, user, **kwargs):
                """Identify the active PostHog request context after Django login."""
                settings.POSTHOG_MW_CLIENT.identify_context(str(user.pk))
                settings.POSTHOG_MW_CLIENT.set(
                    distinct_id=str(user.pk),
                    properties={
                        "email": user.email,
                        "is_staff": user.is_staff,
                    },
                )

            user_logged_in.connect(
                identify_posthog_user,
                dispatch_uid="posthog-identify-logged-in-user",
                weak=False,
            )
