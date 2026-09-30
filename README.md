# Canaco

Blog/CMS construido con **Django 4.2** como parte de los laboratorios de la materia *Tópicos — Desarrollo Web con Django* (TecNM).

## Estructura del proyecto

```
.
├── canaco/                    # Proyecto Django
│   ├── canaco/                # Configuración (settings, urls, wsgi/asgi)
│   ├── home/                  # App principal
│   │   ├── templates/
│   │   │   ├── partials/      # base, header, footer, sidebar_base, sidebar
│   │   │   └── home/          # Una plantilla por página (index, login, perfil, CRUDs…)
│   │   ├── urls.py            # Rutas de la app
│   │   └── views.py           # Vistas
│   ├── static/                # CSS, JS, imágenes y fuentes de la plantilla
│   └── manage.py
├── requirements.txt
└── README.md
```

## Avance por laboratorio

Las rutas de plantillas de los labs 07 son relativas a `canaco/home/templates/`.

| Lab | Tema | Dónde está |
|---|---|---|
| 03 | Creación del proyecto y entorno virtual | `canaco/`, `requirements.txt` |
| 04 | Configuración de `settings.py` (idioma, static, media, login) | `canaco/canaco/settings.py` |
| 05 | App `home`: vistas, rutas y plantillas | `canaco/home/views.py`, `canaco/home/urls.py`, `canaco/home/templates/home/` |
| 06 | Configuración de templates (base, header, footer) y assets | `canaco/home/templates/partials/`, `canaco/home/templates/home/index.html`, `canaco/static/` |
| 07 | Plantillas de noticia, categoría, login y registro | `home/noticia.html`, `home/categoria.html`, `home/login.html`, `home/sign_up.html` |
| 07A | Panel de administración (menú lateral) y perfil | `partials/sidebar_base.html`, `partials/sidebar.html`, `home/perfil.html`, `home/crud_perfil.html` |
| 07B | CRUDs del panel: noticias, comentarios, categorías, usuarios y contraseña | `home/crud_noticias.html`, `home/crear_publicacion.html`, `home/crud_comentarios.html`, `home/crud_categorias.html`, `home/crud_usuarios.html`, `home/crear_usuario.html`, `home/crud_cambiar_contrasena.html` |

## Cómo correrlo

```bash
python3 -m venv canaco_env
source canaco_env/bin/activate
pip install -r requirements.txt
cd canaco
python manage.py runserver
```

Luego abre `http://localhost:8000/`.
