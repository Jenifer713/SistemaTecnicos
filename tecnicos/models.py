from django.db import models
from django.contrib.auth.models import User
from django.core.validators import (
    MinValueValidator, MaxValueValidator, RegexValidator
)


# TÉCNICO

class Tecnico(models.Model):
    ESTADO_CHOICES = [
        ('Activo', 'Activo'),
        ('Inactivo', 'Inactivo'),
    ]

    ESPECIALIDAD_CHOICES = [
        ('Desarrollo Web', 'Desarrollo Web'),
        ('Redes y Telecomunicaciones', 'Redes y Telecomunicaciones'),
        ('Ciberseguridad', 'Ciberseguridad'),
        ('Soporte Técnico', 'Soporte Técnico'),
        ('Base de Datos', 'Base de Datos'),
        ('Inteligencia Artificial', 'Inteligencia Artificial'),
        ('Cloud Computing', 'Cloud Computing'),
        ('Desarrollo Móvil', 'Desarrollo Móvil'),
    ]

    # Vínculo con el sistema de usuarios de Django (opcional para técnicos sin login)
    usuario = models.OneToOneField(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='tecnico'
    )

    cedula      = models.CharField(
        max_length=10, unique=True, verbose_name='Cédula',
        validators=[RegexValidator(r'^\d{10}$', 'La cédula debe tener exactamente 10 dígitos numéricos.')]
    )
    nombres     = models.CharField(
        max_length=100, verbose_name='Nombres',
        validators=[RegexValidator(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]+$', 'Los nombres solo pueden contener letras y espacios.')]
    )
    apellidos   = models.CharField(
        max_length=100, verbose_name='Apellidos',
        validators=[RegexValidator(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]+$', 'Los apellidos solo pueden contener letras y espacios.')]
    )
    correo      = models.EmailField(unique=True, verbose_name='Correo')
    telefono    = models.CharField(
        max_length=10, verbose_name='Teléfono',
        validators=[RegexValidator(r'^\d{10}$', 'El teléfono debe tener exactamente 10 dígitos numéricos.')]
    )
    especialidad= models.CharField(max_length=50, choices=ESPECIALIDAD_CHOICES, verbose_name='Especialidad')
    institucion = models.CharField(max_length=150, verbose_name='Institución')
    ciudad      = models.CharField(max_length=100, verbose_name='Ciudad')
    fecha_ingreso = models.DateField(verbose_name='Fecha de ingreso')
    estado      = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='Activo', verbose_name='Estado')
    foto        = models.ImageField(upload_to='tecnicos/', null=True, blank=True, verbose_name='Foto')

    class Meta:
        verbose_name = 'Técnico'
        verbose_name_plural = 'Técnicos'
        ordering = ['apellidos', 'nombres']

    def __str__(self):
        return f'{self.nombres} {self.apellidos}'

    @property
    def nombre_completo(self):
        return f'{self.nombres} {self.apellidos}'


# CURSO

class Curso(models.Model):
    MODALIDAD_CHOICES = [
        ('Presencial', 'Presencial'),
        ('Virtual', 'Virtual'),
        ('Híbrido', 'Híbrido'),
    ]

    ESTADO_CHOICES = [
        ('Activo', 'Activo'),
        ('Inactivo', 'Inactivo'),
        ('Finalizado', 'Finalizado'),
    ]

    codigo      = models.CharField(max_length=20, unique=True, verbose_name='Código')
    nombre      = models.CharField(max_length=150, verbose_name='Nombre del curso')
    instructor  = models.CharField(max_length=100, verbose_name='Instructor')
    duracion    = models.PositiveIntegerField(
        verbose_name='Duración (horas)',
        validators=[MinValueValidator(1), MaxValueValidator(1000)]
    )
    fecha_inicio= models.DateField(verbose_name='Fecha de inicio')
    fecha_fin   = models.DateField(verbose_name='Fecha de fin')
    modalidad   = models.CharField(max_length=15, choices=MODALIDAD_CHOICES, default='Presencial', verbose_name='Modalidad')
    cupos       = models.PositiveIntegerField(
        verbose_name='Cupos disponibles',
        validators=[MinValueValidator(1), MaxValueValidator(500)]
    )
    descripcion = models.TextField(blank=True, null=True, verbose_name='Descripción')
    estado      = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='Activo', verbose_name='Estado')

    class Meta:
        verbose_name = 'Curso'
        verbose_name_plural = 'Cursos'
        ordering = ['fecha_inicio', 'nombre']

    def __str__(self):
        return f'{self.codigo} - {self.nombre}'



# PARTICIPACIÓN (Técnico ↔ Curso)

class Participacion(models.Model):
    ESTADO_CHOICES = [
        ('Inscrito', 'Inscrito'),
        ('Aprobado', 'Aprobado'),
        ('Reprobado', 'Reprobado'),
        ('Retirado', 'Retirado'),
    ]

    tecnico         = models.ForeignKey(Tecnico, on_delete=models.CASCADE, related_name='participaciones', verbose_name='Técnico')
    curso           = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='participaciones', verbose_name='Curso')
    fecha_inscripcion = models.DateField(auto_now_add=True, verbose_name='Fecha de inscripción')
    nota_final      = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name='Nota final',
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    estado          = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='Inscrito', verbose_name='Estado')

    class Meta:
        verbose_name = 'Participación'
        verbose_name_plural = 'Participaciones'
        # Un técnico no puede inscribirse dos veces al mismo curso
        unique_together = [('tecnico', 'curso')]
        ordering = ['-fecha_inscripcion']

    def __str__(self):
        return f'{self.tecnico} — {self.curso}'

    def save(self, *args, **kwargs):
        """Asigna automáticamente el estado según la nota."""
        if self.nota_final is not None:
            if self.nota_final >= 70:
                self.estado = 'Aprobado'
            else:
                self.estado = 'Reprobado'
        super().save(*args, **kwargs)


# CERTIFICADO

class Certificado(models.Model):
    participacion   = models.OneToOneField(
        Participacion, on_delete=models.CASCADE,
        related_name='certificado',
        verbose_name='Participación'
    )
    codigo          = models.CharField(max_length=30, unique=True, verbose_name='Código de certificado')
    fecha_emision   = models.DateField(auto_now_add=True, verbose_name='Fecha de emisión')
    archivo_pdf     = models.FileField(upload_to='certificados/', null=True, blank=True, verbose_name='Archivo PDF')

    class Meta:
        verbose_name = 'Certificado'
        verbose_name_plural = 'Certificados'
        ordering = ['-fecha_emision']

    def __str__(self):
        return f'Certificado {self.codigo} — {self.participacion.tecnico}'
