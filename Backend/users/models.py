from django.contrib.auth.models import (
    BaseUserManager,
    AbstractBaseUser,
    PermissionsMixin
)
from django.db import models


class UserAccountManager(BaseUserManager):
    def create_user(self, email, password=None, **kwargs):
        if not email:
            raise ValueError('Users must have an email address')

        email = self.normalize_email(email)
        email = email.lower()

        user = self.model(
            email=email,
            **kwargs
        )

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password=None, **kwargs):
        user = self.create_user(
            email,
            password=password,
            **kwargs
        )

        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)

        return user


class UserAccount(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('assistant', 'Lab Assistant'),
        ('teacher', 'Teacher'),
        ('admin', 'Administrator'),
    ]
    
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True, max_length=255)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    objects = UserAccountManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def __str__(self):
        return self.email


class Chemical(models.Model):
    FORM_CHOICES = [
        ('powder', 'Powder'),
        ('aqueous', 'Aqueous'),
        ('crystalline', 'Crystalline'),
    ]

    DANGER_LEVELS = [
        ('green', 'All users'),
        ('yellow', 'Teachers & Assistants'),
        ('red', 'Teachers only'),
    ]

    name = models.CharField(max_length=100)
    form = models.CharField(max_length=20, choices=FORM_CHOICES)
    concentration = models.CharField(max_length=50, blank=True, null=True)
    volume = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    quantity = models.IntegerField()
    storage_location = models.CharField(max_length=255)
    expiry_date = models.DateField()
    msds_file = models.FileField(upload_to='msds/', null=True, blank=True)
    danger_classification = models.CharField(max_length=10, choices=DANGER_LEVELS)
    added_by = models.ForeignKey('UserAccount', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.form})"


class Equipment(models.Model):
    CONDITION_CHOICES = [
        ('working', 'Working'),
        ('needs_maintenance', 'Needs Maintenance'),
        ('broken', 'Broken'),
    ]

    name = models.CharField(max_length=100)
    condition = models.CharField(max_length=30, choices=CONDITION_CHOICES)
    quantity = models.IntegerField()
    last_maintenance_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    added_by = models.ForeignKey('UserAccount', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
