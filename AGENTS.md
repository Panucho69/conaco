# Instrucciones para agentes de código

Este archivo lo leen los asistentes de programación (Codex, Claude, etc.) antes de trabajar en el proyecto. Responde siempre en español.

## Qué es el proyecto

Canaco es un blog/CMS hecho con **Django 4.2** para los laboratorios de la materia *Tópicos — Desarrollo Web con Django* (TecNM). Se avanza un laboratorio a la vez, siguiendo los PDFs del curso.

## Estructura

```
conaco/
├── canaco/        # Configuración: settings.py, urls.py
├── home/          # App principal: models.py, views.py, urls.py, templates/
│   └── templates/
│       ├── partials/  # base, header, footer, sidebar_base, sidebar
│       └── home/      # Una plantilla por página
├── static/        # Plantilla ZenBlog + css/canaco.css
├── manage.py
└── canaco_env/    # Entorno virtual (no se sube a git)
```

`manage.py` está en la raíz. Todos los comandos se corren desde la carpeta principal, sin entrar a subcarpetas.

## Cómo correrlo

```bash
source canaco_env/bin/activate
python manage.py runserver
```

- Base de datos: **MySQL de XAMPP**, base `canaco`, usuario `root` sin contraseña, `HOST` `127.0.0.1` (no `localhost`: en Mac, `localhost` busca un socket que XAMPP no usa). Antes de correr el proyecto, el MySQL de XAMPP tiene que estar encendido.
- Superusuario para `/admin`: `superadmin`.
- Después de cambiar `home/models.py`: `python manage.py makemigrations` y luego `python manage.py migrate`.

## Usuarios y permisos

- Cada `User` tiene un `Perfil` (apellidos y foto). Se crea solo con la signal de `home/signals.py`; en las vistas usa `Perfil.objects.get_or_create(user=...)` por si el usuario es anterior a la signal.
- Roles: **colaborador** (usuario normal), **editor** (`is_staff`) y **administrador** (`is_superuser`).
- Vistas que requieren sesión: `@login_required`. Vistas del panel de administración (noticias, comentarios, categorías, usuarios): `@operador_required`, definido en `home/views.py` (usuario staff y activo).
- El menú lateral solo muestra las opciones de administración a usuarios staff.
- Login y logout usan las vistas de Django (`LoginView`, `LogoutView`); el logout se hace con un formulario POST a `home:logout`.
- Los archivos subidos se guardan con `guardar_archivo()` en `media/uploads/` y se registran en el modelo `Archivo`; en plantillas se muestran con `archivo.display_url`. La carpeta `media/` no se sube a git.

## Plantilla visual (ZenBlog)

El diseño es [ZenBlog](https://bootstrapmade.com/zenblog-bootstrap-blog-template/) (Bootstrap 5.3).

- `static/css/main.css` es el CSS de la plantilla. No lo edites para estilos del proyecto; los colores se cambian en sus variables `:root`.
- Los estilos propios del proyecto (panel, perfil, login, registro) van en `static/css/canaco.css`.
- Conserva el crédito "Diseñado por BootstrapMade" del footer: lo exige la licencia gratuita.
- Imágenes de ejemplo en `static/img/`. La foto de perfil por defecto es `static/uploads/profile-default.jpg`.

## Convenciones de plantillas

- Las páginas públicas extienden `partials/base.html` y las del panel `partials/sidebar_base.html`. **Todas** llenan `{% block content %}`; además existen `{% block title %}`, `{% block extra_css %}` y `{% block extra_js %}`.
- Enlaces siempre con `{% url 'home:nombre' %}` y archivos con `{% static '...' %}`; nunca rutas escritas a mano.
- Los nombres de rutas están en `home/urls.py` (`app_name = "home"`). La de noticias del panel es `crud_noticias`.
- Las acciones del panel siguen el patrón `crud_<modulo>/<int:pk>/<accion>/` (por ejemplo `crud_noticias/5/editar/`); las que borran (`eliminar_*`) solo actúan con POST. El detalle público de una noticia es `home:noticia_detalle` y el de una categoría `home:categoria_detalle`.
- Las noticias tienen `estado` (`borrador` o `publicado`); en plantillas compara con `noticia.estado == 'publicado'`. Los visitantes solo ven noticias publicadas y comentarios aprobados.
- El menú lateral marca la opción activa comparando `request.resolver_match.url_name`; si agregas una página del panel, agrega su nombre a la condición del enlace correspondiente en `partials/sidebar.html`.

## Laboratorios nuevos

Los PDFs traen el HTML con las clases de la plantilla anterior (Blogy: `post-entry-alt`, `home-carousel`, `account-card`, etc.). Al implementar un laboratorio:

1. Copia la lógica de Django tal cual (`{% for %}`, `{% if %}`, `{% url %}`, `{{ variables }}`, vistas, rutas, modelos).
2. Acomódala en el HTML de ZenBlog que ya tiene la página, en lugar de pegar el HTML de Blogy.
3. Corrige los errores típicos del texto copiado del PDF: palabras pegadas (`btnsm` → `btn-sm`, `profilephoto` → `profile-photo`) e indentación perdida en Python.
4. Prueba que todas las páginas respondan antes de hacer commit.

## Git

- **Nunca agregues líneas de coautor ni menciones de herramientas de IA** en commits o pull requests (nada de `Co-Authored-By`, "Generated with…", etc.).
- Un commit por laboratorio, con mensaje en español, por ejemplo `Laboratorio 09: ...`.
- Rama principal: `main`, remoto `origin` (GitHub).
- No subas `canaco_env/`, `db.sqlite3` ni `.env` (ya están en `.gitignore`).

## Trabajo junto con otros asistentes

En este proyecto también trabaja otro asistente. Antes de editar, revisa `git status` y `git log -3` para ver si hay cambios recientes o sin guardar, y no deshagas cambios que no hiciste tú.
