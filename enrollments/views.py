from datetime import datetime
import unicodedata, re

from django.contrib.auth.models import User, Group
from django.http import HttpResponse, Http404
from django.template.loader import get_template

from rest_framework import viewsets, filters, status
from rest_framework.response import Response
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema

from xhtml2pdf import pisa

from .models import Student, Course, Enrollment
from .serializers import StudentSerializer, CourseSerializer, EnrollmentSerializer


#def palabra para definir funciones
#el nombre, por convencion al pensarla como una funcion privada empieza con _ el nombre
#los parametros se declaran asi y el retorno con una flecha
def _base_username(first_name: str, last_name: str) -> str:
    #agarra solo el primer nombre o primer apellido
    fn = (first_name or "").split()[0]
    ln = (last_name or "").split()[0]

    #une el primer nombre con el primer apellido con un punto
    base = f"{fn}.{ln}".lower()
    #unicodedata.normalize("NFKD", base) significa que separa los carecteres raros,
    # los acentos o caracteres especiales
    #.encode("ascii", "ignore") primero separa tildes y caracteres especiales,
    # esto devuelve bytes ASCII
    #.decode("ascii") es para volver esos bytes a str python
    #lo del return es un regex para limpiar todos los caracteres
    # que no sean letras numeros puntos y guiones
    base = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9._-]", "", base) or "user"

def _unique_username(base: str) -> str:
    if not User.objects.filter(username=base).exists():
        return base
    i = 1
    while True:
        candidate = f"{base}{i}"
        if not User.objects.filter(username=base).exists():
            return candidate
        i += 1
@extend_schema(tags=["Students"])
class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all() # pylint: disable=no-member
    serializer_class = StudentSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["first_name", "last_name", "email", "id_number"]
    ordering_fields = ["last_name", "first_name"]

    @action(detail=True, methods=["get"])
    def courses(self, request, pk=None):
        enrolls = Enrollment.objects.filter(student_id = pk).select_related("course") # pylint: disable=no-member
        data = [{"course_id": e.course.id, "code": e.course.code, 
                 "title": e.course.title, "enrolled_at": e.enrolled_at} for e in enrolls]
        return Response(data)
    @action(detail=True, methods=["get"], url_path="report-pdf")
    def report_pdf(self, request, pk=None):
        # Busca el alumno por el id dado en la url
        try:

            student = Student.objects.get(pk=pk)  # pylint: disable=no-member
        except Student.DoesNotExist:  # pylint: disable=no-member
            raise Http404("Alumno no encontrado")

        
        enrolls = (
            Enrollment.objects  # pylint: disable=no-member
            #el filter usa el objeto student
            #osea el estudiante que buscamos por id arriba
            .filter(student=student)
            .select_related("course")
            .order_by("course__code")
        )

        #context es como los datos para que pueda hacer el pdf
        ctx = {
            "student": student,
            "enrolls": enrolls,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        return _render_pdf_from_template(
            request,
            "enrollments/report_student.html",
            ctx,
            f"alumno_{student.last_name}_{student.first_name}_cursos.pdf",
        )


@extend_schema(tags=["Courses"])    
class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all() # pylint: disable=no-member
    serializer_class = CourseSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["code", "title"]
    ordering_fields = ["code", "title"]

    @action(detail=True, methods=["get"])
    def students(self, request, pk=None):
        enrolls = Enrollment.objects.filter(course_id=pk).select_related("student") # pylint: disable=no-member
        data = [{"student_id": e.student.id, "first_name": e.student.first_name, 
                 "last_name": e.student.last_name, "email": e.student.email,
                 "id_number": e.student.id_number, "enrolled_at": e.enrolled_at} for e in enrolls]
        return Response(data)
    
    @action(detail=True, methods=["get"], url_path="report-pdf")
    def report_pdf(self, request, pk=None):
        #lo mismo busca por id de cursony si encuentra lo guarda en course
        try:
            course = Course.objects.get(pk=pk)  # pylint: disable=no-member
        except Course.DoesNotExist:# pylint: disable=no-member
            raise Http404("Curso no encontrado")

        # Inscripciones del curso
        enrolls = (
            #filtra por ese curso que buscamos arriba y trae tambien los estudiantes relacionados
            Enrollment.objects # pylint: disable=no-member
            .filter(course=course)
            .select_related("student")
            .order_by("student__last_name", "student__first_name")
        )
        #el contexto que necesita para construir el pdf
        ctx = {
            "course": course,
            "enrolls": enrolls,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        return _render_pdf_from_template(
            request,
            "enrollments/report_course.html",
            ctx,
            f"curso_{course.code}_alumnos.pdf",
        )
    
@extend_schema(tags=["Enrollments"])
class EnrollmentViewSet(viewsets.ModelViewSet):
    queryset= Enrollment.objects.select_related("student", "course").all() # pylint: disable=no-member
    serializer_class = EnrollmentSerializer
    #aca solo sobreescribimos la funcion create
    #porque el DRF ya genera de porsi, un crud basico
    #entonces para no romper la firma original le pasamos
    # args y kwargs, los cuales son args son los argumentos que puede recibir,
    # es para de la firma original
    # y kwargs tambien guarda argumentos solo que args guarda el valor y
    # kwargs el parametro y el valor de ese parametro, por eso es un diccionario
    def create(self, request, *args, **kwargs):
        #aca recupera del body si se ingreso el codigo de estudiante y curso
        student_id = request.data.get("student")
        course_id = request.data.get("course")
        if not student_id or not course_id:
            return Response({"detail": "student y course son requeridos."}, status= status.HTTP_400_BAD_REQUEST)
        try:
            #aca busca esos estudiantes y cursos
            student = Student.objects.get(pk=student_id) # pylint: disable=no-member
            course = Course.objects.get(pk=course_id) # pylint: disable=no-member
        #manejo de excepciones
        except (Student.DoesNotExist, Course.DoesNotExist): # pylint: disable=no-member
            return Response({"detail": "Alumno o curso no encontrado."},
                            status = status.HTTP_404_NOT_FOUND)
        #Validacion para asegurarse que el alumno aun no exista
        if Enrollment.objects.filter(student=student, course=course).exists(): # pylint: disable=no-member
            return Response({"detail": "El alumno ya esta inscripto en este curso"},
                            status = status.HTTP_400_BAD_REQUEST)
        #aca usa el metodo ya generado por el viewSet de create
        #para crear una matriculaciones silvestre y comun
        enrollment = Enrollment.objects.create(student = student, course = course) # pylint: disable=no-member
        #pero yo no quiero solo eso
        #habilitamos variables que nos seran utiles
        created_user = False
        temp_password = None
        #segun mi logica, si es la primera vez que el alumno se matricula,
        #se creara tambien su usuario y contraseña
        
        if not student.user:
            base = _base_username(student.first_name, student.last_name)
            username = _unique_username(base)
            #crea el objeto user para crearle un usuario al alumno
            user = User(
                username = username,
                first_name = (student.first_name or "").split()[0],
                last_name=(student.last_name or "").split()[0],
                email = student.email
            )
            #asigna temporalmente la cedula como contraseña
            temp_password = student.id_number
            #aca automaticamente al guardar la contraseña tambien la hashea
            user.set_password(temp_password)
            #guarda los cambios
            user.save()

            #Se usa el guion bajo porque el metodo devuelve si o si dos cosas
            #el objeto y un booleano pero como no me importa el bool
            #la convencion dice 
            group, _ = Group.objects.get_or_create(name="alumno")
            user.groups.add(group) # pylint: disable=no-member

            student.user = user
            student.save(update_fields=["user"])
            created_user = True

        else:
            username = student.user.username
        
        #averiguar porque le llamo asi mañana
        payload= {
            "enrollment": EnrollmentSerializer(enrollment).data,
            "credentials":{
                "username": username,
                "email": student.email,
                "created_user": created_user
            }
        }

        if created_user and temp_password:
            payload["credentials"]["temp_password"] = temp_password
        
        return Response(payload, status=status.HTTP_201_CREATED)
def _render_pdf_from_template(request, template_name: str, context: dict, filename: str)-> HttpResponse:
    template = get_template(template_name)
    html = template.render(context)

    response = HttpResponse(content_type="application/pdf")
    # 'inline' para ver en el navegador; usa 'attachment' si querés forzar descarga
    response["Content-Disposition"] = f'inline; filename="{filename}"'

    result = pisa.CreatePDF(src=html, dest=response, encoding="utf-8")
    if result.err:
        return HttpResponse("Error al generar PDF", status=500)
    return response


