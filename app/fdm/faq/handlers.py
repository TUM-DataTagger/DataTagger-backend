from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.text import slugify

from fdm.faq.models import *


@receiver(pre_save, sender=FAQCategory)
def set_faq_category_slug(instance, *args, **kwargs):
    if not instance.slug:
        instance.slug = slugify(instance.name)


@receiver(pre_save, sender=FAQ)
def set_faq_slug(instance, *args, **kwargs):
    if not instance.slug:
        instance.slug = slugify(instance.question)
