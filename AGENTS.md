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

El proyecto corre en **Docker** (`docker-compose.yml`) con tres servicios:

- `web`: Django en http://localhost:8000. Monta la carpeta del proyecto en `/app`, así que los cambios de código se ven al instante.
- `db`: MariaDB 10.11 con la base `canaco` (usuario `canaco`, contraseña `canaco`; root: `canaco_root`). Desde la Mac se llega por el puerto **3307**.
- `phpmyadmin`: http://localhost:8081.

**Base compartida con Azure.** Si existe el archivo `.env` (no se sube a git), `web` y `phpmyadmin` se conectan a la base MySQL de Azure y las fotos se guardan en Azure Blob Storage: el Docker local y https://canaco-samuel.azurewebsites.net ven **los mismos datos**. Cuidado: lo que borres o cambies en local se refleja en el sitio publicado, y `migrate` en local migra la base de producción. Sin `.env` se usa el servicio `db` local como antes. La función `canaco` autoriza la red actual (rango `x.y.0.0`–`x.y.255.255`, porque el proveedor rota la IP) en el firewall de Azure y guarda la última en `.azure-ip`.

```bash
docker compose up -d          # encender
docker compose down           # apagar (los datos se conservan en el volumen db_data)
docker compose exec web python manage.py <comando>   # migrate, makemigrations, createsuperuser...
docker compose logs -f web    # ver errores de Django
```

- El usuario tiene la función de shell `canaco`, que enciende Docker y abre el sitio.
- Los comandos de `manage.py` se corren **dentro** del contenedor `web` con `docker compose exec web ...`.
- `canaco/settings.py` lee la conexión de las variables `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` y `DB_PORT` (las define `docker-compose.yml`). Sin ellas usa el MySQL de XAMPP (`root` sin contraseña en `127.0.0.1:3306`), que queda como alternativa.
- La primera vez que se crea el volumen, MariaDB importa `docker/initdb/canaco.sql` (respaldo de la base de XAMPP, no se sube a git).
- Superusuario para `/admin`: `superadmin`.
- Después de cambiar `home/models.py`: `docker compose exec web python manage.py makemigrations` y luego `... migrate`.
- Si cambias `requirements.txt`, reconstruye el contenedor: `docker compose up -d --build`.

## Producción (Azure)

La app se va a publicar en Azure App Service (dominio `*.azurewebsites.net`). El código ya está preparado; en tu Mac todo sigue igual porque los valores por defecto son los de desarrollo.

- `canaco/settings.py` lee de variables de entorno: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG` (`False` en producción) y `DB_SSL=true` para Azure Database for MySQL. Azure define `WEBSITE_HOSTNAME` y con eso se agregan solos `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` y el encabezado HTTPS del proxy.
- Dominio propio: el usuario va a usar un dominio de **Namecheap** (el `.me` gratis del GitHub Student Pack) apuntando a la App Service, en un plan B1 o superior (F1 no admite dominios propios). Los dominios se pasan en `DJANGO_CUSTOM_DOMAINS`, separados por coma.
- Los estáticos los sirve **whitenoise** desde `staticfiles/` (`collectstatic`, no se sube a git). No guardes nada a mano en `staticfiles/`; edita `static/`.
- Fotos subidas: si están las variables `AZURE_STORAGE_ACCOUNT` y `AZURE_STORAGE_KEY`, se guardan en Azure Blob Storage (cuenta `canacosamuelmedia`, contenedor público `media`) con `django-storages`; si no, en `media/` local. No uses rutas de disco (`.path`, `os.remove`) con archivos subidos: usa `default_storage` o `archivo.ruta.delete(save=False)`.
- Recursos creados (grupo `rg-canaco`, región `mexicocentral`, la única permitida por Azure for Students con MySQL): App Service `canaco-samuel` (plan `plan-canaco`, B1 Linux, Python 3.12, arranque `sh startup.sh`) MySQL flexible `canaco-samuel-db` (B1ms, MySQL 8) y la cuenta de almacenamiento `canacosamuelmedia`. Las credenciales están en `azure.env` en la carpeta del usuario (no se sube a git).
- Para volver a publicar: desde la carpeta del proyecto, `az webapp deploy -g rg-canaco -n canaco-samuel --src-path paquete.zip --type zip` con un zip de `git archive HEAD` (sin cambios sin guardar ni archivos con credenciales).
- `startup.sh` es el arranque de producción: `migrate`, `collectstatic` y **gunicorn**. Es el `CMD` del `Dockerfile`; `docker-compose.yml` lo reemplaza por `runserver` para desarrollo.
- No crees recursos en Azure sin confirmarlo con el usuario: gastan su crédito de Azure for Students.

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
- Todas las plantillas reciben `global_categorias` (todas las categorías) y `global_recientes` (las 3 noticias publicadas más recientes) del context processor `home/context_processors.py`. Úsalas en lugar de pasarlas desde cada vista; el header y el footer ya las usan.
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
