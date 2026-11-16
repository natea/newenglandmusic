from django.db import migrations, models


def fill_slugs(apps, schema_editor):
    from core.models import venue_slug

    Venue = apps.get_model("core", "Venue")
    taken = set()
    # by pk, so the venue added first keeps the plain name; update(), so no event re-renders
    for venue in Venue.objects.order_by("pk").only("pk", "name", "city_town"):
        slug = venue_slug(venue.name, venue.city_town, taken=taken)
        taken.add(slug)
        Venue.objects.filter(pk=venue.pk).update(slug=slug)


class Migration(migrations.Migration):
    dependencies = [("core", "0109_act_is_inactive")]

    operations = [
        migrations.AddField(
            model_name="venue",
            name="slug",
            field=models.SlugField(blank=True, max_length=140, null=True, unique=True),
        ),
        migrations.RunPython(fill_slugs, migrations.RunPython.noop),
    ]
