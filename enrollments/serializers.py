from rest_framework import serializers
from .models import Student, Course, Enrollment

class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ["id", "first_name", "last_name", "email", "id_number"]

class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ["id", "code", "title", "capacity"]

class EnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enrollment
        fields = ["id", "student", "course", "enrolled_at"]
        read_only_fields = ["enrolled_at"]