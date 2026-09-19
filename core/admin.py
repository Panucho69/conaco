from django.contrib import admin

from .models import Archivo, Categoria, Comentario, GaleriaPublicacion, Perfil, Publicacion

admin.site.register(Archivo)
admin.site.register(Perfil)
admin.site.register(Categoria)
admin.site.register(Publicacion)
admin.site.register(GaleriaPublicacion)
admin.site.register(Comentario)
