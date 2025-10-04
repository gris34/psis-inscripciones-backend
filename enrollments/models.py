#MODULO DE MATRICULACION
#ARCHIVO DE MODELOS, para las migraciones a la bd
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator, MinLengthValidator

# Create your models here.

cedula_validator = RegexValidator(
    regex=r"[0-9.\-]+$",
    message="La cédula solo puede contener dígitos, puntos o guiones."
)

class Student(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, null=True, blank=True, related_name="student"
    )

    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    email = models.EmailField(unique=True)

    id_number = models.CharField(
        max_length=20,
        unique=True,
        validators=[MinLengthValidator(4), cedula_validator],
        help_text="Número de cedula sera la contraseña inicial del usuario"
    )

    def __str__(self):
        return f"{self.last_name}, {self.first_name}"
    
class Course(models.Model):
    code = models.CharField(max_length=10, unique=True)
    title = models.CharField(max_length=120)
    capacity = models.PositiveIntegerField(default=30)

    def __str__(self):
        return f"{self.code} - {self.title}"
    
class Enrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "course")