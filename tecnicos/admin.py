from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Tecnico, Curso, Participacion, Certificado


# ─────────────────────────────────────────────
# ModelForms con validaciones para el Admin
# ─────────────────────────────────────────────

class TecnicoAdminForm(forms.ModelForm):
    class Meta:
        model  = Tecnico
        fields = '__all__'

    def clean_cedula(self):
        cedula = self.cleaned_data.get('cedula', '').strip()
        if not cedula.isdigit() or len(cedula) != 10:
            raise ValidationError('La cédula debe tener exactamente 10 dígitos numéricos.')
        return cedula

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono', '').strip()
        if not telefono.isdigit() or len(telefono) != 10:
            raise ValidationError('El teléfono debe tener exactamente 10 dígitos numéricos.')
        return telefono

    def clean_nombres(self):
        import re
        nombres = self.cleaned_data.get('nombres', '').strip()
        if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]+$', nombres):
            raise ValidationError('Los nombres solo pueden contener letras y espacios.')
        if len(nombres) < 2:
            raise ValidationError('Los nombres deben tener al menos 2 caracteres.')
        return nombres

    def clean_apellidos(self):
        import re
        apellidos = self.cleaned_data.get('apellidos', '').strip()
        if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]+$', apellidos):
            raise ValidationError('Los apellidos solo pueden contener letras y espacios.')
        if len(apellidos) < 2:
            raise ValidationError('Los apellidos deben tener al menos 2 caracteres.')
        return apellidos

    def clean_fecha_ingreso(self):
        fecha = self.cleaned_data.get('fecha_ingreso')
        if fecha and fecha > timezone.localdate():
            raise ValidationError('La fecha de ingreso no puede ser una fecha futura.')
        return fecha


class CursoAdminForm(forms.ModelForm):
    class Meta:
        model  = Curso
        fields = '__all__'

    def clean(self):
        cleaned = super().clean()
        fecha_inicio = cleaned.get('fecha_inicio')
        fecha_fin    = cleaned.get('fecha_fin')
        duracion     = cleaned.get('duracion')
        cupos        = cleaned.get('cupos')

        if fecha_inicio and fecha_fin and fecha_fin <= fecha_inicio:
            raise ValidationError('La fecha de fin debe ser mayor que la fecha de inicio.')

        if duracion is not None and (duracion < 1 or duracion > 1000):
            raise ValidationError('La duración debe estar entre 1 y 1000 horas.')

        if cupos is not None and (cupos < 1 or cupos > 500):
            raise ValidationError('Los cupos deben estar entre 1 y 500.')

        return cleaned


class ParticipacionAdminForm(forms.ModelForm):
    class Meta:
        model  = Participacion
        fields = '__all__'

    def clean_nota_final(self):
        nota = self.cleaned_data.get('nota_final')
        if nota is not None:
            if nota < 0 or nota > 100:
                raise ValidationError('La nota debe estar entre 0 y 100.')
        return nota


# ─────────────────────────────────────────────
# Registro en el Admin
# ─────────────────────────────────────────────

@admin.register(Tecnico)
class TecnicoAdmin(admin.ModelAdmin):
    form          = TecnicoAdminForm
    list_display  = ('cedula', 'nombre_completo', 'especialidad', 'institucion', 'ciudad', 'estado')
    list_filter   = ('estado', 'especialidad', 'ciudad')
    search_fields = ('cedula', 'nombres', 'apellidos', 'correo')


@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    form          = CursoAdminForm
    list_display  = ('codigo', 'nombre', 'instructor', 'duracion', 'fecha_inicio', 'fecha_fin', 'modalidad', 'cupos', 'estado')
    list_filter   = ('estado', 'modalidad')
    search_fields = ('codigo', 'nombre', 'instructor')


@admin.register(Participacion)
class ParticipacionAdmin(admin.ModelAdmin):
    form          = ParticipacionAdminForm
    list_display  = ('tecnico', 'curso', 'fecha_inscripcion', 'nota_final', 'estado')
    list_filter   = ('estado', 'curso')
    search_fields = ('tecnico__nombres', 'tecnico__apellidos', 'curso__nombre')


@admin.register(Certificado)
class CertificadoAdmin(admin.ModelAdmin):
    list_display  = ('codigo', 'participacion', 'fecha_emision')
    search_fields = ('codigo',)
