# a "Bands & artists" menu item for the a-z index (add-act-index-and-search), so production
# gets it on deploy; editors can move, rename or hide it in the admin

from django.db import migrations
from django.db.models import Max

URL = "/bands"


def add_menu_item(apps, schema_editor):
    MenuItem = apps.get_model("core", "MenuItem")
    if MenuItem.objects.filter(url=URL).exists():
        return
    last = MenuItem.objects.aggregate(last=Max("order"))["last"]
    MenuItem.objects.create(
        name="Bands & artists", url=URL, show_in_header=True, show_in_footer=True,
        order=0 if last is None else last + 1,
    )


def remove_menu_item(apps, schema_editor):
    apps.get_model("core", "MenuItem").objects.filter(url=URL, name="Bands & artists").delete()


class Migration(migrations.Migration):
    dependencies = [("core", "0101_act_review")]
    operations = [migrations.RunPython(add_menu_item, remove_menu_item)]
