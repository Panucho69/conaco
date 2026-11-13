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
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse

from .models import Archivo, Categoria, Comentario, GaleriaPublicacion, MensajeContacto, Perfil, Publicacion
from .moderacion import motivo_revision
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


# AJAX: las páginas del panel envían sus formularios con fetch() (static/js/ajax.js) y la
# vista responde JSON en lugar de redirigir. Sin JavaScript todo funciona con recargas normales.

def es_ajax(request):
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'


def respuesta_ajax(request, mensaje='', ok=True, campo=None, status=None, **cambios):
    """JSON que entiende ajax.js.

    Cambios que aplica en la página (cada uno es {selector CSS: html} o una lista de selectores):
      reemplazar: cambia el elemento completo   contenido: cambia lo de adentro
      agregar:    agrega al final del elemento  quitar:    lista de elementos a borrar
      textos:     cambia solo el texto          cerrar_modal: True para cerrar la ventana
    """
    datos = {'ok': ok, 'mensaje': mensaje, 'campo': campo}
    datos.update(cambios)
    return JsonResponse(datos, status=status or (200 if ok else 400))


def html(request, plantilla, contexto=None):
    return render_to_string(plantilla, contexto or {}, request=request)


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
        contenido = request.POST.get('contenido', '').strip()[:3000]
        if contenido:
            # Se publica solo; si tiene lenguaje ofensivo o enlaces queda pendiente de revisión
            motivo = motivo_revision(contenido)
            Comentario.objects.create(
                publicacion=publicacion, user=request.user, contenido=contenido,
                estado=Comentario.ESTADO_PENDIENTE if motivo else Comentario.ESTADO_APROBADO,
                motivo_revision=motivo,
            )
            if motivo:
                logger.info('Comentario retenido para revisión (%s) de %s en la noticia %s', motivo, request.user.username, publicacion.pk)
                messages.warning(request, 'Tu comentario quedó en revisión: el equipo lo revisará antes de publicarlo. '
                                          'Recuerda que no se permiten groserías, insultos ni enlaces.')
            else:
                messages.success(request, 'Comentario publicado.')
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
            if es_ajax(request):
                return respuesta_ajax(request, error, ok=False, campo=campo)
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

        if es_ajax(request):
            request.user.refresh_from_db()
            return respuesta_ajax(
                request, 'Perfil actualizado.',
                reemplazar={'#menu-usuario': html(request, 'partials/menu_usuario.html')},
                textos={'#header-usuario': user.username},
            )
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
            if es_ajax(request):
                return respuesta_ajax(request, error, ok=False, campo=campo)
            messages.error(request, error)
            return render(request, 'home/crud_cambiar_contrasena.html', {'campo_error': campo})

        user.set_password(nueva)
        user.save()
        update_session_auth_hash(request, user)

        if es_ajax(request):
            return respuesta_ajax(request, 'Contraseña actualizada. Tu sesión sigue abierta.')
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


def filtros_comentarios():
    conteo = {fila['estado']: fila['total'] for fila in Comentario.objects.values('estado').annotate(total=Count('id'))}
    return [
        ('', 'Todos', sum(conteo.values())),
        (Comentario.ESTADO_PENDIENTE, 'Pendientes', conteo.get(Comentario.ESTADO_PENDIENTE, 0)),
        (Comentario.ESTADO_APROBADO, 'Aprobados', conteo.get(Comentario.ESTADO_APROBADO, 0)),
        (Comentario.ESTADO_BLOQUEADO, 'Bloqueados', conteo.get(Comentario.ESTADO_BLOQUEADO, 0)),
    ]


@operador_required
def crud_comentarios(request):
    comentarios = Comentario.objects.select_related('publicacion', 'user').order_by('-createdat')
    filtro = request.GET.get('estado', '')
    if filtro in dict(Comentario.ESTADOS):
        comentarios = comentarios.filter(estado=filtro)
    else:
        filtro = ''
    return render(request, 'home/crud_comentarios.html', {
        'comentarios': comentarios,
        'filtro': filtro,
        'filtros': filtros_comentarios(),
    })


def cambiar_comentario(request, pk, estado=None):
    """Aprueba, bloquea (estado) o elimina (estado=None) un comentario. Solo por POST."""
    comentario = get_object_or_404(Comentario.objects.select_related('publicacion', 'user'), pk=pk)
    filtro = request.POST.get('filtro', '')
    if filtro not in dict(Comentario.ESTADOS):
        filtro = ''

    if request.method != 'POST':
        if es_ajax(request):
            return respuesta_ajax(request, 'Acción no permitida.', ok=False, status=405)
        return redirect('home:crud_comentarios')

    selector = f'#comentario-{comentario.pk}'
    if estado:
        comentario.estado = estado
        comentario.save()
        mensaje = 'Comentario aprobado.' if estado == Comentario.ESTADO_APROBADO else 'Comentario bloqueado.'
    else:
        comentario.delete()
        mensaje = 'Comentario eliminado.'

    if not es_ajax(request):
        url = reverse('home:crud_comentarios')
        return redirect(f'{url}?estado={filtro}' if filtro else url)

    contexto = {'filtro': filtro, 'filtros': filtros_comentarios()}
    pendientes = Comentario.objects.filter(estado=Comentario.ESTADO_PENDIENTE).count()
    aviso = (f'<span class="menu-aviso" id="aviso-comentarios" title="Comentarios por revisar"'
             f'{"" if pendientes else " hidden"}>{pendientes}</span>')
    cambios = {'reemplazar': {
        '#filtros-comentarios': html(request, 'home/parciales/filtros_comentarios.html', contexto),
        '#aviso-comentarios': aviso,
    }}
    # Si el comentario ya no corresponde al filtro que se está viendo, se quita de la lista
    if not estado or (filtro and filtro != estado):
        cambios['quitar'] = [selector]
        quedan = Comentario.objects.filter(estado=filtro).exists() if filtro else Comentario.objects.exists()
        if not quedan:
            cambios['contenido'] = {'#lista-comentarios': html(request, 'home/parciales/comentarios_vacio.html', contexto)}
    else:
        contexto['comentario'] = comentario
        cambios['reemplazar'][selector] = html(request, 'home/parciales/tarjeta_comentario.html', contexto)
    return respuesta_ajax(request, mensaje, **cambios)


@operador_required
def aprobar_comentario(request, pk):
    return cambiar_comentario(request, pk, Comentario.ESTADO_APROBADO)


@operador_required
def bloquear_comentario(request, pk):
    return cambiar_comentario(request, pk, Comentario.ESTADO_BLOQUEADO)


@operador_required
def eliminar_comentario(request, pk):
    return cambiar_comentario(request, pk)


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


def categorias_con_total():
    return Categoria.objects.select_related('fk_user').annotate(total_noticias=Count('publicacion'))


def error_nombre_categoria(nombre, excluir=None):
    if not nombre:
        return 'Escribe el nombre de la categoría.'
    repetidas = Categoria.objects.filter(nombre__iexact=nombre)
    if excluir:
        repetidas = repetidas.exclude(pk=excluir.pk)
    if repetidas.exists():
        return f'Ya existe la categoría "{nombre}".'
    return None


@operador_required
def crud_categorias(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()[:60]
        error = error_nombre_categoria(nombre)
        if error:
            if es_ajax(request):
                return respuesta_ajax(request, error, ok=False, campo='nombre')
            messages.error(request, error)
            return redirect('home:crud_categorias')

        categoria = Categoria.objects.create(nombre=nombre, fk_user=request.user)
        mensaje = f'Categoría "{nombre}" agregada.'
        if es_ajax(request):
            categoria = categorias_con_total().get(pk=categoria.pk)
            return respuesta_ajax(
                request, mensaje,
                agregar={'#lista-categorias': html(request, 'home/parciales/fila_categoria.html', {'categoria': categoria})},
                quitar=['#categorias-vacia'],
            )
        messages.success(request, mensaje)
        return redirect('home:crud_categorias')

    return render(request, 'home/crud_categorias.html', {'categorias': categorias_con_total().order_by('nombre')})


@operador_required
def editar_categoria(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    contexto = {'categoria': categoria, 'ajax': es_ajax(request)}

    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()[:60]
        error = error_nombre_categoria(nombre, excluir=categoria)
        if error:
            if es_ajax(request):
                return respuesta_ajax(request, error, ok=False, campo='nombre')
            messages.error(request, error)
            contexto.update(nombre=nombre, campo_error='nombre')
            return render(request, 'home/editar_categoria.html', contexto)

        categoria.nombre = nombre
        categoria.save()
        mensaje = f'Categoría renombrada a "{nombre}".'
        if es_ajax(request):
            categoria = categorias_con_total().get(pk=categoria.pk)
            return respuesta_ajax(
                request, mensaje, cerrar_modal=True,
                reemplazar={f'#categoria-{categoria.pk}': html(request, 'home/parciales/fila_categoria.html', {'categoria': categoria})},
            )
        messages.success(request, mensaje)
        return redirect('home:crud_categorias')

    if es_ajax(request):
        return JsonResponse({'titulo': 'Cambiar nombre', 'html': html(request, 'home/parciales/form_categoria.html', contexto)})
    return render(request, 'home/editar_categoria.html', contexto)


@operador_required
def eliminar_categoria(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method != 'POST':
        if es_ajax(request):
            return respuesta_ajax(request, 'Acción no permitida.', ok=False, status=405)
        return redirect('home:crud_categorias')

    nombre = categoria.nombre
    categoria.delete()
    mensaje = f'Categoría "{nombre}" eliminada.'
    if es_ajax(request):
        cambios = {'quitar': [f'#categoria-{pk}']}
        if not Categoria.objects.exists():
            cambios['contenido'] = {'#lista-categorias': html(request, 'home/parciales/categorias_vacia.html')}
        return respuesta_ajax(request, mensaje, **cambios)
    messages.success(request, mensaje)
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
    contexto = {'usuario_editado': usuario, 'perfil_editado': perfil, 'ajax': es_ajax(request)}

    if request.method != 'POST':
        if usuario:
            rol = 'administrador' if usuario.is_superuser else 'editor' if usuario.is_staff else 'colaborador'
            contexto['datos'] = {
                'username': usuario.username, 'email': usuario.email, 'first_name': usuario.first_name,
                'apellido_paterno': perfil.apellido_paterno, 'apellido_materno': perfil.apellido_materno, 'rol': rol,
            }
        else:
            contexto['datos'] = {'rol': 'colaborador'}
        if es_ajax(request):
            titulo = f'Editar a {usuario.username}' if usuario else 'Nuevo usuario'
            return JsonResponse({'titulo': titulo, 'html': html(request, 'home/parciales/form_usuario.html', contexto)})
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
        if es_ajax(request):
            return respuesta_ajax(request, error, ok=False, campo=campo)
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
    mensaje = f'Usuario "{usuario.username}" {"creado" if nuevo else "actualizado"}.'
    if es_ajax(request):
        fila = html(request, 'home/parciales/fila_usuario.html', {'usuario': usuario})
        if nuevo:
            return respuesta_ajax(request, mensaje, cerrar_modal=True,
                                  agregar={'#lista-usuarios': fila},
                                  textos={'#total-usuarios': str(User.objects.count())})
        return respuesta_ajax(request, mensaje, cerrar_modal=True, reemplazar={f'#usuario-{usuario.pk}': fila})
    messages.success(request, mensaje)
    return redirect('home:crud_usuarios')


@operador_required
def crear_usuario(request):
    return formulario_usuario(request)


@operador_required
def editar_usuario(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    if not puede_gestionar(request.user, usuario):
        mensaje = 'Solo un administrador puede editar a otro administrador.'
        if es_ajax(request):
            return respuesta_ajax(request, mensaje, ok=False, status=403)
        messages.error(request, mensaje)
        return redirect('home:crud_usuarios')
    return formulario_usuario(request, usuario)


def accion_usuario(request, pk, eliminar=False):
    """Bloquea/desbloquea o elimina una cuenta. Nadie se modifica a sí mismo y un editor no toca administradores."""
    usuario = get_object_or_404(User, pk=pk)
    error = None
    if request.method != 'POST':
        error = 'Acción no permitida.'
    elif usuario == request.user:
        error = 'No puedes bloquear ni eliminar tu propia cuenta.'
    elif not puede_gestionar(request.user, usuario):
        error = 'Solo un administrador puede modificar a otro administrador.'

    if error:
        if es_ajax(request):
            return respuesta_ajax(request, error, ok=False, status=403)
        if request.method == 'POST':
            messages.error(request, error)
        return redirect('home:crud_usuarios')

    if eliminar:
        usuario.delete()
        mensaje = f'Cuenta de {usuario.username} eliminada.'
        cambios = {'quitar': [f'#usuario-{pk}'], 'textos': {'#total-usuarios': str(User.objects.count())}}
    else:
        usuario.is_active = not usuario.is_active
        usuario.save()
        mensaje = f'{usuario.username} {"desbloqueado" if usuario.is_active else "bloqueado"}.'
        cambios = {'reemplazar': {f'#usuario-{pk}': html(request, 'home/parciales/fila_usuario.html', {'usuario': usuario})}}

    if es_ajax(request):
        return respuesta_ajax(request, mensaje, **cambios)
    messages.success(request, mensaje)
    return redirect('home:crud_usuarios')


@operador_required
def bloquear_usuario(request, pk):
    return accion_usuario(request, pk)


@operador_required
def eliminar_usuario(request, pk):
    return accion_usuario(request, pk, eliminar=True)
