from core.models import Event
from django.core.management.base import BaseCommand
from tqdm import tqdm


class Command(BaseCommand):
    def handle(self, *args, **options):
        # all_objects, not objects: unapproved events need fresh html for when they are approved
        for event in tqdm(Event.all_objects.all()):
            event.save()
        print("done")
