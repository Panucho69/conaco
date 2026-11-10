from django.conf import settings

from home.models import Categoria, MensajeContacto, Publicacion


def global_categorias(request):
    return {
        'global_categorias': Categoria.objects.all().order_by('nombre'),
        'global_recientes': Publicacion.objects.filter(estado=Publicacion.ESTADO_PUBLICADO).order_by('-createdat')[:3],
        'google_analytics_id': settings.GOOGLE_ANALYTICS_ID,
        # Solo se consulta si el visitante es del equipo (para el aviso del menú lateral)
        'mensajes_sin_leer': (
            MensajeContacto.objects.filter(leido=False).count
            if request.user.is_authenticated and request.user.is_staff else 0
        ),
    }
