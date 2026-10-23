from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db.models import ImageField
from django.core.files.storage import storages


class Command(BaseCommand):
    help = 'Upload referenced local image files to the configured default storage.'

    def handle(self, *args, **options):
        if not settings.CLOUDINARY_CONFIGURED:
            raise CommandError(
                'Cloudinary is not configured. Set all Cloudinary environment '
                'variables before running this command.'
            )

        storage = storages['default']
        media_root = Path(settings.MEDIA_ROOT).resolve()
        uploaded = 0
        skipped = 0
        missing = []

        for model in apps.get_models():
            image_fields = [
                field for field in model._meta.get_fields()
                if isinstance(field, ImageField)
            ]
            for field in image_fields:
                for instance in model.objects.exclude(
                    **{field.name: ''}
                ).iterator():
                    image = getattr(instance, field.name)
                    name = image.name
                    if not name:
                        continue
                    if storage.exists(name):
                        skipped += 1
                        continue

                    source = (media_root / name).resolve()
                    if not source.is_relative_to(media_root):
                        raise CommandError(
                            f'Image path is outside MEDIA_ROOT: {name}'
                        )
                    if not source.is_file():
                        missing.append(name)
                        continue

                    with source.open('rb') as image_file:
                        image.save(name, File(image_file), save=False)
                    instance.save(update_fields=[field.name])
                    uploaded += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Uploaded {uploaded} image(s); {skipped} already existed in Cloudinary.'
            )
        )
        if missing:
            unique_missing = sorted(set(missing))
            self.stderr.write(
                'Missing local image files: ' + ', '.join(unique_missing)
            )
            raise CommandError(
                f'{len(unique_missing)} referenced image file(s) could not be uploaded.'
            )
