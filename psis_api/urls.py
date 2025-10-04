
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from enrollments.views import StudentViewSet, CourseViewSet, EnrollmentViewSet, LoginView, MeView
from rest_framework_simplejwt.views import TokenRefreshView

router = DefaultRouter()
router.register(r"students", StudentViewSet)
router.register(r"courses", CourseViewSet)
router.register(r"enrollments", EnrollmentViewSet)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),

    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),

    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
]
