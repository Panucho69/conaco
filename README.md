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

Las rutas de plantillas de los labs 07 son relativas a `home/templates/`.

| Lab | Tema | Dónde está |
|---|---|---|
| 03 | Creación del proyecto y entorno virtual | `canaco/`, `manage.py`, `requirements.txt` |
| 04 | Configuración de `settings.py` (idioma, static, media, login) | `canaco/settings.py` |
| 05 | App `home`: vistas, rutas y plantillas | `home/views.py`, `home/urls.py`, `home/templates/home/` |
| 06 | Configuración de templates (base, header, footer) y assets | `home/templates/partials/`, `home/templates/home/index.html`, `static/` |
| 07 | Plantillas de noticia, categoría, login y registro | `home/noticia.html`, `home/categoria.html`, `home/login.html`, `home/sign_up.html` |
| 07A | Panel de administración (menú lateral) y perfil | `partials/sidebar_base.html`, `partials/sidebar.html`, `home/perfil.html`, `home/crud_perfil.html` |
| 07B | CRUDs del panel: noticias, comentarios, categorías, usuarios y contraseña | `home/crud_noticias.html`, `home/crear_publicacion.html`, `home/crud_comentarios.html`, `home/crud_categorias.html`, `home/crud_usuarios.html`, `home/crear_usuario.html`, `home/crud_cambiar_contrasena.html` |

## Cómo correrlo

```bash
python3 -m venv canaco_env
source canaco_env/bin/activate
pip install -r requirements.txt
python manage.py runserver
```

Luego abre `http://localhost:8000/`.
