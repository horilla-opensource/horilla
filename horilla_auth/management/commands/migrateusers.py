from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from horilla_auth.models import HorillaUser, LegacyUser

class Command(BaseCommand):
    help = "Migrate users from LegacyUser (auth_user) to HorillaUser, including groups and permissions."

    def handle(self, *args, **options):
        created_count = 0
        skipped_count = 0

        with transaction.atomic():
            for old_user in LegacyUser.objects.all():
                if HorillaUser.objects.filter(username=old_user.username).exists():
                    skipped_count += 1
                    continue

                date_joined = old_user.date_joined
                if date_joined and timezone.is_naive(date_joined):
                    date_joined = timezone.make_aware(date_joined)
                last_login = old_user.last_login
                if last_login and timezone.is_naive(last_login):
                    last_login = timezone.make_aware(last_login)

                new_user = HorillaUser.objects.create(
                    id=old_user.id,
                    username=old_user.username,
                    password=old_user.password,
                    first_name=old_user.first_name,
                    last_name=old_user.last_name,
                    email=old_user.email,
                    is_staff=old_user.is_staff,
                    is_active=old_user.is_active,
                    is_superuser=old_user.is_superuser,
                    last_login=last_login,
                    date_joined=date_joined,
                    is_new_employee=False,
                )

                # Copy groups
                new_user.groups.set(old_user.groups.all())

                # Copy user permissions
                new_user.user_permissions.set(old_user.user_permissions.all())

                created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"✅ Migration complete: {created_count} users migrated, {skipped_count} skipped (with groups & permissions)."
        ))
