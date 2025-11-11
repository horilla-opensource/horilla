from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import Group, Permission
from django.utils.translation import gettext_lazy as _

class HorillaUser(AbstractUser):
    is_new_employee = models.BooleanField(default=False)

    class Meta:
        swappable = "AUTH_USER_MODEL"
        verbose_name = _("User")
        verbose_name_plural = _("Users")

class LegacyUser(models.Model):
    id = models.BigAutoField(primary_key=True)
    username = models.CharField(max_length=150)
    password = models.CharField(max_length=128)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)
    last_login = models.DateTimeField(blank=True, null=True)
    date_joined = models.DateTimeField(blank=True, null=True)

    # Map Many-to-Many through existing join tables
    groups = models.ManyToManyField(
        Group,
        through='AuthUserGroups',
        related_name='legacy_users'
    )
    user_permissions = models.ManyToManyField(
        Permission,
        through='AuthUserUserPermissions',
        related_name='legacy_users'
    )

    class Meta:
        db_table = 'auth_user'
        managed = False

class AuthUserGroups(models.Model):
    user = models.ForeignKey(LegacyUser, db_column='user_id', on_delete=models.CASCADE)
    group = models.ForeignKey(Group, db_column='group_id', on_delete=models.CASCADE)

    class Meta:
        db_table = 'auth_user_groups'
        managed = False


class AuthUserUserPermissions(models.Model):
    user = models.ForeignKey(LegacyUser, db_column='user_id', on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, db_column='permission_id', on_delete=models.CASCADE)

    class Meta:
        db_table = 'auth_user_user_permissions'
        managed = False
