from django.contrib import admin
from .models import Tecnico, Curso, Participacion, Certificado


@admin.register(Tecnico)
class TecnicoAdmin(admin.ModelAdmin):
    list_display  = ('cedula', 'nombre_completo', 'especialidad', 'institucion', 'ciudad', 'estado')
    list_filter   = ('estado', 'especialidad', 'ciudad')
    search_fields = ('cedula', 'nombres', 'apellidos', 'correo')


@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display  = ('codigo', 'nombre', 'instructor', 'duracion', 'fecha_inicio', 'fecha_fin', 'modalidad', 'cupos', 'estado')
    list_filter   = ('estado', 'modalidad')
    search_fields = ('codigo', 'nombre', 'instructor')


@admin.register(Participacion)
class ParticipacionAdmin(admin.ModelAdmin):
    list_display  = ('tecnico', 'curso', 'fecha_inscripcion', 'nota_final', 'estado')
    list_filter   = ('estado', 'curso')
    search_fields = ('tecnico__nombres', 'tecnico__apellidos', 'curso__nombre')


@admin.register(Certificado)
class CertificadoAdmin(admin.ModelAdmin):
    list_display  = ('codigo', 'participacion', 'fecha_emision')
    search_fields = ('codigo',)
