import logging

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render

from .models import Archivo, Categoria, Comentario, GaleriaPublicacion, Perfil, Publicacion
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
    return render(request, 'home/contactanos.html')


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

        if not username:
            messages.error(request, 'El usuario es obligatorio.')
            return redirect('home:sign_up')

        if password1 != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
            return redirect('home:sign_up')

        error = errores_contrasena(password1, User(username=username, email=email, first_name=first_name))
        if error:
            messages.error(request, error)
            return redirect('home:sign_up')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'El nombre de usuario ya está en uso.')
            return redirect('home:sign_up')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'El correo electrónico ya está registrado.')
            return redirect('home:sign_up')

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

        if not username:
            messages.error(request, 'El usuario es obligatorio.')
            return redirect('home:crud_perfil')
        error = errores_imagenes(foto)
        if error:
            messages.error(request, error)
            return redirect('home:crud_perfil')
        if User.objects.filter(username=username).exclude(pk=user.pk).exists():
            messages.error(request, 'Ese nombre de usuario ya está en uso.')
            return redirect('home:crud_perfil')

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

    return render(request, 'home/crud_perfil.html', {'perfil_usuario': perfil})


@login_required
def crud_cambiar_contrasena(request):
    if request.method == 'POST':
        actual = request.POST.get('actual')
        nueva = request.POST.get('nueva')
        confirmar = request.POST.get('confirmar')

        user = request.user

        if not user.check_password(actual):
            messages.error(request, 'La contraseña actual es incorrecta.')
            return redirect('home:crud_cambiar_contrasena')

        if nueva != confirmar:
            messages.error(request, 'Las nuevas contraseñas no coinciden.')
            return redirect('home:crud_cambiar_contrasena')

        error = errores_contrasena(nueva, user)
        if error:
            messages.error(request, error)
            return redirect('home:crud_cambiar_contrasena')

        user.set_password(nueva)
        user.save()
        update_session_auth_hash(request, user)

        messages.success(request, 'Contraseña actualizada correctamente.')
        return redirect('home:crud_cambiar_contrasena')

    return render(request, 'home/crud_cambiar_contrasena.html')


# Panel de administración (solo operadores: usuarios staff activos)

@operador_required
def crud_noticias(request):
    publicaciones = Publicacion.objects.select_related('categoria', 'autor').order_by('-createdat')
    return render(request, 'home/crud_noticias.html', {'publicaciones': publicaciones})


@operador_required
def crear_publicacion(request):
    categorias = Categoria.objects.all().order_by('nombre')
    if request.method == 'POST':
        error = errores_imagenes(request.FILES.get('imagen_portada'), *request.FILES.getlist('galeria'))
        if error:
            messages.error(request, error)
            return redirect('home:crear_publicacion')
        publicacion = Publicacion.objects.create(
            titulo=request.POST.get('titulo', '').strip(),
            resumen=request.POST.get('resumen', '').strip(),
            contenido=request.POST.get('contenido', '').strip(),
            categoria_id=request.POST.get('categoria') or None,
            estado=request.POST.get('estado') or Publicacion.ESTADO_BORRADOR,
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
    return render(request, 'home/crear_publicacion.html', {'categorias': categorias})


@operador_required
def editar_publicacion(request, pk):
    publicacion = get_object_or_404(Publicacion, pk=pk)
    categorias = Categoria.objects.all().order_by('nombre')
    if request.method == 'POST':
        error = errores_imagenes(request.FILES.get('imagen_portada'), *request.FILES.getlist('galeria'))
        if error:
            messages.error(request, error)
            return redirect('home:editar_publicacion', pk=publicacion.pk)
        publicacion.titulo = request.POST.get('titulo', '').strip()
        publicacion.resumen = request.POST.get('resumen', '').strip()
        publicacion.contenido = request.POST.get('contenido', '').strip()
        publicacion.categoria_id = request.POST.get('categoria') or None
        publicacion.estado = request.POST.get('estado') or Publicacion.ESTADO_BORRADOR
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
    return render(request, 'home/crud_comentarios.html', {'comentarios': comentarios})


@operador_required
def aprobar_comentario(request, pk):
    comentario = get_object_or_404(Comentario, pk=pk)
    if request.method == 'POST':
        comentario.estado = Comentario.ESTADO_APROBADO
        comentario.save()
    return redirect('home:crud_comentarios')


@operador_required
def bloquear_comentario(request, pk):
    comentario = get_object_or_404(Comentario, pk=pk)
    if request.method == 'POST':
        comentario.estado = Comentario.ESTADO_BLOQUEADO
        comentario.save()
    return redirect('home:crud_comentarios')


@operador_required
def eliminar_comentario(request, pk):
    comentario = get_object_or_404(Comentario, pk=pk)
    if request.method == 'POST':
        comentario.delete()
    return redirect('home:crud_comentarios')


@operador_required
def crud_categorias(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        if nombre:
            Categoria.objects.create(nombre=nombre, fk_user=request.user)
            messages.success(request, 'Categoría agregada correctamente.')
        return redirect('home:crud_categorias')
    categorias = Categoria.objects.all().order_by('-createdat')
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


@operador_required
def crear_usuario(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        apellido_paterno = request.POST.get('apellido_paterno', '').strip()
        apellido_materno = request.POST.get('apellido_materno', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        if not username or not password1:
            messages.error(request, 'Usuario y contraseña son obligatorios.')
            return redirect('home:crear_usuario')
        if password1 != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
            return redirect('home:crear_usuario')
        if User.objects.filter(username=username).exists():
            messages.error(request, 'El usuario ya existe.')
            return redirect('home:crear_usuario')
        if request.POST.get('rol') == 'administrador' and not request.user.is_superuser:
            messages.error(request, 'Solo un administrador puede crear otros administradores.')
            return redirect('home:crear_usuario')
        error = errores_contrasena(password1, User(username=username, email=email, first_name=first_name))
        if error:
            messages.error(request, error)
            return redirect('home:crear_usuario')

        user = User.objects.create_user(username=username, email=email, password=password1)
        user.first_name = first_name
        user.last_name = ' '.join(filter(None, [apellido_paterno, apellido_materno]))
        rol = request.POST.get('rol')
        user.is_staff = rol in ['editor', 'administrador']
        user.is_superuser = rol == 'administrador'
        user.save()
        perfil, _ = Perfil.objects.get_or_create(user=user)
        perfil.apellido_paterno = apellido_paterno
        perfil.apellido_materno = apellido_materno
        perfil.save()
        messages.success(request, 'Usuario creado correctamente.')
        return redirect('home:crud_usuarios')

    return render(request, 'home/crear_usuario.html')


@operador_required
def editar_usuario(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    if not puede_gestionar(request.user, usuario):
        messages.error(request, 'Solo un administrador puede editar a otro administrador.')
        return redirect('home:crud_usuarios')
    perfil, _ = Perfil.objects.get_or_create(user=usuario)
    if request.method == 'POST':
        if request.POST.get('rol') == 'administrador' and not request.user.is_superuser:
            messages.error(request, 'Solo un administrador puede asignar el rol de administrador.')
            return redirect('home:editar_usuario', pk=usuario.pk)
        usuario.username = request.POST.get('username', usuario.username).strip()
        usuario.email = request.POST.get('email', usuario.email).strip()
        usuario.first_name = request.POST.get('first_name', usuario.first_name).strip()
        perfil.apellido_paterno = request.POST.get('apellido_paterno', perfil.apellido_paterno).strip()
        perfil.apellido_materno = request.POST.get('apellido_materno', perfil.apellido_materno).strip()
        usuario.last_name = ' '.join(filter(None, [perfil.apellido_paterno, perfil.apellido_materno]))
        rol = request.POST.get('rol')
        if rol:
            usuario.is_staff = rol in ['editor', 'administrador']
            usuario.is_superuser = rol == 'administrador'
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        if password1 or password2:
            if password1 != password2:
                messages.error(request, 'Las contraseñas no coinciden.')
                return redirect('home:editar_usuario', pk=usuario.pk)
            error = errores_contrasena(password1, usuario)
            if error:
                messages.error(request, error)
                return redirect('home:editar_usuario', pk=usuario.pk)
            usuario.set_password(password1)
        usuario.save()
        perfil.save()
        messages.success(request, 'Usuario actualizado correctamente.')
        return redirect('home:crud_usuarios')
    return render(request, 'home/crear_usuario.html', {
        'usuario_editado': usuario,
        'perfil_editado': perfil,
    })


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
