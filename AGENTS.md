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
- **Google Analytics (GA4):** `partials/base.html` carga la etiqueta solo si existe la variable `GOOGLE_ANALYTICS_ID`: acepta un ID de medición (`G-...`) o de Tag Manager (`GTM-...`). El sitio usa `G-9F55DW4Q1E`. Se define únicamente en la App Service, no en `.env`, para que las visitas locales no cuenten.
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
- **Contacto:** `home:contactanos` guarda los mensajes en el modelo `MensajeContacto` (tiene un campo trampa `sitio_web` contra spam) y el equipo los lee en `home:crud_mensajes`. El menú lateral muestra cuántos hay sin leer (`mensajes_sin_leer`, del context processor).
- Los archivos subidos se guardan con `guardar_archivo()` en `media/uploads/` y se registran en el modelo `Archivo`; en plantillas se muestran con `archivo.display_url`. La carpeta `media/` no se sube a git.

## Seguridad

- **Contraseñas:** toda contraseña nueva (registro, cambio de contraseña, crear/editar usuario) pasa por `errores_contrasena()` en `home/views.py`, que aplica `AUTH_PASSWORD_VALIDATORS`. No uses `set_password()` ni `create_user()` sin validarla antes.
- **Imágenes subidas:** valida con `errores_imagenes()` (usa `home/seguridad.py`: solo JPG, PNG, GIF o WEBP reales, máximo 5 MB) **antes** de guardar nada.
- **Roles:** un editor (`is_staff`) no puede crear, ascender, editar, bloquear ni eliminar administradores; se revisa con `puede_gestionar()`. Respétalo en vistas nuevas de usuarios.
- **Acciones del panel solo por POST:** cualquier acción que cambie datos (publicar, aprobar, bloquear, eliminar) se hace con un `<form method="post">` con `{% csrf_token %}`, nunca con un enlace `<a href>`. La vista solo actúa si `request.method == 'POST'`.
- **Intentos de inicio de sesión:** `django-axes` bloquea 15 minutos tras 5 fallos con el mismo usuario desde la misma IP (página `home/bloqueado.html`). Para desbloquear: `docker compose exec web python manage.py axes_reset`. La IP real en Azure la calcula `obtener_ip_cliente()`.
- **CSRF fallido:** `CSRF_FAILURE_VIEW` muestra `home/csrf_fallido.html` (página "La página expiró") y registra el motivo, IP, Origin y navegador en el log. Para verlo en vivo: `az webapp log tail -g rg-canaco -n canaco-samuel`.
- **Dependencias:** Django está fijado en la última versión de la rama 4.2 (`4.2.30`). Si Dependabot avisa de vulnerabilidades, sube a la última `4.2.x`; las alertas que solo tienen corrección en 5.x son de GeoDjango, GDAL o la caché de páginas, que el proyecto no usa.
- **Producción:** con `WEBSITE_HOSTNAME` se activan HTTPS obligatorio, cookies seguras y HSTS (30 días). `python manage.py check --deploy` no debe mostrar avisos con esas variables.

## AJAX (CRUD sin recargar la página)

Categorías, comentarios, usuarios, perfil y cambio de contraseña se guardan con `fetch()` sin recargar. Sin JavaScript los mismos formularios siguen funcionando con recarga normal.

- **Plantilla:** pon `data-ajax` al `<form>` (y `data-limpiar` si debe vaciarse al guardar). Un `<a data-modal href="...">` abre esa página dentro de la ventana `#modal-ajax` de `sidebar_base.html`. Lo maneja `static/js/ajax.js`; si agregas HTML con otros medios, llama `Canaco.iniciar(elemento)` para activar las ayudas de `formularios.js`.
- **Vista:** pregunta `es_ajax(request)`. Si es AJAX responde con `respuesta_ajax(request, mensaje, ok=..., campo=..., ...)` en lugar de `messages` + `redirect`; si no, conserva el comportamiento normal. Para un error: `ok=False` y `campo` con el `name` del campo. Para mostrar cambios, el servidor manda el HTML ya renderizado con `html(request, plantilla, contexto)`: `reemplazar={selector: html}`, `contenido={selector: html}`, `agregar={selector: html}`, `quitar=[selectores]`, `textos={selector: texto}` y `cerrar_modal=True`.
- Un GET por AJAX a una página de formulario (`crear_usuario`, `editar_usuario`, `editar_categoria`) devuelve `{"titulo", "html"}` para la ventana modal.
- **Parciales:** las filas y tarjetas que cambian están en `home/templates/home/parciales/` (`fila_categoria`, `fila_usuario`, `tarjeta_comentario`, `filtros_comentarios`, `form_usuario`, `form_categoria`...) y llevan un `id` como `categoria-5` o `usuario-3`. La página y la respuesta AJAX usan **la misma** parcial; si cambias el diseño de una fila, cámbialo ahí. En parciales usa `usuario`, no `user` (Django ya usa `user` para la sesión).

## Plantilla visual (ZenBlog)

El diseño es [ZenBlog](https://bootstrapmade.com/zenblog-bootstrap-blog-template/) (Bootstrap 5.3).

- `static/css/main.css` es el CSS de la plantilla. No lo edites para estilos del proyecto; los colores se cambian en sus variables `:root`.
- Los estilos propios del proyecto (panel, perfil, login, registro) van en `static/css/canaco.css`.
- **Formularios** (login, registro, perfil, contraseña, contacto y panel): cada campo es un `<div class="campo">` con su `<label>` arriba; `campo-icono` agrega un ícono, `campo-clave` el botón del ojo, `campos-dobles` pone dos campos lado a lado y `campo-error` lo marca en rojo. Si un formulario falla, la vista vuelve a mostrarlo con `render` (no `redirect`) pasando `datos` (lo que se escribió) y `campo_error` (el nombre del campo).
- `static/js/formularios.js` (cargado en `base.html`) se activa con atributos: `data-reglas` (requisitos de contraseña en vivo), `data-repite="id"` (aviso de que coinciden), `data-vista-previa="#selector"` (vista previa de imágenes), `data-contador="#selector"` (contador de caracteres) y `data-confirmar="mensaje"` en un `<form>` (pide confirmación antes de borrar).
- **Panel:** cada página empieza con `.panel-cabecera` (título y botón principal), el contenido va en `.panel-tarjeta`, las listas usan `.tabla-panel` (en celular se vuelven tarjetas; pon `data-etiqueta` en cada `<td>`) o `.tarjeta-texto`, los estados `.estado estado-ok|espera|no|neutro` y las acciones de cada fila `.acciones` con botones `.accion` de solo ícono (con `title` y `aria-label`). Botones: `.boton-principal` y `.boton-secundario`. Los avisos se muestran con `{% include 'partials/mensajes.html' %}`.
- Conserva el crédito "Diseñado por BootstrapMade" del footer: lo exige la licencia gratuita.
- Imágenes de ejemplo en `static/img/`. La foto de perfil por defecto es `static/uploads/profile-default.jpg`.

## Convenciones de plantillas

- Las páginas públicas extienden `partials/base.html` y las del panel `partials/sidebar_base.html`. **Todas** llenan `{% block content %}`; además existen `{% block title %}`, `{% block extra_css %}` y `{% block extra_js %}`.
- Enlaces siempre con `{% url 'home:nombre' %}` y archivos con `{% static '...' %}`; nunca rutas escritas a mano.
- Los nombres de rutas están en `home/urls.py` (`app_name = "home"`). La de noticias del panel es `crud_noticias`.
- Las acciones del panel siguen el patrón `crud_<modulo>/<int:pk>/<accion>/` (por ejemplo `crud_noticias/5/editar/`); las que borran (`eliminar_*`) solo actúan con POST. El detalle público de una noticia es `home:noticia_detalle` y el de una categoría `home:categoria_detalle`.
- Las noticias tienen `estado` (`borrador` o `publicado`); en plantillas compara con `noticia.estado == 'publicado'`. Los visitantes solo ven noticias publicadas y comentarios aprobados.
- **Moderación de comentarios:** un comentario nuevo se aprueba solo, salvo que `motivo_revision()` de `home/moderacion.py` detecte groserías, insultos, discriminación, enlaces o todo en mayúsculas: entonces queda `pendiente` y el motivo se guarda en `Comentario.motivo_revision`, que se muestra en el panel. Para cambiar qué se detecta, edita las listas `RAICES` (inicio de palabra) y `PALABRAS` (palabra completa) de ese archivo; normaliza acentos, números en lugar de letras (`p3nd3jo`) y letras repetidas. El menú lateral muestra los pendientes (`comentarios_pendientes`).
- Todas las plantillas reciben `global_categorias` (todas las categorías), `global_recientes` (las 3 noticias publicadas más recientes), `mensajes_sin_leer`, `comentarios_pendientes` y `google_analytics_id` del context processor `home/context_processors.py`. Úsalas en lugar de pasarlas desde cada vista; el header y el footer ya las usan.
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
