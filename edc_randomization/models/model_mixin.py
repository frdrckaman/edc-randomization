from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django_crypto_fields.fields import EncryptedCharField
from edc_model.models import HistoricalRecords
from edc_sites.models import CurrentSiteManager

from ..choices import ASSIGNMENT_CHOICES
from ..constants import ACTIVE, PLACEBO, ACTIVE_NAME, PLACEBO_NAME
from ..randomizer import Randomizer, RandomizationError


class RandomizationListModelError(Exception):
    pass


class RandomizationListManager(models.Manager):
    def get_by_natural_key(self, sid):
        return self.get(sid=sid)


class RandomizationListModelMixin(models.Model):

    """
    A model mixin for the randomization list.

    The default expects and ACTIVE vs PLACEBO randomization. If
    yours differs, you need to re-declare field "assignment"
    and model method "treatment_description". The default
    `Randomizer` class MAY also need to be customized.
    """

    # customize if approriate
    randomizer_cls = Randomizer

    # customize if approriate
    assignment = EncryptedCharField(choices=ASSIGNMENT_CHOICES)

    subject_identifier = models.CharField(
        verbose_name="Subject Identifier", max_length=50, null=True, unique=True
    )

    sid = models.IntegerField(unique=True)

    site_name = models.CharField(max_length=100)

    allocation = EncryptedCharField(
        verbose_name="Original integer allocation", null=True
    )

    allocated = models.BooleanField(default=False)

    allocated_datetime = models.DateTimeField(null=True)

    allocated_user = models.CharField(max_length=50, null=True)

    allocated_site = models.ForeignKey(Site, null=True, on_delete=models.PROTECT)

    verified = models.BooleanField(default=False)

    verified_datetime = models.DateTimeField(null=True)

    verified_user = models.CharField(max_length=50, null=True)

    objects = RandomizationListManager()

    history = HistoricalRecords(inherit=True)

    on_site = CurrentSiteManager("allocated_site")

    def __str__(self):
        return f"{self.site_name}.{self.sid} subject={self.subject_identifier}"

    def save(self, *args, **kwargs):
        try:
            self.assignment_description
        except RandomizationError as e:
            raise RandomizationListModelError(e)
        try:
            Site.objects.get(name=self.site_name)
        except ObjectDoesNotExist:
            site_names = [obj.name for obj in Site.objects.all()]
            raise RandomizationListModelError(
                f"Invalid site name. Got {self.site_name}. "
                f"Expected one of {site_names}."
            )
        super().save(*args, **kwargs)

    @property
    def short_label(self):
        return f"{self.assignment} SID:{self.site_name}.{self.sid}"

    # customize if approriate
    @property
    def assignment_description(self):
        """May be overridden.
        """
        if self.assignment == PLACEBO:
            assignment_description = PLACEBO_NAME
        elif self.assignment == ACTIVE:
            assignment_description = ACTIVE_NAME
        else:
            raise RandomizationError(
                f"Invalid assignment. Expected one of [{PLACEBO}, {ACTIVE}]. "
                f"Got `{self.assignment}`"
            )
        return assignment_description

    def natural_key(self):
        return (self.sid,)

    class Meta:
        abstract = True
        ordering = ("site_name", "sid")
        unique_together = ("site_name", "sid")
        permissions = (("display_assignment", "Can display assignment"),)
