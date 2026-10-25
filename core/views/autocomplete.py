from core.models import Venue
from dal import autocomplete


class VenueAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # venues with an unknown status (is_active=None) are still listed
        qs = Venue.objects.exclude(is_active=False)

        if not self.q:
            return qs

        return qs.filter(name__icontains=self.q.strip())

    def get_result_label(self, result):
        # many venues share a name (e.g. "Porchfest"), so show where they are
        if result.location:
            return f"{result.name} ({result.location})"
        return result.name
