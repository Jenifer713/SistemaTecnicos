from django.urls import path
from . import views

urlpatterns = [
    # Página pública
    path('',            views.inicio,           name='inicio'),

    # Autenticación
    path('login/',      views.login_view,        name='login'),
    path('logout/',     views.logout_view,       name='logout'),
    path('registro/',   views.registro_tecnico,  name='registro_tecnico'),

    # Dashboard
    path('dashboard/',  views.dashboard,         name='dashboard'),

    # ── CRUD TÉCNICOS ──
    path('tecnicos/',                   views.listado_tecnicos, name='listado_tecnicos'),
    path('tecnicos/nuevo/',             views.nuevo_tecnico,    name='nuevo_tecnico'),
    path('tecnicos/editar/<int:pk>/',   views.editar_tecnico,   name='editar_tecnico'),
    path('tecnicos/eliminar/<int:pk>/', views.eliminar_tecnico, name='eliminar_tecnico'),

    # ── CRUD CURSOS ──
    path('cursos/',                   views.listado_cursos,     name='listado_cursos'),
    path('cursos/nuevo/',             views.nuevo_curso,        name='nuevo_curso'),
    path('cursos/editar/<int:pk>/',   views.editar_curso,       name='editar_curso'),
    path('cursos/eliminar/<int:pk>/', views.eliminar_curso,     name='eliminar_curso'),

    # ── CRUD PARTICIPACIONES ──
    path('participaciones/',                   views.listado_participaciones, name='listado_participaciones'),
    path('participaciones/nueva/',             views.nueva_participacion,     name='nueva_participacion'),
    path('participaciones/editar/<int:pk>/',   views.editar_participacion,    name='editar_participacion'),
    path('participaciones/eliminar/<int:pk>/', views.eliminar_participacion,  name='eliminar_participacion'),

    # ── CERTIFICADOS ──
    path('certificado/generar/<int:pk>/',   views.generar_certificado,       name='generar_certificado'),
    path('certificado/imprimir/<int:pk>/',  views.imprimir_certificado,      name='imprimir_certificado'),
    path('certificado/enviar/<int:pk>/',    views.enviar_certificado_email,  name='enviar_certificado_email'),
    path('verificar/<str:codigo>/',         views.verificar_certificado,     name='verificar_certificado'),
    path('reporte-participaciones/',        views.reporte_participaciones,   name='reporte_participaciones'),

    # ── PERFIL TÉCNICO ──
    path('perfil/', views.perfil_tecnico, name='perfil_tecnico'),

    # ── CURSOS DISPONIBLES (técnico) ──
    path('cursos-disponibles/', views.cursos_disponibles, name='cursos_disponibles'),
]
