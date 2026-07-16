from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
import re
from .models import Tecnico, Curso, Participacion, Certificado


# ─────────────────────────────────────────────
# HELPERS DE VALIDACIÓN SERVER-SIDE
# ─────────────────────────────────────────────

def _validar_cedula(cedula):
    """Valida que la cédula tenga exactamente 10 dígitos numéricos."""
    if not cedula or not cedula.isdigit() or len(cedula) != 10:
        return 'La cédula debe tener exactamente 10 dígitos numéricos.'
    return None

def _validar_telefono(telefono):
    """Valida que el teléfono tenga exactamente 10 dígitos numéricos."""
    if not telefono or not telefono.isdigit() or len(telefono) != 10:
        return 'El teléfono debe tener exactamente 10 dígitos numéricos.'
    return None

def _validar_solo_letras(valor, nombre_campo):
    """Valida que el campo solo contenga letras y espacios."""
    if not valor or not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]+$', valor):
        return f'{nombre_campo} solo puede contener letras y espacios.'
    if len(valor) < 2:
        return f'{nombre_campo} debe tener al menos 2 caracteres.'
    return None

def _validar_fecha_no_futura(fecha_str):
    """Valida que la fecha no sea futura y que tenga formato correcto."""
    if not fecha_str:
        return 'La fecha de ingreso es obligatoria.'
    from datetime import date
    try:
        from datetime import datetime
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    except ValueError:
        return 'El formato de fecha no es válido.'
    if fecha > timezone.localdate():
        return 'La fecha de ingreso no puede ser una fecha futura.'
    return None

def _validar_foto(foto):
    """Valida extensión y tamaño de una imagen subida."""
    if foto:
        ext = foto.name.split('.')[-1].lower()
        if ext not in ['jpg', 'jpeg', 'png']:
            return 'Solo se permiten imágenes en formato JPG o PNG.'
        if foto.size > 2 * 1024 * 1024:  # 2 MB
            return 'La imagen no puede superar 2 MB.'
    return None



# HELPERS
def solo_admin(view_func):
    """Decorator: solo usuarios is_staff pueden acceder."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_staff:
            messages.error(request, 'No tienes permisos para acceder a esta sección.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper



# INICIO
def inicio(request):
    # Siempre muestra la página de inicio, sin redireccionar
    return render(request, 'inicio.html')



# LOGIN / LOGOUT

def login_view(request):
    # Si ya está autenticado puede seguir navegando normalmente
    from django.contrib.auth.forms import AuthenticationForm
    form = AuthenticationForm()

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            form = AuthenticationForm(data=request.POST)
            form.full_clean()

    return render(request, 'login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('inicio')



# DASHBOARD

@login_required(login_url='/login/')
def dashboard(request):
    user    = request.user
    es_admin = user.is_staff
    context = {
        'es_admin': es_admin,
        'fecha_hoy': timezone.localdate().strftime('%d de %B de %Y'),
    }

    if es_admin:
        context.update({
            'total_tecnicos':        Tecnico.objects.count(),
            'total_cursos':          Curso.objects.filter(estado='Activo').count(),
            'total_participaciones': Participacion.objects.count(),
            'total_certificados':    Certificado.objects.count(),
            'ultimas_participaciones': Participacion.objects.select_related(
                'tecnico', 'curso'
            ).order_by('-fecha_inscripcion')[:10],
        })
    else:
        try:
            tecnico = user.tecnico
            participaciones = Participacion.objects.filter(
                tecnico=tecnico).select_related('curso')
            context.update({
                'mis_participaciones':    participaciones.count(),
                'mis_aprobados':          participaciones.filter(estado='Aprobado').count(),
                'mis_certificados':       Certificado.objects.filter(
                                              participacion__tecnico=tecnico).count(),
                'participaciones_tecnico': participaciones,
                'tecnico': tecnico,
            })
        except Tecnico.DoesNotExist:
            context.update({
                'mis_participaciones': 0, 'mis_aprobados': 0,
                'mis_certificados': 0,    'participaciones_tecnico': [],
                'tecnico': None,
            })

    return render(request, 'dashboard.html', context)



# CRUD TÉCNICOS

@solo_admin
def listado_tecnicos(request):
    tecnicos = Tecnico.objects.all().order_by('apellidos', 'nombres')
    return render(request, 'tecnicos_crud/listado_tecnicos.html',
                  {'tecnicos': tecnicos})


@solo_admin
def nuevo_tecnico(request):
    if request.method == 'POST':
        # Datos del técnico
        cedula        = request.POST.get('cedula', '').strip()
        nombres       = request.POST.get('nombres', '').strip()
        apellidos     = request.POST.get('apellidos', '').strip()
        correo        = request.POST.get('correo', '').strip()
        telefono      = request.POST.get('telefono', '').strip()
        especialidad  = request.POST.get('especialidad', '').strip()
        institucion   = request.POST.get('institucion', '').strip()
        ciudad        = request.POST.get('ciudad', '').strip()
        fecha_ingreso = request.POST.get('fecha_ingreso', '').strip()
        estado        = request.POST.get('estado', 'Activo')
        foto          = request.FILES.get('foto', None)

        # Datos de acceso (usuario del sistema)
        username  = request.POST.get('username', '').strip()
        password  = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')

        errores = []

        # ── Validaciones datos del técnico ──
        err = _validar_cedula(cedula)
        if err: errores.append(err)

        err = _validar_solo_letras(nombres, 'Los nombres')
        if err: errores.append(err)

        err = _validar_solo_letras(apellidos, 'Los apellidos')
        if err: errores.append(err)

        if not correo:
            errores.append('El correo electrónico es obligatorio.')

        err = _validar_telefono(telefono)
        if err: errores.append(err)

        if not especialidad:
            errores.append('La especialidad es obligatoria.')

        if not institucion or len(institucion) < 3:
            errores.append('La institución debe tener al menos 3 caracteres.')

        if not ciudad or len(ciudad) < 2:
            errores.append('La ciudad debe tener al menos 2 caracteres.')

        err = _validar_fecha_no_futura(fecha_ingreso)
        if err: errores.append(err)

        err = _validar_foto(foto)
        if err: errores.append(err)

        # ── Validaciones de acceso (obligatorias al crear) ──
        if not username or len(username) < 3:
            errores.append('El nombre de usuario debe tener al menos 3 caracteres.')
        elif not re.match(r'^[a-zA-Z0-9_]+$', username):
            errores.append('El usuario solo puede contener letras, números y guión bajo (_).')
        elif User.objects.filter(username=username).exists():
            errores.append('Ese nombre de usuario ya está en uso.')

        if not password or len(password) < 6:
            errores.append('La contraseña debe tener al menos 6 caracteres.')
        elif password != password2:
            errores.append('Las contraseñas no coinciden.')

        # ── Unicidad cédula/correo ──
        if not errores:
            if Tecnico.objects.filter(cedula=cedula).exists():
                errores.append('Ya existe un técnico con esa cédula.')
            if Tecnico.objects.filter(correo=correo).exists():
                errores.append('Ya existe un técnico con ese correo.')

        if errores:
            for e in errores:
                messages.error(request, e)
        else:
            # Crear el usuario Django (no staff)
            user = User.objects.create_user(
                username=username,
                password=password,
                email=correo,
                first_name=nombres,
                last_name=apellidos,
            )
            # Crear el técnico vinculado al usuario
            t = Tecnico(
                usuario=user,
                cedula=cedula, nombres=nombres, apellidos=apellidos,
                correo=correo, telefono=telefono, especialidad=especialidad,
                institucion=institucion, ciudad=ciudad,
                fecha_ingreso=fecha_ingreso, estado=estado,
            )
            if foto:
                t.foto = foto
            t.save()
            messages.success(
                request,
                f'Técnico {nombres} {apellidos} registrado exitosamente. '
                f'Usuario de acceso: {username}'
            )
            return redirect('listado_tecnicos')

    return render(request, 'tecnicos_crud/form_tecnico.html', {
        'tecnico': None,
        'especialidades': Tecnico.ESPECIALIDAD_CHOICES,
    })


@solo_admin
def editar_tecnico(request, pk):
    tecnico = get_object_or_404(Tecnico, pk=pk)

    if request.method == 'POST':
        cedula        = request.POST.get('cedula', '').strip()
        nombres       = request.POST.get('nombres', '').strip()
        apellidos     = request.POST.get('apellidos', '').strip()
        correo        = request.POST.get('correo', '').strip()
        telefono      = request.POST.get('telefono', '').strip()
        especialidad  = request.POST.get('especialidad', '').strip()
        institucion   = request.POST.get('institucion', '').strip()
        ciudad        = request.POST.get('ciudad', '').strip()
        fecha_ingreso = request.POST.get('fecha_ingreso', '').strip()
        estado        = request.POST.get('estado', 'Activo')
        foto          = request.FILES.get('foto', None)

        # Campos de acceso (opcionales en edición)
        username      = request.POST.get('username', '').strip()
        nueva_pass    = request.POST.get('password', '')
        nueva_pass2   = request.POST.get('password2', '')

        errores = []

        err = _validar_cedula(cedula)
        if err: errores.append(err)

        err = _validar_solo_letras(nombres, 'Los nombres')
        if err: errores.append(err)

        err = _validar_solo_letras(apellidos, 'Los apellidos')
        if err: errores.append(err)

        if not correo:
            errores.append('El correo electrónico es obligatorio.')

        err = _validar_telefono(telefono)
        if err: errores.append(err)

        if not especialidad:
            errores.append('La especialidad es obligatoria.')

        if not institucion or len(institucion) < 3:
            errores.append('La institución debe tener al menos 3 caracteres.')

        if not ciudad or len(ciudad) < 2:
            errores.append('La ciudad debe tener al menos 2 caracteres.')

        err = _validar_fecha_no_futura(fecha_ingreso)
        if err: errores.append(err)

        err = _validar_foto(foto)
        if err: errores.append(err)

        # Validar username si se proporcionó
        if username:
            if len(username) < 3:
                errores.append('El nombre de usuario debe tener al menos 3 caracteres.')
            elif not re.match(r'^[a-zA-Z0-9_]+$', username):
                errores.append('El usuario solo puede contener letras, números y guión bajo (_).')
            elif User.objects.filter(username=username).exclude(
                    pk=tecnico.usuario.pk if tecnico.usuario else None).exists():
                errores.append('Ese nombre de usuario ya está en uso.')

        # Validar contraseña si se proporcionó
        if nueva_pass:
            if len(nueva_pass) < 6:
                errores.append('La nueva contraseña debe tener al menos 6 caracteres.')
            elif nueva_pass != nueva_pass2:
                errores.append('Las contraseñas no coinciden.')

        if not errores:
            if Tecnico.objects.filter(cedula=cedula).exclude(pk=pk).exists():
                errores.append('Ya existe otro técnico con esa cédula.')
            if Tecnico.objects.filter(correo=correo).exclude(pk=pk).exists():
                errores.append('Ya existe otro técnico con ese correo.')

        if errores:
            for e in errores:
                messages.error(request, e)
        else:
            # Actualizar o crear el usuario Django
            if tecnico.usuario:
                # Ya tiene usuario — actualizar datos
                user = tecnico.usuario
                if username:
                    user.username = username
                user.first_name = nombres
                user.last_name  = apellidos
                user.email      = correo
                if nueva_pass:
                    user.set_password(nueva_pass)
                user.save()
            else:
                # No tiene usuario — crearlo si se proporcionó username
                if username and nueva_pass:
                    user = User.objects.create_user(
                        username=username,
                        password=nueva_pass,
                        email=correo,
                        first_name=nombres,
                        last_name=apellidos,
                    )
                    tecnico.usuario = user

            # Actualizar el técnico
            tecnico.cedula        = cedula
            tecnico.nombres       = nombres
            tecnico.apellidos     = apellidos
            tecnico.correo        = correo
            tecnico.telefono      = telefono
            tecnico.especialidad  = especialidad
            tecnico.institucion   = institucion
            tecnico.ciudad        = ciudad
            tecnico.fecha_ingreso = fecha_ingreso
            tecnico.estado        = estado
            if foto:
                tecnico.foto = foto
            tecnico.save()
            messages.success(request, f'Técnico {nombres} {apellidos} actualizado exitosamente.')
            return redirect('listado_tecnicos')

    return render(request, 'tecnicos_crud/form_tecnico.html', {
        'tecnico': tecnico,
        'especialidades': Tecnico.ESPECIALIDAD_CHOICES,
    })


@solo_admin
def eliminar_tecnico(request, pk):
    tecnico = get_object_or_404(Tecnico, pk=pk)
    # Validación: no eliminar si tiene participaciones en cursos
    if tecnico.participaciones.exists():
        messages.error(
            request,
            f'El técnico {tecnico.nombre_completo} está inscrito en un curso y no se puede eliminar.'
        )
        return redirect('listado_tecnicos')
    nombre = str(tecnico)
    tecnico.delete()
    messages.success(request, f'Técnico {nombre} eliminado exitosamente.')
    return redirect('listado_tecnicos')


# CRUD CURSOS

@solo_admin
def listado_cursos(request):
    cursos = Curso.objects.all().order_by('fecha_inicio', 'nombre')
    return render(request, 'cursos_crud/listado_cursos.html', {'cursos': cursos})


@solo_admin
def nuevo_curso(request):
    if request.method == 'POST':
        codigo       = request.POST.get('codigo', '').strip()
        nombre       = request.POST.get('nombre', '').strip()
        instructor   = request.POST.get('instructor', '').strip()
        duracion     = request.POST.get('duracion', 0)
        fecha_inicio = request.POST.get('fecha_inicio', '')
        fecha_fin    = request.POST.get('fecha_fin', '')
        modalidad    = request.POST.get('modalidad', 'Presencial')
        cupos        = request.POST.get('cupos', 0)
        descripcion  = request.POST.get('descripcion', '').strip()
        estado       = request.POST.get('estado', 'Activo')

        errores = []
        if Curso.objects.filter(codigo=codigo).exists():
            errores.append('Ya existe un curso con ese código.')
        if fecha_inicio and fecha_fin and fecha_fin <= fecha_inicio:
            errores.append('La fecha de fin debe ser mayor que la fecha de inicio.')
        try:
            dur = int(duracion)
            if dur < 1 or dur > 1000:
                errores.append('La duración debe estar entre 1 y 1000 horas.')
        except (ValueError, TypeError):
            errores.append('La duración debe ser un número entero positivo.')
        try:
            cup = int(cupos)
            if cup < 1 or cup > 500:
                errores.append('Los cupos deben estar entre 1 y 500.')
        except (ValueError, TypeError):
            errores.append('Los cupos deben ser un número entero positivo.')

        if errores:
            for e in errores:
                messages.error(request, e)
        else:
            Curso.objects.create(
                codigo=codigo, nombre=nombre, instructor=instructor,
                duracion=duracion, fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin, modalidad=modalidad,
                cupos=cupos, descripcion=descripcion, estado=estado
            )
            messages.success(request, f'Curso "{nombre}" registrado exitosamente.')
            return redirect('listado_cursos')

    return render(request, 'cursos_crud/form_curso.html', {
        'curso': None,
        'modalidades': Curso.MODALIDAD_CHOICES,
    })


@solo_admin
def editar_curso(request, pk):
    curso = get_object_or_404(Curso, pk=pk)

    if request.method == 'POST':
        codigo       = request.POST.get('codigo', '').strip()
        nombre       = request.POST.get('nombre', '').strip()
        instructor   = request.POST.get('instructor', '').strip()
        duracion     = request.POST.get('duracion', 0)
        fecha_inicio = request.POST.get('fecha_inicio', '')
        fecha_fin    = request.POST.get('fecha_fin', '')
        modalidad    = request.POST.get('modalidad', 'Presencial')
        cupos        = request.POST.get('cupos', 0)
        descripcion  = request.POST.get('descripcion', '').strip()
        estado       = request.POST.get('estado', 'Activo')

        errores = []
        if Curso.objects.filter(codigo=codigo).exclude(pk=pk).exists():
            errores.append('Ya existe otro curso con ese código.')
        if fecha_inicio and fecha_fin and fecha_fin <= fecha_inicio:
            errores.append('La fecha de fin debe ser mayor que la fecha de inicio.')

        # Validaciones de rango (igual que en nuevo_curso)
        try:
            dur = int(duracion)
            if dur < 1 or dur > 1000:
                errores.append('La duración debe estar entre 1 y 1000 horas.')
        except (ValueError, TypeError):
            errores.append('La duración debe ser un número entero positivo.')

        try:
            cup = int(cupos)
            if cup < 1 or cup > 500:
                errores.append('Los cupos deben estar entre 1 y 500.')
        except (ValueError, TypeError):
            errores.append('Los cupos deben ser un número entero positivo.')

        if errores:
            for e in errores:
                messages.error(request, e)
        else:
            curso.codigo = codigo
            curso.nombre = nombre
            curso.instructor = instructor
            curso.duracion = dur
            curso.fecha_inicio = fecha_inicio
            curso.fecha_fin = fecha_fin
            curso.modalidad = modalidad
            curso.cupos = cup
            curso.descripcion = descripcion
            curso.estado = estado
            curso.save()
            messages.success(request, f'Curso "{nombre}" actualizado exitosamente.')
            return redirect('listado_cursos')

    return render(request, 'cursos_crud/form_curso.html', {
        'curso': curso,
        'modalidades': Curso.MODALIDAD_CHOICES,
    })


@solo_admin
def eliminar_curso(request, pk):
    curso = get_object_or_404(Curso, pk=pk)
    # Validación: no eliminar si tiene técnicos inscritos
    if curso.participaciones.exists():
        messages.error(
            request,
            f'El curso "{curso.nombre}" tiene técnicos inscritos y no se puede eliminar.'
        )
        return redirect('listado_cursos')
    nombre = curso.nombre
    curso.delete()
    messages.success(request, f'Curso "{nombre}" eliminado exitosamente.')
    return redirect('listado_cursos')



# CRUD PARTICIPACIONES

@solo_admin
def listado_participaciones(request):
    curso_id = request.GET.get('curso')
    participaciones = Participacion.objects.select_related('tecnico', 'curso').all()
    if curso_id:
        participaciones = participaciones.filter(curso__id=curso_id)
    return render(request, 'participaciones/listado_participaciones.html',
                  {'participaciones': participaciones})


@solo_admin
def nueva_participacion(request):
    if request.method == 'POST':
        tecnico_id = request.POST.get('tecnico')
        curso_id   = request.POST.get('curso')
        nota       = request.POST.get('nota_final', '').strip()

        errores = []
        if Participacion.objects.filter(tecnico_id=tecnico_id, curso_id=curso_id).exists():
            errores.append('Este técnico ya está inscrito en ese curso.')

        nota_val = None
        if nota:
            try:
                nota_val = float(nota)
                if not (0 <= nota_val <= 100):
                    errores.append('La nota debe estar entre 0 y 100.')
            except ValueError:
                errores.append('La nota debe ser un número válido.')

        if errores:
            for e in errores:
                messages.error(request, e)
        else:
            p = Participacion(tecnico_id=tecnico_id, curso_id=curso_id)
            if nota_val is not None:
                p.nota_final = nota_val
            p.save()
            messages.success(request, 'Participación registrada exitosamente.')
            return redirect('listado_participaciones')

    tecnicos = Tecnico.objects.filter(estado='Activo').order_by('apellidos')
    cursos   = Curso.objects.filter(estado='Activo').order_by('nombre')
    return render(request, 'participaciones/form_participacion.html', {
        'participacion': None,
        'tecnicos': tecnicos,
        'cursos': cursos,
    })


@solo_admin
def editar_participacion(request, pk):
    participacion = get_object_or_404(Participacion, pk=pk)

    if request.method == 'POST':
        nota  = request.POST.get('nota_final', '').strip()
        estado = request.POST.get('estado', participacion.estado)

        errores = []
        nota_val = None
        if nota:
            try:
                nota_val = float(nota)
                if not (0 <= nota_val <= 100):
                    errores.append('La nota debe estar entre 0 y 100.')
            except ValueError:
                errores.append('La nota debe ser un número válido.')

        if errores:
            for e in errores:
                messages.error(request, e)
        else:
            if nota_val is not None:
                participacion.nota_final = nota_val
            else:
                participacion.estado = estado
            participacion.save()
            messages.success(request, 'Participación actualizada exitosamente.')
            return redirect('listado_participaciones')

    tecnicos = Tecnico.objects.filter(estado='Activo').order_by('apellidos')
    cursos   = Curso.objects.filter(estado='Activo').order_by('nombre')
    return render(request, 'participaciones/form_participacion.html', {
        'participacion': participacion,
        'tecnicos': tecnicos,
        'cursos': cursos,
    })


@solo_admin
def eliminar_participacion(request, pk):
    participacion = get_object_or_404(Participacion, pk=pk)
    participacion.delete()
    messages.success(request, 'Participación eliminada exitosamente.')
    return redirect('listado_participaciones')


# CERTIFICADOS

import io, qrcode
from django.http import HttpResponse, Http404
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.utils import ImageReader


def _obtener_o_crear_certificado(participacion):
    """Obtiene o crea el certificado de forma segura evitando IntegrityError."""
    # Primero intenta obtenerlo
    try:
        return Certificado.objects.get(participacion=participacion)
    except Certificado.DoesNotExist:
        pass
    # No existe — créalo con código único
    from django.db import IntegrityError as DBIntegrityError
    for _ in range(5):  # hasta 5 intentos
        codigo = _generar_codigo_cert(participacion)
        try:
            cert = Certificado.objects.create(
                participacion=participacion,
                codigo=codigo
            )
            return cert
        except DBIntegrityError:
            continue
    # Último intento con uuid completo
    import uuid
    year = participacion.curso.fecha_fin.year
    cert = Certificado.objects.create(
        participacion=participacion,
        codigo=f'CERT-{year}-{uuid.uuid4().hex[:8].upper()}'
    )
    return cert


def _generar_codigo_cert(participacion):
    """Genera un código único tipo CERT-2026-0001."""
    import uuid
    year  = participacion.curso.fecha_fin.year
    total = Certificado.objects.count() + 1
    codigo = f'CERT-{year}-{total:04d}'
    if Certificado.objects.filter(codigo=codigo).exists():
        codigo = f'CERT-{year}-{uuid.uuid4().hex[:6].upper()}'
    return codigo


def _generar_pdf_certificado(participacion, cert, url_verificacion):
    """
    Genera el PDF del certificado con diseño limpio y moderno.
    Paleta: blanco + azul marino #1E3A5F + verde esmeralda #2ECC71 + gris suave.
    """
    # ── Paleta de colores ──────────────────────────────────────────
    AZUL        = colors.HexColor('#1E3A5F')   # encabezado y textos principales
    VERDE       = colors.HexColor('#2ECC71')   # acento / líneas decorativas
    GRIS_CLARO  = colors.HexColor('#F4F6F9')   # fondo suave del cuerpo
    GRIS_TEXTO  = colors.HexColor('#555555')   # texto secundario
    GRIS_CODIGO = colors.HexColor('#888888')   # texto del código y pie

    # ── QR ────────────────────────────────────────────────────────
    texto_qr = (
        f"TECNICO: {participacion.tecnico.nombre_completo} | "
        f"CEDULA: {participacion.tecnico.cedula} | "
        f"CURSO: {participacion.curso.nombre} | "
        f"DURACION: {participacion.curso.duracion}h | "
        f"INSTRUCTOR: {participacion.curso.instructor} | "
        f"FECHA: {participacion.curso.fecha_fin} | "
        f"NOTA: {participacion.nota_final} | "
        f"ESTADO: Aprobado | "
        f"CODIGO: {cert.codigo}"
    )
    qr_img = qrcode.make(texto_qr)
    qr_buf = io.BytesIO()
    qr_img.save(qr_buf, format='PNG')
    qr_buf.seek(0)

    # ── Canvas A4 horizontal ───────────────────────────────────────
    buf = io.BytesIO()
    w, h = landscape(A4)
    c = rl_canvas.Canvas(buf, pagesize=(w, h))

    # ── FONDO GENERAL blanco ──────────────────────────────────────
    c.setFillColor(colors.white)
    c.rect(0, 0, w, h, fill=1, stroke=0)

    # ── BANDA SUPERIOR azul marino (encabezado) ────────────────────
    banda_h = 3.2 * cm
    c.setFillColor(AZUL)
    c.rect(0, h - banda_h, w, banda_h, fill=1, stroke=0)

    # ── Línea verde bajo la banda ──────────────────────────────────
    c.setStrokeColor(VERDE)
    c.setLineWidth(4)
    c.line(0, h - banda_h, w, h - banda_h)

    # ── Título en la banda ─────────────────────────────────────────
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 26)
    c.drawCentredString(w / 2, h - 2.2 * cm, 'CERTIFICADO DE APROBACIÓN')

    # ── BANDA INFERIOR azul marino (pie) ──────────────────────────
    pie_h = 2.5 * cm
    c.setFillColor(AZUL)
    c.rect(0, 0, w, pie_h, fill=1, stroke=0)

    # ── Línea verde sobre el pie ───────────────────────────────────
    c.setStrokeColor(VERDE)
    c.setLineWidth(3)
    c.line(0, pie_h, w, pie_h)

    # ── FRANJA IZQUIERDA verde (decorativa) ───────────────────────
    c.setFillColor(VERDE)
    c.rect(0, pie_h, 0.6 * cm, h - banda_h - pie_h, fill=1, stroke=0)

    # ── FRANJA DERECHA verde (decorativa) ─────────────────────────
    c.rect(w - 0.6 * cm, pie_h, 0.6 * cm, h - banda_h - pie_h, fill=1, stroke=0)

    # ── FONDO GRIS SUAVE del cuerpo central ───────────────────────
    c.setFillColor(GRIS_CLARO)
    c.rect(0.6 * cm, pie_h, w - 1.2 * cm, h - banda_h - pie_h, fill=1, stroke=0)

    # ── Texto "Se certifica que" ───────────────────────────────────
    y_base = h - banda_h - 1.6 * cm
    c.setFillColor(GRIS_TEXTO)
    c.setFont('Helvetica', 13)
    c.drawCentredString(w / 2, y_base, 'Se certifica que')

    # ── Nombre del técnico ─────────────────────────────────────────
    y_base -= 1.4 * cm
    c.setFillColor(AZUL)
    c.setFont('Helvetica-Bold', 30)
    c.drawCentredString(w / 2, y_base, participacion.tecnico.nombre_completo)

    # Línea decorativa bajo el nombre
    y_base -= 0.5 * cm
    c.setStrokeColor(VERDE)
    c.setLineWidth(2)
    nombre_w = 12 * cm
    c.line(w / 2 - nombre_w / 2, y_base, w / 2 + nombre_w / 2, y_base)

    # ── Cédula ─────────────────────────────────────────────────────
    y_base -= 0.9 * cm
    c.setFillColor(GRIS_TEXTO)
    c.setFont('Helvetica', 11)
    c.drawCentredString(w / 2, y_base,
        f'Cédula: {participacion.tecnico.cedula}')

    # ── "ha aprobado…" ─────────────────────────────────────────────
    y_base -= 1.0 * cm
    c.setFont('Helvetica', 13)
    c.drawCentredString(w / 2, y_base, 'ha completado y aprobado satisfactoriamente el curso')

    # ── Nombre del curso ───────────────────────────────────────────
    y_base -= 1.2 * cm
    c.setFillColor(AZUL)
    c.setFont('Helvetica-Bold', 20)
    c.drawCentredString(w / 2, y_base, f'"{participacion.curso.nombre}"')

    # ── Detalles del curso en una sola línea ──────────────────────
    y_base -= 1.2 * cm
    fecha_str = participacion.curso.fecha_fin.strftime('%d/%m/%Y')
    c.setFillColor(GRIS_TEXTO)
    c.setFont('Helvetica', 11)
    c.drawCentredString(
        w / 2, y_base,
        f'{participacion.curso.duracion} horas   ·   {participacion.curso.modalidad}'
        f'   ·   Finalización: {fecha_str}'
        f'   ·   Nota: {participacion.nota_final}'
    )

    # ── SECCIÓN FIRMA (izquierda) + QR (derecha) ──────────────────
    firma_y_linea = pie_h + 1.8 * cm
    firma_cx      = w / 2 - 6 * cm       # centro de la línea de firma

    c.setStrokeColor(AZUL)
    c.setLineWidth(1)
    c.line(firma_cx - 4 * cm, firma_y_linea, firma_cx + 4 * cm, firma_y_linea)

    c.setFillColor(AZUL)
    c.setFont('Helvetica-Bold', 11)
    c.drawCentredString(firma_cx, firma_y_linea - 0.45 * cm,
                        participacion.curso.instructor)
    c.setFillColor(GRIS_TEXTO)
    c.setFont('Helvetica', 9)
    c.drawCentredString(firma_cx, firma_y_linea - 0.9 * cm, 'Instructor del curso')

    # ── QR (derecha) ──────────────────────────────────────────────
    qr_size = 3.5 * cm
    qr_x    = w - 1.2 * cm - qr_size
    qr_y    = pie_h + 0.3 * cm
    qr_reader = ImageReader(qr_buf)
    c.drawImage(qr_reader, qr_x, qr_y, width=qr_size, height=qr_size)
    c.setFillColor(GRIS_CODIGO)
    c.setFont('Helvetica', 7)
    c.drawCentredString(qr_x + qr_size / 2, qr_y - 0.3 * cm, 'Escanear para verificar')

    # ── Código en el pie ──────────────────────────────────────────
    c.setFillColor(colors.white)
    c.setFont('Helvetica', 9)
    c.drawCentredString(w / 2, 0.9 * cm,
        f'Código: {cert.codigo}   ·   Emitido: {cert.fecha_emision}'
        f'   ·   Verificar en: {url_verificacion}')

    c.save()
    buf.seek(0)
    return buf


@login_required(login_url='/login/')
def generar_certificado(request, pk):
    """Descarga el PDF del certificado."""
    participacion = get_object_or_404(Participacion, pk=pk)

    if participacion.estado != 'Aprobado':
        messages.error(request, 'Solo se pueden generar certificados para participaciones aprobadas.')
        return redirect('dashboard')

    if not request.user.is_staff:
        try:
            if request.user.tecnico != participacion.tecnico:
                raise Http404
        except Tecnico.DoesNotExist:
            raise Http404

    cert = _obtener_o_crear_certificado(participacion)
    url_verificacion = request.build_absolute_uri(f'/verificar/{cert.codigo}/')

    buf = _generar_pdf_certificado(participacion, cert, url_verificacion)
    response = HttpResponse(buf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="certificado_{cert.codigo}.pdf"'
    return response


@login_required(login_url='/login/')
def verificar_certificado(request, codigo):
    """Página pública de verificación del certificado (destino del QR)."""
    import base64
    try:
        cert = Certificado.objects.select_related(
            'participacion__tecnico', 'participacion__curso'
        ).get(codigo=codigo)
        valido = True

        # Generar QR lado servidor
        texto_qr = (
            f"TECNICO: {cert.participacion.tecnico.nombre_completo} | "
            f"CEDULA: {cert.participacion.tecnico.cedula} | "
            f"CURSO: {cert.participacion.curso.nombre} | "
            f"DURACION: {cert.participacion.curso.duracion}h | "
            f"INSTRUCTOR: {cert.participacion.curso.instructor} | "
            f"FECHA: {cert.participacion.curso.fecha_fin} | "
            f"NOTA: {cert.participacion.nota_final} | "
            f"ESTADO: Aprobado | "
            f"CODIGO: {cert.codigo}"
        )
        qr_img = qrcode.make(texto_qr)
        qr_buf = io.BytesIO()
        qr_img.save(qr_buf, format='PNG')
        qr_b64 = base64.b64encode(qr_buf.getvalue()).decode('utf-8')

    except Certificado.DoesNotExist:
        cert   = None
        valido = False
        qr_b64 = None

    return render(request, 'certificados/verificar.html', {
        'cert': cert,
        'valido': valido,
        'codigo': codigo,
        'qr_b64': qr_b64,
    })



# PERFIL DEL TÉCNICO (ver y editar)

@login_required(login_url='/login/')
def perfil_tecnico(request):
    """El técnico ve y edita su propio perfil — todos los campos."""
    try:
        tecnico = request.user.tecnico
    except Tecnico.DoesNotExist:
        messages.error(request, 'No tienes un perfil de técnico asignado.')
        return redirect('dashboard')

    if request.method == 'POST':
        cedula        = request.POST.get('cedula', '').strip()
        nombres       = request.POST.get('nombres', '').strip()
        apellidos     = request.POST.get('apellidos', '').strip()
        correo        = request.POST.get('correo', '').strip()
        telefono      = request.POST.get('telefono', '').strip()
        especialidad  = request.POST.get('especialidad', '').strip()
        institucion   = request.POST.get('institucion', '').strip()
        ciudad        = request.POST.get('ciudad', '').strip()
        fecha_ingreso = request.POST.get('fecha_ingreso', '').strip()
        foto          = request.FILES.get('foto', None)

        errores = []

        err = _validar_cedula(cedula)
        if err: errores.append(err)

        err = _validar_solo_letras(nombres, 'Los nombres')
        if err: errores.append(err)

        err = _validar_solo_letras(apellidos, 'Los apellidos')
        if err: errores.append(err)

        if not correo:
            errores.append('El correo electrónico es obligatorio.')

        err = _validar_telefono(telefono)
        if err: errores.append(err)

        if not especialidad:
            errores.append('La especialidad es obligatoria.')

        if not institucion or len(institucion) < 3:
            errores.append('La institución debe tener al menos 3 caracteres.')

        if not ciudad or len(ciudad) < 2:
            errores.append('La ciudad debe tener al menos 2 caracteres.')

        err = _validar_fecha_no_futura(fecha_ingreso)
        if err: errores.append(err)

        err = _validar_foto(foto)
        if err: errores.append(err)

        if not errores:
            if Tecnico.objects.filter(cedula=cedula).exclude(pk=tecnico.pk).exists():
                errores.append('Ya existe otro técnico con esa cédula.')
            if Tecnico.objects.filter(correo=correo).exclude(pk=tecnico.pk).exists():
                errores.append('Ya existe otro técnico con ese correo.')

        if errores:
            for e in errores:
                messages.error(request, e)
        else:
            tecnico.cedula       = cedula
            tecnico.nombres      = nombres
            tecnico.apellidos    = apellidos
            tecnico.correo       = correo
            tecnico.telefono     = telefono
            tecnico.especialidad = especialidad
            tecnico.institucion  = institucion
            tecnico.ciudad       = ciudad
            tecnico.fecha_ingreso = fecha_ingreso
            if foto:
                tecnico.foto = foto
            tecnico.save()
            messages.success(request, 'Perfil actualizado exitosamente.')
            return redirect('perfil_tecnico')

    return render(request, 'perfil/perfil_tecnico.html', {
        'tecnico': tecnico,
        'especialidades': Tecnico.ESPECIALIDAD_CHOICES,
    })


# PANEL TÉCNICO — self-service

@login_required(login_url='/login/')
def mis_cursos(request):
    """El técnico ve SOLO sus propias participaciones."""
    try:
        tecnico = request.user.tecnico
    except Tecnico.DoesNotExist:
        messages.error(request, 'No tienes un perfil de técnico asignado.')
        return redirect('dashboard')

    participaciones = Participacion.objects.filter(
        tecnico=tecnico).select_related('curso').order_by('-curso__fecha_inicio')

    return render(request, 'tecnico/mis_cursos.html', {
        'participaciones': participaciones,
    })


@login_required(login_url='/login/')
def cursos_inscribir(request):
    """Cursos activos en los que el técnico AÚN no está inscrito."""
    try:
        tecnico = request.user.tecnico
    except Tecnico.DoesNotExist:
        messages.error(request, 'No tienes un perfil de técnico asignado.')
        return redirect('dashboard')

    ya_inscrito_ids = Participacion.objects.filter(
        tecnico=tecnico).values_list('curso_id', flat=True)

    cursos_disponibles = Curso.objects.filter(
        estado='Activo').exclude(id__in=ya_inscrito_ids).order_by('fecha_inicio')

    return render(request, 'tecnico/cursos_inscribir.html', {
        'cursos': cursos_disponibles,
    })


@login_required(login_url='/login/')
def inscribirme(request, curso_id):
    """El técnico se autoinscribe en un curso (POST)."""
    try:
        tecnico = request.user.tecnico
    except Tecnico.DoesNotExist:
        messages.error(request, 'No tienes un perfil de técnico asignado.')
        return redirect('dashboard')

    curso = get_object_or_404(Curso, pk=curso_id, estado='Activo')

    # Verificar cupos disponibles
    inscritos_actuales = curso.participaciones.count()
    if inscritos_actuales >= curso.cupos:
        messages.error(request, f'El curso "{curso.nombre}" ya no tiene cupos disponibles.')
        return redirect('cursos_inscribir')

    if Participacion.objects.filter(tecnico=tecnico, curso=curso).exists():
        messages.warning(request, 'Ya estás inscrito en este curso.')
    else:
        Participacion.objects.create(tecnico=tecnico, curso=curso)
        messages.success(request, f'Te inscribiste en "{curso.nombre}" exitosamente.')

    return redirect('cursos_inscribir')



# CERTIFICADOS — listado admin

@solo_admin
def listado_certificados(request):
    certificados = Certificado.objects.select_related(
        'participacion__tecnico', 'participacion__curso'
    ).order_by('-fecha_emision') if hasattr(Certificado, 'fecha_emision') else Certificado.objects.select_related(
        'participacion__tecnico', 'participacion__curso')

    return render(request, 'certificados/listado.html', {
        'certificados': certificados,
    })


# ═══════════════════════════════════════════════
# REGISTRO PÚBLICO DE TÉCNICO
# ═══════════════════════════════════════════════
def registro_tecnico(request):
    """Registro público: crea usuario Django + Técnico vinculado."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    error_username = None

    if request.method == 'POST':
        cedula        = request.POST.get('cedula', '').strip()
        nombres       = request.POST.get('nombres', '').strip()
        apellidos     = request.POST.get('apellidos', '').strip()
        correo        = request.POST.get('correo', '').strip()
        telefono      = request.POST.get('telefono', '').strip()
        especialidad  = request.POST.get('especialidad', '').strip()
        institucion   = request.POST.get('institucion', '').strip()
        ciudad        = request.POST.get('ciudad', '').strip()
        fecha_ingreso = request.POST.get('fecha_ingreso', '').strip()
        username      = request.POST.get('username', '').strip()
        password      = request.POST.get('password', '')
        password2     = request.POST.get('password2', '')
        foto          = request.FILES.get('foto', None)

        errores = []

        # Validar cédula
        err = _validar_cedula(cedula)
        if err: errores.append(err)

        # Validar nombres y apellidos
        err = _validar_solo_letras(nombres, 'Los nombres')
        if err: errores.append(err)

        err = _validar_solo_letras(apellidos, 'Los apellidos')
        if err: errores.append(err)

        if not correo:
            errores.append('El correo electrónico es obligatorio.')

        # Validar teléfono
        err = _validar_telefono(telefono)
        if err: errores.append(err)

        if not especialidad:
            errores.append('La especialidad es obligatoria.')

        if not institucion or len(institucion) < 3:
            errores.append('La institución debe tener al menos 3 caracteres.')

        if not ciudad or len(ciudad) < 2:
            errores.append('La ciudad debe tener al menos 2 caracteres.')

        # Validar fecha de ingreso
        err = _validar_fecha_no_futura(fecha_ingreso)
        if err: errores.append(err)

        # Validar foto
        err = _validar_foto(foto)
        if err: errores.append(err)

        # Validar usuario y contraseña
        if not username or len(username) < 3:
            error_username = 'El nombre de usuario debe tener al menos 3 caracteres.'
            errores.append(error_username)
        elif not re.match(r'^[a-zA-Z0-9_]+$', username):
            error_username = 'El usuario solo puede contener letras, números y guión bajo (_).'
            errores.append(error_username)
        elif User.objects.filter(username=username).exists():
            error_username = 'Ese nombre de usuario ya está en uso.'
            errores.append(error_username)

        if not password or len(password) < 6:
            errores.append('La contraseña debe tener al menos 6 caracteres.')
        elif password != password2:
            errores.append('Las contraseñas no coinciden.')

        # Unicidad de cédula y correo
        if Tecnico.objects.filter(cedula=cedula).exists():
            errores.append('Ya existe un técnico con esa cédula.')
        if correo and Tecnico.objects.filter(correo=correo).exists():
            errores.append('Ya existe un técnico con ese correo.')

        if errores:
            # Solo mostrar error_username en el campo, los demás como messages
            for e in errores:
                if e != error_username:
                    messages.error(request, e)
            return render(request, 'registro.html', {
                'especialidades': Tecnico.ESPECIALIDAD_CHOICES,
                'form_data': request.POST,
                'error_username': error_username,
            })

        # Crear usuario (no staff)
        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=nombres,
            last_name=apellidos,
            email=correo,
        )

        # Crear técnico vinculado
        t = Tecnico(
            usuario=user,
            cedula=cedula, nombres=nombres, apellidos=apellidos,
            correo=correo, telefono=telefono, especialidad=especialidad,
            institucion=institucion, ciudad=ciudad,
            fecha_ingreso=fecha_ingreso, estado='Activo',
        )
        if foto:
            t.foto = foto
        t.save()

        # Login automático
        from django.contrib.auth import login as auth_login
        auth_login(request, user)

        # ── Email de bienvenida ──
        try:
            from django.core.mail import send_mail
            from django.conf import settings as django_settings
            send_mail(
                subject='Bienvenido/a al Sistema de Técnicos en Tecnología',
                message=(
                    f'Estimado/a {nombres} {apellidos},\n\n'
                    f'Tu cuenta ha sido creada exitosamente.\n\n'
                    f'Datos de acceso:\n'
                    f'  Usuario: {username}\n'
                    f'  Correo:  {correo}\n\n'
                    f'Especialidad: {especialidad}\n'
                    f'Institución:  {institucion}\n\n'
                    f'Ingresa al sistema en: http://127.0.0.1:8000/login/\n\n'
                    f'Sistema de Gestión de Técnicos en Tecnología'
                ),
                from_email=django_settings.DEFAULT_FROM_EMAIL,
                recipient_list=[correo],
                fail_silently=True,
            )
        except Exception:
            pass

        messages.success(request, f'Bienvenido/a {nombres}. Tu cuenta fue creada exitosamente.')
        return redirect('dashboard')

    return render(request, 'registro.html', {
        'especialidades': Tecnico.ESPECIALIDAD_CHOICES,
        'form_data': {},
        'error_username': None,
    })


# ═══════════════════════════════════════════════
# CURSOS DISPONIBLES (para técnico inscribirse)
# ═══════════════════════════════════════════════
@login_required(login_url='/login/')
def cursos_disponibles(request):
    """El técnico ve los cursos activos en los que aún no está inscrito."""
    try:
        tecnico = request.user.tecnico
        inscritos = Participacion.objects.filter(
            tecnico=tecnico
        ).values_list('curso_id', flat=True)
        cursos = Curso.objects.filter(
            estado='Activo'
        ).exclude(id__in=inscritos).order_by('nombre')
    except Tecnico.DoesNotExist:
        cursos = Curso.objects.filter(estado='Activo')
        tecnico = None

    if request.method == 'POST' and tecnico:
        curso_id = request.POST.get('curso_id')
        if curso_id:
            curso = get_object_or_404(Curso, pk=curso_id, estado='Activo')
            # Verificar cupos disponibles
            inscritos_actuales = curso.participaciones.count()
            if inscritos_actuales >= curso.cupos:
                messages.error(request, f'El curso "{curso.nombre}" ya no tiene cupos disponibles.')
            elif not Participacion.objects.filter(tecnico=tecnico, curso=curso).exists():
                Participacion.objects.create(tecnico=tecnico, curso=curso)
                messages.success(request, f'Te has inscrito en "{curso.nombre}" exitosamente.')
            else:
                messages.error(request, 'Ya estás inscrito en ese curso.')
            return redirect('cursos_disponibles')

    return render(request, 'cursos_disponibles.html', {
        'cursos': cursos,
        'tecnico': tecnico,
    })


# ═══════════════════════════════════════════════
# IMPRIMIR CERTIFICADO — mismo PDF que descargar, pero se abre en el navegador
# ═══════════════════════════════════════════════
@login_required(login_url='/login/')
def imprimir_certificado(request, pk):
    """Genera el mismo PDF del certificado y lo muestra inline en el navegador para imprimir."""
    participacion = get_object_or_404(Participacion, pk=pk)

    if participacion.estado != 'Aprobado':
        messages.error(request, 'Solo se pueden imprimir certificados aprobados.')
        return redirect('dashboard')

    if not request.user.is_staff:
        try:
            if request.user.tecnico != participacion.tecnico:
                raise Http404
        except Tecnico.DoesNotExist:
            raise Http404

    cert = _obtener_o_crear_certificado(participacion)
    url_verificacion = request.build_absolute_uri(f'/verificar/{cert.codigo}/')

    # Reutiliza la misma función de generación de PDF
    pdf_buf = _generar_pdf_certificado(participacion, cert, url_verificacion)

    response = HttpResponse(pdf_buf, content_type='application/pdf')
    # inline = abre en el navegador (no descarga)
    response['Content-Disposition'] = f'inline; filename="certificado_{cert.codigo}.pdf"'
    return response


# ═══════════════════════════════════════════════
# REPORTE DE PARTICIPACIONES (ventana de impresión)
# ═══════════════════════════════════════════════
@solo_admin
def reporte_participaciones(request):
    participaciones = Participacion.objects.select_related(
        'tecnico', 'curso'
    ).all().order_by('-fecha_inscripcion')
    return render(request, 'participaciones/reporte_participaciones.html', {
        'participaciones': participaciones,
    })


# ═══════════════════════════════════════════════
# ENVIAR CERTIFICADO POR EMAIL
# ═══════════════════════════════════════════════
@login_required(login_url='/login/')
def enviar_certificado_email(request, pk):
    """Genera el PDF del certificado y lo envía al correo del técnico."""
    from django.core.mail import EmailMessage
    from django.conf import settings as django_settings

    participacion = get_object_or_404(Participacion, pk=pk)

    if participacion.estado != 'Aprobado':
        messages.error(request, 'Solo se pueden enviar certificados de participaciones aprobadas.')
        return redirect('dashboard')

    # Verificar permisos
    if not request.user.is_staff:
        try:
            if request.user.tecnico != participacion.tecnico:
                raise Http404
        except Tecnico.DoesNotExist:
            raise Http404

    cert = _obtener_o_crear_certificado(participacion)

    url_verificacion = request.build_absolute_uri(f'/verificar/{cert.codigo}/')

    # Usar la misma función helper — PDF idéntico al de descargar e imprimir
    buf = _generar_pdf_certificado(participacion, cert, url_verificacion)

    # Enviar email
    correo_tecnico = participacion.tecnico.correo
    nombre_tecnico = participacion.tecnico.nombre_completo
    nombre_curso   = participacion.curso.nombre

    try:
        email = EmailMessage(
            subject=f'Certificado de Aprobación — {nombre_curso}',
            body=(
                f'Estimado/a {nombre_tecnico},\n\n'
                f'Adjunto encontrará su certificado de aprobación del curso "{nombre_curso}".\n\n'
                f'Código de verificación: {cert.codigo}\n'
                f'Puede verificar su certificado en: {url_verificacion}\n\n'
                f'Sistema de Gestión de Técnicos en Tecnología'
            ),
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            to=[correo_tecnico],
        )
        email.attach(
            filename=f'certificado_{cert.codigo}.pdf',
            content=buf.read(),
            mimetype='application/pdf'
        )
        email.send(fail_silently=False)
        messages.success(
            request,
            f'Certificado enviado exitosamente al correo {correo_tecnico}.'
        )
    except Exception as e:
        messages.error(
            request,
            f'No se pudo enviar el correo. Verifica la configuración del servidor de email. Error: {str(e)}'
        )

    # Redirigir según el perfil
    if request.user.is_staff:
        return redirect('listado_participaciones')
    return redirect('dashboard')
