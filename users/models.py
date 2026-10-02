from django.db import models
from django.db.models.functions import Lower
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser

from common.models import UUIDModel




class UsersManager(BaseUserManager):
    @classmethod
    def normalize_email(cls, email):
        return super().normalize_email(email).lower()

    def get_by_natural_key(self, username):
        return self.get(email=self.normalize_email(username))

    async def aget_by_natural_key(self, username):
        return await self.aget(email=self.normalize_email(username))

    def create_user(
        self,
        email: str,
        password: str | None = None,
        **extra_fields
    ):
        if not email:
            raise ValueError('Email is required')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")

        return self.create_user(email, password, **extra_fields)
    


class User(AbstractUser, UUIDModel):
    username = None
    email = models.EmailField(unique=True)
    

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UsersManager()

    class Meta(AbstractUser.Meta):
        abstract = False
        constraints = [
            models.CheckConstraint(
                condition=models.Q(email=Lower("email")),
                name="users_user_email_lowercase",
            ),
        ]

    def save(self, *args, **kwargs):
        self.email = type(self).objects.normalize_email(self.email)
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.email