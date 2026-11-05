# Canaco

Blog/CMS construido con **Django 4.2** como parte de los laboratorios de la materia *Tópicos — Desarrollo Web con Django* (TecNM).

## Estructura del proyecto

```
conaco/
├── canaco/            # Configuración (settings.py, urls.py, wsgi/asgi)
├── home/              # App principal
│   ├── templates/
│   │   ├── partials/  # base, header, footer, sidebar_base, sidebar
│   │   └── home/      # Una plantilla por página (index, login, perfil, CRUDs…)
│   ├── urls.py        # Rutas de la app
│   └── views.py       # Vistas
├── static/            # Plantilla ZenBlog (css/main.css, js/, vendor/, img/) y css/canaco.css
├── manage.py
├── requirements.txt
└── README.md
```

## Plantilla

El diseño usa [ZenBlog](https://bootstrapmade.com/zenblog-bootstrap-blog-template/) de BootstrapMade (Bootstrap 5.3). La licencia gratuita pide conservar el crédito "Diseñado por BootstrapMade" en el footer.

- `static/css/main.css`: estilos de la plantilla (colores y fuentes al inicio del archivo, en `:root`).
- `static/css/canaco.css`: estilos propios del proyecto (panel, perfil, login y registro).

## Avance por laboratorio

Las rutas de plantillas que empiezan con `home/` o `partials/` (labs 07 en adelante) son relativas a `home/templates/`.

| Lab | Tema | Dónde está |
|---|---|---|
| 03 | Creación del proyecto y entorno virtual | `canaco/`, `manage.py`, `requirements.txt` |
| 04 | Configuración de `settings.py` (idioma, static, media, login) | `canaco/settings.py` |
| 05 | App `home`: vistas, rutas y plantillas | `home/views.py`, `home/urls.py`, `home/templates/home/` |
| 06 | Configuración de templates (base, header, footer) y assets | `home/templates/partials/`, `home/templates/home/index.html`, `static/` |
| 07 | Plantillas de noticia, categoría, login y registro | `home/noticia.html`, `home/categoria.html`, `home/login.html`, `home/sign_up.html` |
| 07A | Panel de administración (menú lateral) y perfil | `partials/sidebar_base.html`, `partials/sidebar.html`, `home/perfil.html`, `home/crud_perfil.html` |
| 07B | CRUDs del panel: noticias, comentarios, categorías, usuarios y contraseña | `home/crud_noticias.html`, `home/crear_publicacion.html`, `home/crud_comentarios.html`, `home/crud_categorias.html`, `home/crud_usuarios.html`, `home/crear_usuario.html`, `home/crud_cambiar_contrasena.html` |
| 08 | Base de datos MySQL (XAMPP), migraciones y modelos | `canaco/settings.py`, `home/models.py`, `home/migrations/` |
| 10 | Registro, login/logout, perfil, cambio de contraseña y CRUD de usuarios con roles | `home/views.py`, `home/urls.py`, `home/signals.py`, `home/apps.py` |
| 11 | CRUD de noticias (portada y galería), comentarios con moderación y categorías | `home/views.py`, `home/urls.py`, `home/noticia.html`, `home/editar_categoria.html` |
| 12 | Inicio y página de categorías con datos reales | `home/views.py`, `home/index.html`, `home/categoria.html` |
| 13 | Context processor: categorías y noticias recientes en todas las páginas | `home/context_processors.py`, `canaco/settings.py`, `partials/footer.html`, `partials/header.html` |

## Cómo correrlo

Con [Docker Desktop](https://www.docker.com/products/docker-desktop/) encendido:

```bash
docker compose up -d
```

- Sitio: http://localhost:8000
- phpMyAdmin: http://localhost:8081

Para apagarlo: `docker compose down`. Los datos de la base se conservan.

Los comandos de Django se corren dentro del contenedor, por ejemplo:

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

Si cambia `requirements.txt`, reconstruye con `docker compose up -d --build`.

### Producción (Azure)

En producción la app arranca con `startup.sh` (migraciones, `collectstatic` y gunicorn) y se configura con variables de entorno:

| Variable | Valor |
|---|---|
| `DJANGO_SECRET_KEY` | Una clave larga y secreta |
| `DJANGO_DEBUG` | `False` |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Datos del servidor MySQL de Azure |
| `DB_SSL` | `true` |
| `DJANGO_CUSTOM_DOMAINS` | Dominio propio, por ejemplo `canaco.me,www.canaco.me` |

Azure define `WEBSITE_HOSTNAME`, y con ella Django acepta el dominio `*.azurewebsites.net`.

### Sin Docker (XAMPP)

Con el MySQL de XAMPP encendido y la base `canaco` creada:

```bash
python3 -m venv canaco_env
source canaco_env/bin/activate
pip install -r requirements.txt
python manage.py runserver
```
