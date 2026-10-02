from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers


User = get_user_model()



class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate_email(self, value: str) -> str:
        email = User.objects.normalize_email(value)
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError(
                'Email already exists'
            )
        return email
    
    def validate(self, attrs: dict[str, str]) -> dict[str, str]:
        user = User(email=attrs['email'])
        try:
            validate_password(attrs['password'], user=user)
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                {'password': error.messages}
            ) from error
        return attrs
    

class RegisteredUserSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    email = serializers.EmailField(read_only=True)
