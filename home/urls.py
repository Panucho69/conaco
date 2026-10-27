from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView
from django.urls import path
from . import views

app_name = "home"

urlpatterns = [
    # Páginas públicas
    path("", views.index, name="index"),
    path("contactanos/", views.contactanos, name="contactanos"),
    path("categoria/", views.categoria, name="categoria"),
    path("noticia/", views.noticia, name="noticia"),

    # Cuentas
    path("login/", auth_views.LoginView.as_view(template_name='home/login.html'), name="login"),
    path("logout/", LogoutView.as_view(next_page='home:login'), name="logout"),
    path("sign_up/", views.sign_up, name="sign_up"),

    # Perfil
    path("perfil/", views.perfil, name="perfil"),
    path("crud_perfil/", views.crud_perfil, name="crud_perfil"),
    path("crud_cambiar_contrasena/", views.crud_cambiar_contrasena, name="crud_cambiar_contrasena"),

    # Panel: noticias, comentarios y categorías
    path("crud_noticias/", views.crud_noticias, name="crud_noticias"),
    path("crear_publicacion/", views.crear_publicacion, name="crear_publicacion"),
    path("crud_comentarios/", views.crud_comentarios, name="crud_comentarios"),
    path("crud_categorias/", views.crud_categorias, name="crud_categorias"),
    path("editar_categoria/", views.editar_categoria, name="editar_categoria"),

    # Panel: usuarios
    path("crud_usuarios/", views.crud_usuarios, name="crud_usuarios"),
    path("crud_usuarios/crear/", views.crear_usuario, name="crear_usuario"),
    path("crud_usuarios/<int:pk>/editar/", views.editar_usuario, name="editar_usuario"),
    path("crud_usuarios/<int:pk>/bloquear/", views.bloquear_usuario, name="bloquear_usuario"),
    path("crud_usuarios/<int:pk>/eliminar/", views.eliminar_usuario, name="eliminar_usuario"),
]
