import logging

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.core.files.storage import default_storage
from django.db.models import Count, F
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .models import Archivo, Categoria, Comentario, GaleriaPublicacion, MensajeContacto, Perfil, Publicacion
from .seguridad import obtener_ip_cliente, validar_imagen

logger = logging.getLogger(__name__)


def es_operador(user):
    return user.is_authenticated and user.is_staff and user.is_active


operador_required = user_passes_test(es_operador, login_url='home:login')


def puede_gestionar(actor, usuario):
    # Solo un administrador puede modificar, bloquear o eliminar a otro administrador
    return actor.is_superuser or not usuario.is_superuser


def errores_contrasena(password, user=None):
    # Aplica las reglas de AUTH_PASSWORD_VALIDATORS (largo mínimo, no muy común, etc.)
    try:
        validate_password(password, user)
    except ValidationError as error:
        return ' '.join(error.messages)
    return None


def errores_imagenes(*uploads):
    for upload in uploads:
        if upload:
            error = validar_imagen(upload)
            if error:
                return error
    return None


def guardar_archivo(upload, user):
    filename = default_storage.save(f"uploads/{upload.name}", upload)
    return Archivo.objects.create(
        nombre=upload.name,
        nombre_temporal=filename,
        ruta=filename,
        tipo=upload.content_type,
        tamano=upload.size,
        fk_user=user,
    )


# Páginas públicas

def index(request):
    publicaciones = Publicacion.objects.filter(
        estado=Publicacion.ESTADO_PUBLICADO,
    ).select_related('categoria', 'autor', 'imagen_portada').order_by('-createdat')
    return render(request, 'home/index.html', {
        'slider': publicaciones[:3],
        'publicaciones': publicaciones[:3],
    })


def contactanos(request):
    if request.method == 'POST':
        datos = {campo: request.POST.get(campo, '').strip() for campo in ('nombre', 'correo', 'asunto', 'mensaje')}

        # Campo trampa: invisible para las personas, los robots de spam lo llenan
        if request.POST.get('sitio_web'):
            return redirect('home:contactanos')

        error, campo = None, None
        if not datos['nombre']:
            error, campo = 'Escribe tu nombre.', 'nombre'
        else:
            try:
                validate_email(datos['correo'])
            except ValidationError:
                error, campo = 'Escribe un correo válido para poder responderte.', 'correo'
        if not error and len(datos['mensaje']) < 10:
            error, campo = 'Cuéntanos un poco más: el mensaje debe tener al menos 10 caracteres.', 'mensaje'

        if error:
            messages.error(request, error)
            return render(request, 'home/contactanos.html', {'datos': datos, 'campo_error': campo})

        MensajeContacto.objects.create(
            nombre=datos['nombre'][:120],
            correo=datos['correo'],
            asunto=datos['asunto'][:150],
            mensaje=datos['mensaje'][:5000],
        )
        messages.success(request, 'Mensaje enviado. Te responderemos a tu correo.')
        return redirect('home:contactanos')

    datos = {}
    if request.user.is_authenticated:
        datos = {'nombre': request.user.get_full_name(), 'correo': request.user.email}
    return render(request, 'home/contactanos.html', {'datos': datos})


def csrf_fallido(request, reason=''):
    # Reemplaza la página amarilla de Django (CSRF_FAILURE_VIEW) y deja el motivo en los logs de Azure
    logger.warning(
        'CSRF fallido en %s %s: %s | ip=%s origin=%s referer=%s cookie_csrf=%s navegador=%s',
        request.method, request.path, reason, obtener_ip_cliente(request),
        request.META.get('HTTP_ORIGIN', '-'), 'sí' if request.META.get('HTTP_REFERER') else 'no',
        'sí' if 'csrftoken' in request.COOKIES else 'no', request.META.get('HTTP_USER_AGENT', '-')[:120],
    )
    return render(request, 'home/csrf_fallido.html', status=403)


def categoria(request, pk=None):
    categorias = Categoria.objects.all().order_by('nombre')
    categoria_actual = get_object_or_404(Categoria, pk=pk) if pk else None
    publicaciones = Publicacion.objects.filter(estado=Publicacion.ESTADO_PUBLICADO).select_related(
        'categoria', 'autor', 'imagen_portada',
    )
    if categoria_actual:
        publicaciones = publicaciones.filter(categoria=categoria_actual)
    return render(request, 'home/categoria.html', {
        'categorias': categorias,
        'categoria_actual': categoria_actual,
        'publicaciones': publicaciones.order_by('-createdat'),
    })


def noticia(request, pk=None):
    if pk and es_operador(request.user):
        qs = Publicacion.objects.all()
    else:
        qs = Publicacion.objects.filter(estado=Publicacion.ESTADO_PUBLICADO)

    qs = qs.select_related('categoria', 'autor', 'imagen_portada')
    publicacion = get_object_or_404(qs, pk=pk) if pk else qs.order_by('-createdat').first()
    if not publicacion:
        messages.info(request, 'Todavía no hay noticias publicadas.')
        return redirect('home:index')

    Publicacion.objects.filter(pk=publicacion.pk).update(visitas=F('visitas') + 1)
    publicacion.refresh_from_db()

    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, 'Debes iniciar sesión para comentar.')
            return redirect('home:login')
        contenido = request.POST.get('contenido', '').strip()
        if contenido:
            Comentario.objects.create(publicacion=publicacion, user=request.user, contenido=contenido)
            messages.success(request, 'Comentario enviado. Será visible cuando lo apruebe el administrador.')
        return redirect('home:noticia_detalle', pk=publicacion.pk)

    recientes = Publicacion.objects.filter(
        estado=Publicacion.ESTADO_PUBLICADO,
    ).exclude(pk=publicacion.pk).order_by('-createdat')[:4]
    comentarios = publicacion.comentarios.filter(
        estado=Comentario.ESTADO_APROBADO,
    ).select_related('user').order_by('-createdat')
    categorias = Categoria.objects.all().order_by('nombre')

    return render(request, 'home/noticia.html', {
        'publicacion': publicacion,
        'recientes': recientes,
        'comentarios': comentarios,
        'categorias': categorias,
    })


def sign_up(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        apellido_paterno = request.POST.get('apellido_paterno', '').strip()
        apellido_materno = request.POST.get('apellido_materno', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        # Si algo falla se vuelve a mostrar el formulario con lo que ya escribió (menos las contraseñas)
        error, campo = None, None
        if not username:
            error, campo = 'Escribe un nombre de usuario.', 'username'
        elif User.objects.filter(username=username).exists():
            error, campo = 'Ese nombre de usuario ya está en uso. Prueba con otro.', 'username'
        elif email and User.objects.filter(email=email).exists():
            error, campo = 'Ya hay una cuenta con ese correo. Inicia sesión o usa otro correo.', 'email'
        elif password1 != password2:
            error, campo = 'Las contraseñas no coinciden.', 'password2'
        else:
            error = errores_contrasena(password1, User(username=username, email=email, first_name=first_name))
            campo = 'password1' if error else None

        if error:
            messages.error(request, error)
            return render(request, 'home/sign_up.html', {
                'datos': request.POST,
                'campo_error': campo,
            })

        user = User.objects.create_user(username=username, email=email, password=password1)
        user.first_name = first_name
        user.last_name = ' '.join(filter(None, [apellido_paterno, apellido_materno]))
        user.save()
        perfil, _ = Perfil.objects.get_or_create(user=user)
        perfil.apellido_paterno = apellido_paterno
        perfil.apellido_materno = apellido_materno
        perfil.save()
        messages.success(request, 'Tu cuenta ha sido creada con éxito. Ahora puedes iniciar sesión.')
        return redirect('home:login')

    return render(request, 'home/sign_up.html')


# Perfil del usuario (cualquier usuario con sesión iniciada)

@login_required
def perfil(request):
    perfil_usuario, _ = Perfil.objects.get_or_create(user=request.user)
    return render(request, 'home/perfil.html', {'perfil_usuario': perfil_usuario})


@login_required
def crud_perfil(request):
    user = request.user
    perfil, _ = Perfil.objects.get_or_create(user=user)

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        apellido_paterno = request.POST.get('apellido_paterno', '').strip()
        apellido_materno = request.POST.get('apellido_materno', '').strip()
        foto = request.FILES.get('foto')

        error, campo = None, None
        if not username:
            error, campo = 'Escribe un nombre de usuario.', 'username'
        elif User.objects.filter(username=username).exclude(pk=user.pk).exists():
            error, campo = 'Ese nombre de usuario ya está en uso. Prueba con otro.', 'username'
        elif email and User.objects.filter(email=email).exclude(pk=user.pk).exists():
            error, campo = 'Ya hay otra cuenta con ese correo.', 'email'
        else:
            error = errores_imagenes(foto)
            campo = 'foto' if error else None

        if error:
            messages.error(request, error)
            return render(request, 'home/crud_perfil.html', {
                'perfil_usuario': perfil,
                'datos': request.POST,
                'campo_error': campo,
            })

        user.username = username
        if email:
            user.email = email
        user.first_name = first_name
        user.last_name = ' '.join(filter(None, [apellido_paterno, apellido_materno]))
        user.save()

        perfil.apellido_paterno = apellido_paterno
        perfil.apellido_materno = apellido_materno

        if foto:
            if perfil.foto_perfil:
                archivo_anterior = perfil.foto_perfil
                # Borra el archivo en el almacenamiento que esté configurado (disco local o Azure)
                if archivo_anterior.ruta and not str(archivo_anterior.ruta).startswith('uploads/profile-default'):
                    archivo_anterior.ruta.delete(save=False)
                archivo_anterior.delete()

            perfil.foto_perfil = guardar_archivo(foto, user)

        perfil.save()

        messages.success(request, 'Perfil actualizado correctamente.')
        return redirect('home:perfil')

    return render(request, 'home/crud_perfil.html', {
        'perfil_usuario': perfil,
        'datos': {
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'apellido_paterno': perfil.apellido_paterno,
            'apellido_materno': perfil.apellido_materno,
        },
    })


@login_required
def crud_cambiar_contrasena(request):
    if request.method == 'POST':
        actual = request.POST.get('actual')
        nueva = request.POST.get('nueva')
        confirmar = request.POST.get('confirmar')

        user = request.user

        error, campo = None, None
        if not user.check_password(actual):
            error, campo = 'La contraseña actual no es correcta.', 'actual'
        elif nueva != confirmar:
            error, campo = 'Las contraseñas nuevas no coinciden.', 'confirmar'
        else:
            error = errores_contrasena(nueva, user)
            campo = 'nueva' if error else None

        if error:
            messages.error(request, error)
            return render(request, 'home/crud_cambiar_contrasena.html', {'campo_error': campo})

        user.set_password(nueva)
        user.save()
        update_session_auth_hash(request, user)

        messages.success(request, 'Contraseña actualizada correctamente.')
        return redirect('home:crud_cambiar_contrasena')

    return render(request, 'home/crud_cambiar_contrasena.html')


# Panel de administración (solo operadores: usuarios staff activos)

@operador_required
def crud_noticias(request):
    publicaciones = Publicacion.objects.select_related('categoria', 'autor', 'imagen_portada').order_by('-createdat')
    return render(request, 'home/crud_noticias.html', {'publicaciones': publicaciones})


def datos_publicacion(request):
    """Lee el formulario de noticias y devuelve (datos, mensaje de error, campo con error)."""
    datos = {
        'titulo': request.POST.get('titulo', '').strip(),
        'resumen': request.POST.get('resumen', '').strip(),
        'contenido': request.POST.get('contenido', '').strip(),
        'categoria': request.POST.get('categoria', ''),
        'estado': request.POST.get('estado') or Publicacion.ESTADO_BORRADOR,
    }
    if not datos['titulo']:
        return datos, 'Escribe el título de la noticia.', 'titulo'
    if not datos['resumen']:
        return datos, 'Escribe un resumen: es lo que se ve en la portada y en las categorías.', 'resumen'
    error = errores_imagenes(request.FILES.get('imagen_portada'), *request.FILES.getlist('galeria'))
    if error:
        return datos, error + ' Vuelve a elegir las imágenes.', 'imagenes'
    return datos, None, None


@operador_required
def crear_publicacion(request):
    categorias = Categoria.objects.all().order_by('nombre')
    if request.method == 'POST':
        datos, error, campo = datos_publicacion(request)
        if error:
            messages.error(request, error)
            return render(request, 'home/crear_publicacion.html', {
                'categorias': categorias, 'datos': datos, 'campo_error': campo,
            })
        publicacion = Publicacion.objects.create(
            titulo=datos['titulo'],
            resumen=datos['resumen'],
            contenido=datos['contenido'],
            categoria_id=datos['categoria'] or None,
            estado=datos['estado'],
            autor=request.user,
        )
        portada = request.FILES.get('imagen_portada')
        if portada:
            publicacion.imagen_portada = guardar_archivo(portada, request.user)
            publicacion.save()
        for imagen in request.FILES.getlist('galeria'):
            GaleriaPublicacion.objects.create(publicacion=publicacion, archivo=guardar_archivo(imagen, request.user))
        messages.success(request, 'Publicación creada correctamente.')
        return redirect('home:crud_noticias')
    return render(request, 'home/crear_publicacion.html', {
        'categorias': categorias,
        'datos': {'estado': Publicacion.ESTADO_BORRADOR},
    })


@operador_required
def editar_publicacion(request, pk):
    publicacion = get_object_or_404(Publicacion, pk=pk)
    categorias = Categoria.objects.all().order_by('nombre')
    if request.method == 'POST':
        datos, error, campo = datos_publicacion(request)
        if error:
            messages.error(request, error)
            return render(request, 'home/crear_publicacion.html', {
                'categorias': categorias, 'publicacion': publicacion, 'datos': datos, 'campo_error': campo,
            })
        publicacion.titulo = datos['titulo']
        publicacion.resumen = datos['resumen']
        publicacion.contenido = datos['contenido']
        publicacion.categoria_id = datos['categoria'] or None
        publicacion.estado = datos['estado']
        portada = request.FILES.get('imagen_portada')
        if portada:
            publicacion.imagen_portada = guardar_archivo(portada, request.user)
        publicacion.save()
        for imagen in request.FILES.getlist('galeria'):
            GaleriaPublicacion.objects.create(publicacion=publicacion, archivo=guardar_archivo(imagen, request.user))
        messages.success(request, 'Publicación actualizada correctamente.')
        return redirect('home:crud_noticias')
    return render(request, 'home/crear_publicacion.html', {
        'categorias': categorias,
        'publicacion': publicacion,
        'datos': {
            'titulo': publicacion.titulo,
            'resumen': publicacion.resumen,
            'contenido': publicacion.contenido,
            'categoria': str(publicacion.categoria_id or ''),
            'estado': publicacion.estado,
        },
    })


@operador_required
def publicar_publicacion(request, pk):
    publicacion = get_object_or_404(Publicacion, pk=pk)
    if request.method == 'POST':
        publicacion.estado = Publicacion.ESTADO_PUBLICADO if publicacion.estado != Publicacion.ESTADO_PUBLICADO else Publicacion.ESTADO_BORRADOR
        publicacion.save()
    return redirect('home:crud_noticias')


@operador_required
def eliminar_publicacion(request, pk):
    publicacion = get_object_or_404(Publicacion, pk=pk)
    if request.method == 'POST':
        publicacion.delete()
        messages.success(request, 'Publicación eliminada correctamente.')
    return redirect('home:crud_noticias')


@operador_required
def crud_comentarios(request):
    comentarios = Comentario.objects.select_related('publicacion', 'user').order_by('-createdat')
    conteo = {fila['estado']: fila['total'] for fila in comentarios.order_by().values('estado').annotate(total=Count('id'))}
    filtro = request.GET.get('estado', '')
    if filtro in dict(Comentario.ESTADOS):
        comentarios = comentarios.filter(estado=filtro)
    else:
        filtro = ''
    return render(request, 'home/crud_comentarios.html', {
        'comentarios': comentarios,
        'filtro': filtro,
        'filtros': [
            ('', 'Todos', sum(conteo.values())),
            (Comentario.ESTADO_PENDIENTE, 'Pendientes', conteo.get(Comentario.ESTADO_PENDIENTE, 0)),
            (Comentario.ESTADO_APROBADO, 'Aprobados', conteo.get(Comentario.ESTADO_APROBADO, 0)),
            (Comentario.ESTADO_BLOQUEADO, 'Bloqueados', conteo.get(Comentario.ESTADO_BLOQUEADO, 0)),
        ],
    })


def volver_a_comentarios(request):
    estado = request.POST.get('filtro', '')
    url = reverse('home:crud_comentarios')
    return redirect(f'{url}?estado={estado}' if estado in dict(Comentario.ESTADOS) else url)


@operador_required
def aprobar_comentario(request, pk):
    comentario = get_object_or_404(Comentario, pk=pk)
    if request.method == 'POST':
        comentario.estado = Comentario.ESTADO_APROBADO
        comentario.save()
    return volver_a_comentarios(request)


@operador_required
def bloquear_comentario(request, pk):
    comentario = get_object_or_404(Comentario, pk=pk)
    if request.method == 'POST':
        comentario.estado = Comentario.ESTADO_BLOQUEADO
        comentario.save()
    return volver_a_comentarios(request)


@operador_required
def eliminar_comentario(request, pk):
    comentario = get_object_or_404(Comentario, pk=pk)
    if request.method == 'POST':
        comentario.delete()
    return volver_a_comentarios(request)


@operador_required
def crud_mensajes(request):
    mensajes_contacto = MensajeContacto.objects.order_by('leido', '-createdat')
    return render(request, 'home/crud_mensajes.html', {'mensajes_contacto': mensajes_contacto})


@operador_required
def leer_mensaje(request, pk):
    mensaje = get_object_or_404(MensajeContacto, pk=pk)
    if request.method == 'POST':
        mensaje.leido = not mensaje.leido
        mensaje.save()
    return redirect('home:crud_mensajes')


@operador_required
def eliminar_mensaje(request, pk):
    mensaje = get_object_or_404(MensajeContacto, pk=pk)
    if request.method == 'POST':
        mensaje.delete()
        messages.success(request, 'Mensaje eliminado.')
    return redirect('home:crud_mensajes')


@operador_required
def crud_categorias(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        if not nombre:
            messages.error(request, 'Escribe el nombre de la categoría.')
        elif Categoria.objects.filter(nombre__iexact=nombre).exists():
            messages.error(request, f'Ya existe la categoría "{nombre}".')
        else:
            Categoria.objects.create(nombre=nombre[:60], fk_user=request.user)
            messages.success(request, f'Categoría "{nombre}" agregada.')
        return redirect('home:crud_categorias')
    categorias = Categoria.objects.select_related('fk_user').annotate(
        total_noticias=Count('publicacion'),
    ).order_by('nombre')
    return render(request, 'home/crud_categorias.html', {'categorias': categorias})


@operador_required
def editar_categoria(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        if nombre:
            categoria.nombre = nombre
            categoria.save()
            messages.success(request, 'Categoría actualizada correctamente.')
        return redirect('home:crud_categorias')
    return render(request, 'home/editar_categoria.html', {'categoria': categoria})


@operador_required
def eliminar_categoria(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        categoria.delete()
        messages.success(request, 'Categoría eliminada correctamente.')
    return redirect('home:crud_categorias')


@operador_required
def crud_usuarios(request):
    for usuario in User.objects.all():
        Perfil.objects.get_or_create(user=usuario)
    usuarios = User.objects.select_related('perfil').order_by('date_joined')
    return render(request, 'home/crud_usuarios.html', {'usuarios': usuarios})


def formulario_usuario(request, usuario=None):
    """Crea (usuario=None) o edita una cuenta desde el panel. Si algo falla, vuelve a mostrar lo escrito."""
    perfil = Perfil.objects.get_or_create(user=usuario)[0] if usuario else None
    contexto = {'usuario_editado': usuario, 'perfil_editado': perfil}

    if request.method != 'POST':
        if usuario:
            rol = 'administrador' if usuario.is_superuser else 'editor' if usuario.is_staff else 'colaborador'
            contexto['datos'] = {
                'username': usuario.username, 'email': usuario.email, 'first_name': usuario.first_name,
                'apellido_paterno': perfil.apellido_paterno, 'apellido_materno': perfil.apellido_materno, 'rol': rol,
            }
        else:
            contexto['datos'] = {'rol': 'colaborador'}
        return render(request, 'home/crear_usuario.html', contexto)

    datos = {campo: request.POST.get(campo, '').strip() for campo in (
        'username', 'email', 'first_name', 'apellido_paterno', 'apellido_materno', 'rol')}
    if datos['rol'] not in ('colaborador', 'editor', 'administrador'):
        datos['rol'] = 'colaborador'
    password1 = request.POST.get('password1', '')
    password2 = request.POST.get('password2', '')
    otros = User.objects.exclude(pk=usuario.pk) if usuario else User.objects.all()

    error, campo = None, None
    if not datos['username']:
        error, campo = 'Escribe un nombre de usuario.', 'username'
    elif otros.filter(username=datos['username']).exists():
        error, campo = 'Ese nombre de usuario ya está en uso.', 'username'
    elif datos['email'] and otros.filter(email=datos['email']).exists():
        error, campo = 'Ya hay otra cuenta con ese correo.', 'email'
    elif datos['rol'] == 'administrador' and not request.user.is_superuser:
        error, campo = 'Solo un administrador puede asignar el rol de administrador.', 'rol'
    elif not usuario and not password1:
        error, campo = 'Escribe una contraseña para la cuenta nueva.', 'password1'
    elif (password1 or password2) and password1 != password2:
        error, campo = 'Las contraseñas no coinciden.', 'password2'
    elif password1:
        error = errores_contrasena(password1, usuario or User(
            username=datos['username'], email=datos['email'], first_name=datos['first_name']))
        campo = 'password1' if error else None

    if error:
        messages.error(request, error)
        contexto.update(datos=datos, campo_error=campo)
        return render(request, 'home/crear_usuario.html', contexto)

    nuevo = usuario is None
    if nuevo:
        usuario = User()
    usuario.username = datos['username']
    usuario.email = datos['email']
    usuario.first_name = datos['first_name']
    usuario.last_name = ' '.join(filter(None, [datos['apellido_paterno'], datos['apellido_materno']]))
    usuario.is_staff = datos['rol'] in ('editor', 'administrador')
    usuario.is_superuser = datos['rol'] == 'administrador'
    if password1:
        usuario.set_password(password1)
    usuario.save()
    perfil = perfil or Perfil.objects.get_or_create(user=usuario)[0]
    perfil.apellido_paterno = datos['apellido_paterno']
    perfil.apellido_materno = datos['apellido_materno']
    perfil.save()
    messages.success(request, f'Usuario "{usuario.username}" {"creado" if nuevo else "actualizado"}.')
    return redirect('home:crud_usuarios')


@operador_required
def crear_usuario(request):
    return formulario_usuario(request)


@operador_required
def editar_usuario(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    if not puede_gestionar(request.user, usuario):
        messages.error(request, 'Solo un administrador puede editar a otro administrador.')
        return redirect('home:crud_usuarios')
    return formulario_usuario(request, usuario)


@operador_required
def bloquear_usuario(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    if request.method == 'POST' and usuario != request.user and puede_gestionar(request.user, usuario):
        usuario.is_active = not usuario.is_active
        usuario.save()
    return redirect('home:crud_usuarios')


@operador_required
def eliminar_usuario(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    if request.method == 'POST' and usuario != request.user and puede_gestionar(request.user, usuario):
        usuario.delete()
    return redirect('home:crud_usuarios')
