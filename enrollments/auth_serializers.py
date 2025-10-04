from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Student

class LoginSerializer[TokenObtainPairSerializer]:
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user) # pylint: disable=no-member
        token["username"] = user.username
        token["groups"] = list(user.groups.values_list("name", flat=True))
        return token
    
    def validate(self,attrs):
        data = super().validate(attrs) # pylint: disable=no-member
        user = self.user # pylint: disable=no-member
        groups = list(user.groups.values_list("name", flat=True))
        student = Student.objects.filter(user=user).first() # pylint: disable=no-member


        data["user"] = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "groups": groups,
            "student_id": student.id if student else None,
        }
        return data        