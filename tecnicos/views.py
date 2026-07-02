from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Tecnico, Curso, Participacion, Certificado



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
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'inicio.html')



# LOGIN / LOGOUT

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

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
    return redirect('login')



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
        # Recoger datos
        cedula       = request.POST.get('cedula', '').strip()
        nombres      = request.POST.get('nombres', '').strip()
        apellidos    = request.POST.get('apellidos', '').strip()
        correo       = request.POST.get('correo', '').strip()
        telefono     = request.POST.get('telefono', '').strip()
        especialidad = request.POST.get('especialidad', '').strip()
        institucion  = request.POST.get('institucion', '').strip()
        ciudad       = request.POST.get('ciudad', '').strip()
        fecha_ingreso = request.POST.get('fecha_ingreso', '')
        estado       = request.POST.get('estado', 'Activo')
        foto         = request.FILES.get('foto', None)

        # Validación básica server-side
        errores = []
        if Tecnico.objects.filter(cedula=cedula).exists():
            errores.append('Ya existe un técnico con esa cédula.')
        if Tecnico.objects.filter(correo=correo).exists():
            errores.append('Ya existe un técnico con ese correo.')

        if errores:
            for e in errores:
                messages.error(request, e)
        else:
            t = Tecnico(
                cedula=cedula, nombres=nombres, apellidos=apellidos,
                correo=correo, telefono=telefono, especialidad=especialidad,
                institucion=institucion, ciudad=ciudad,
                fecha_ingreso=fecha_ingreso, estado=estado,
            )
            if foto:
                t.foto = foto
            t.save()
            messages.success(request, f'Técnico {nombres} {apellidos} registrado exitosamente.')
            return redirect('listado_tecnicos')

    return render(request, 'tecnicos_crud/form_tecnico.html', {
        'tecnico': None,
        'especialidades': Tecnico.ESPECIALIDAD_CHOICES,
    })


@solo_admin
def editar_tecnico(request, pk):
    tecnico = get_object_or_404(Tecnico, pk=pk)

    if request.method == 'POST':
        cedula       = request.POST.get('cedula', '').strip()
        nombres      = request.POST.get('nombres', '').strip()
        apellidos    = request.POST.get('apellidos', '').strip()
        correo       = request.POST.get('correo', '').strip()
        telefono     = request.POST.get('telefono', '').strip()
        especialidad = request.POST.get('especialidad', '').strip()
        institucion  = request.POST.get('institucion', '').strip()
        ciudad       = request.POST.get('ciudad', '').strip()
        fecha_ingreso = request.POST.get('fecha_ingreso', '')
        estado       = request.POST.get('estado', 'Activo')
        foto         = request.FILES.get('foto', None)

        errores = []
        if Tecnico.objects.filter(cedula=cedula).exclude(pk=pk).exists():
            errores.append('Ya existe otro técnico con esa cédula.')
        if Tecnico.objects.filter(correo=correo).exclude(pk=pk).exists():
            errores.append('Ya existe otro técnico con ese correo.')

        if errores:
            for e in errores:
                messages.error(request, e)
        else:
            tecnico.cedula = cedula
            tecnico.nombres = nombres
            tecnico.apellidos = apellidos
            tecnico.correo = correo
            tecnico.telefono = telefono
            tecnico.especialidad = especialidad
            tecnico.institucion = institucion
            tecnico.ciudad = ciudad
            tecnico.fecha_ingreso = fecha_ingreso
            tecnico.estado = estado
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

        if errores:
            for e in errores:
                messages.error(request, e)
        else:
            curso.codigo = codigo
            curso.nombre = nombre
            curso.instructor = instructor
            curso.duracion = duracion
            curso.fecha_inicio = fecha_inicio
            curso.fecha_fin = fecha_fin
            curso.modalidad = modalidad
            curso.cupos = cupos
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


def _generar_codigo_cert(participacion):
    """Genera un código único tipo CERT-2026-0001."""
    year  = participacion.curso.fecha_fin.year
    total = Certificado.objects.count() + 1
    return f'CERT-{year}-{total:04d}'


@login_required(login_url='/login/')
def generar_certificado(request, pk):
    """Genera el PDF del certificado y lo guarda en BD si no existe."""
    participacion = get_object_or_404(Participacion, pk=pk)

    # Solo técnicos aprobados
    if participacion.estado != 'Aprobado':
        messages.error(request, 'Solo se pueden generar certificados para participaciones aprobadas.')
        return redirect('dashboard')

    # Verificar permisos: admin o el propio técnico
    if not request.user.is_staff:
        try:
            if request.user.tecnico != participacion.tecnico:
                raise Http404
        except Tecnico.DoesNotExist:
            raise Http404

    # Crear o recuperar certificado
    cert, creado = Certificado.objects.get_or_create(
        participacion=participacion,
        defaults={'codigo': _generar_codigo_cert(participacion)}
    )

    # ── Generar QR ──
    url_verificacion = request.build_absolute_uri(f'/verificar/{cert.codigo}/')
    qr_img = qrcode.make(url_verificacion)
    qr_buf = io.BytesIO()
    qr_img.save(qr_buf, format='PNG')
    qr_buf.seek(0)

    # ── Generar PDF con ReportLab ──
    buf = io.BytesIO()
    w, h = landscape(A4)
    c = rl_canvas.Canvas(buf, pagesize=(w, h))

    # Fondo degradado simulado con rectángulos
    c.setFillColor(colors.HexColor('#1a1a2e'))
    c.rect(0, 0, w, h, fill=1, stroke=0)
    c.setFillColor(colors.HexColor('#16213e'))
    c.rect(0, h * 0.55, w, h * 0.45, fill=1, stroke=0)

    # Borde dorado
    c.setStrokeColor(colors.HexColor('#FFD700'))
    c.setLineWidth(4)
    c.rect(1*cm, 1*cm, w - 2*cm, h - 2*cm, fill=0, stroke=1)
    c.setLineWidth(1.5)
    c.rect(1.3*cm, 1.3*cm, w - 2.6*cm, h - 2.6*cm, fill=0, stroke=1)

    # Título
    c.setFillColor(colors.HexColor('#FFD700'))
    c.setFont('Helvetica-Bold', 36)
    c.drawCentredString(w / 2, h - 3.5*cm, 'CERTIFICADO DE APROBACIÓN')

    # Línea decorativa
    c.setStrokeColor(colors.HexColor('#FFD700'))
    c.setLineWidth(2)
    c.line(3*cm, h - 4.2*cm, w - 3*cm, h - 4.2*cm)

    # Texto "Se certifica que"
    c.setFillColor(colors.white)
    c.setFont('Helvetica', 18)
    c.drawCentredString(w / 2, h - 5.5*cm, 'Se certifica que')

    # Nombre del técnico
    c.setFont('Helvetica-Bold', 28)
    c.setFillColor(colors.HexColor('#FFD700'))
    nombre = participacion.tecnico.nombre_completo
    c.drawCentredString(w / 2, h - 7*cm, nombre)

    # Texto intermedio
    c.setFillColor(colors.white)
    c.setFont('Helvetica', 16)
    c.drawCentredString(w / 2, h - 8.2*cm, 'ha aprobado satisfactoriamente el curso')

    # Nombre del curso
    c.setFont('Helvetica-Bold', 22)
    c.setFillColor(colors.HexColor('#FFD700'))
    c.drawCentredString(w / 2, h - 9.5*cm, f'"{participacion.curso.nombre}"')

    # Detalles
    c.setFillColor(colors.white)
    c.setFont('Helvetica', 14)
    from django.utils.formats import date_format
    fecha_str = participacion.curso.fecha_fin.strftime('%d de %B de %Y')
    c.drawCentredString(w / 2, h - 10.8*cm,
        f'Duración: {participacion.curso.duracion} horas  |  Modalidad: {participacion.curso.modalidad}  |  Fecha: {fecha_str}')

    # Código de verificación
    c.setFont('Helvetica', 12)
    c.setFillColor(colors.HexColor('#aaaaaa'))
    c.drawCentredString(w / 2, h - 11.8*cm, f'Código de verificación: {cert.codigo}')

    # Instructor / firma
    c.setStrokeColor(colors.HexColor('#FFD700'))
    c.setLineWidth(1)
    firma_x = w / 2 - 5*cm
    c.line(firma_x, 3.5*cm, firma_x + 10*cm, 3.5*cm)
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 12)
    c.drawCentredString(w / 2, 3*cm, participacion.curso.instructor)
    c.setFont('Helvetica', 10)
    c.drawCentredString(w / 2, 2.4*cm, 'Instructor del curso')

    # QR
    qr_reader = ImageReader(qr_buf)
    c.drawImage(qr_reader, w - 6*cm, 1.8*cm, width=4.5*cm, height=4.5*cm)
    c.setFillColor(colors.HexColor('#aaaaaa'))
    c.setFont('Helvetica', 8)
    c.drawCentredString(w - 3.75*cm, 1.5*cm, 'Escanea para verificar')

    c.save()
    buf.seek(0)
    response = HttpResponse(buf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="certificado_{cert.codigo}.pdf"'
    return response


@login_required(login_url='/login/')
def verificar_certificado(request, codigo):
    """Página pública de verificación del certificado (destino del QR)."""
    try:
        cert = Certificado.objects.select_related(
            'participacion__tecnico', 'participacion__curso'
        ).get(codigo=codigo)
        valido = True
    except Certificado.DoesNotExist:
        cert   = None
        valido = False

    return render(request, 'certificados/verificar.html', {
        'cert': cert,
        'valido': valido,
        'codigo': codigo,
    })



# PERFIL DEL TÉCNICO (ver y editar)

@login_required(login_url='/login/')
def perfil_tecnico(request):
    """El técnico ve y edita su propio perfil."""
    try:
        tecnico = request.user.tecnico
    except Tecnico.DoesNotExist:
        messages.error(request, 'No tienes un perfil de técnico asignado.')
        return redirect('dashboard')

    if request.method == 'POST':
        telefono    = request.POST.get('telefono', '').strip()
        institucion = request.POST.get('institucion', '').strip()
        ciudad      = request.POST.get('ciudad', '').strip()
        foto        = request.FILES.get('foto', None)

        tecnico.telefono    = telefono
        tecnico.institucion = institucion
        tecnico.ciudad      = ciudad
        if foto:
            tecnico.foto = foto
        tecnico.save()
        messages.success(request, 'Perfil actualizado exitosamente.')
        return redirect('perfil_tecnico')

    return render(request, 'perfil/perfil_tecnico.html', {'tecnico': tecnico})


# REGISTRO PÚBLICO

from django.contrib.auth.models import User

def registro_view(request):
    """Un visitante crea su cuenta de técnico (User + Tecnico)."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username     = request.POST.get('username', '').strip()
        password     = request.POST.get('password', '')
        password2    = request.POST.get('password2', '')
        cedula       = request.POST.get('cedula', '').strip()
        nombres      = request.POST.get('nombres', '').strip()
        apellidos    = request.POST.get('apellidos', '').strip()
        correo       = request.POST.get('correo', '').strip()
        telefono     = request.POST.get('telefono', '').strip()
        especialidad = request.POST.get('especialidad', '').strip()
        institucion  = request.POST.get('institucion', '').strip()
        ciudad       = request.POST.get('ciudad', '').strip()

        errores = []
        if password != password2:
            errores.append('Las contraseñas no coinciden.')
        if User.objects.filter(username=username).exists():
            errores.append('Ese nombre de usuario ya está en uso.')
        if Tecnico.objects.filter(cedula=cedula).exists():
            errores.append('Ya existe un técnico con esa cédula.')
        if Tecnico.objects.filter(correo=correo).exists():
            errores.append('Ya existe un técnico con ese correo.')

        if errores:
            for e in errores:
                messages.error(request, e)
        else:
            user = User.objects.create_user(
                username=username, password=password,
                email=correo, first_name=nombres, last_name=apellidos
            )
            Tecnico.objects.create(
                user=user, cedula=cedula, nombres=nombres, apellidos=apellidos,
                correo=correo, telefono=telefono, especialidad=especialidad,
                institucion=institucion, ciudad=ciudad,
                fecha_ingreso=timezone.localdate(), estado='Activo',
            )
            messages.success(request, 'Cuenta creada exitosamente. Ya puedes iniciar sesión.')
            return redirect('login')

    return render(request, 'registro.html', {
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
        from django.contrib.auth.models import User

        cedula        = request.POST.get('cedula', '').strip()
        nombres       = request.POST.get('nombres', '').strip()
        apellidos     = request.POST.get('apellidos', '').strip()
        correo        = request.POST.get('correo', '').strip()
        telefono      = request.POST.get('telefono', '').strip()
        especialidad  = request.POST.get('especialidad', '').strip()
        institucion   = request.POST.get('institucion', '').strip()
        ciudad        = request.POST.get('ciudad', '').strip()
        fecha_ingreso = request.POST.get('fecha_ingreso', '')
        username      = request.POST.get('username', '').strip()
        password      = request.POST.get('password', '')
        foto          = request.FILES.get('foto', None)

        errores = []

        if Tecnico.objects.filter(cedula=cedula).exists():
            errores.append('Ya existe un técnico con esa cédula.')
        if Tecnico.objects.filter(correo=correo).exists():
            errores.append('Ya existe un técnico con ese correo.')
        if User.objects.filter(username=username).exists():
            error_username = 'Ese nombre de usuario ya está en uso.'
            errores.append(error_username)

        if errores:
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
            if not Participacion.objects.filter(tecnico=tecnico, curso=curso).exists():
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
# IMPRIMIR CERTIFICADO (ventana de impresión)
# ═══════════════════════════════════════════════
@login_required(login_url='/login/')
def imprimir_certificado(request, pk):
    """Vista HTML para imprimir el certificado desde el navegador."""
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

    cert, _ = Certificado.objects.get_or_create(
        participacion=participacion,
        defaults={'codigo': _generar_codigo_cert(participacion)}
    )

    url_verificacion = request.build_absolute_uri(f'/verificar/{cert.codigo}/')
    return render(request, 'certificados/imprimir_certificado.html', {
        'cert': cert,
        'participacion': participacion,
        'url_verificacion': url_verificacion,
    })


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
