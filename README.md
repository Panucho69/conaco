# Canaco

Blog/CMS construido con **Django 4.2** como parte de los laboratorios de la materia *Tópicos — Desarrollo Web con Django* (TecNM).

## Estructura del proyecto

```
.
├── canaco/                    # Proyecto Django
│   ├── canaco/                # Configuración (settings, urls, wsgi/asgi)
│   ├── home/                  # App principal
│   │   ├── templates/
│   │   │   ├── partials/      # base.html, header.html, footer.html
│   │   │   └── home/          # Una plantilla por página (index, login, perfil, CRUDs…)
│   │   ├── urls.py            # Rutas de la app
│   │   └── views.py           # Vistas
│   ├── static/                # CSS, JS, imágenes y fuentes de la plantilla
│   └── manage.py
├── requirements.txt
└── README.md
```

## Avance por laboratorio

| Lab | Tema | Dónde está |
|---|---|---|
| 03 | Creación del proyecto y entorno virtual | `canaco/`, `requirements.txt` |
| 04 | Configuración de `settings.py` (idioma, static, media, login) | `canaco/canaco/settings.py` |
| 05 | App `home`: vistas, rutas y plantillas | `canaco/home/views.py`, `canaco/home/urls.py`, `canaco/home/templates/home/` |
| 06 | Configuración de templates (base, header, footer) y assets | `canaco/home/templates/partials/`, `canaco/home/templates/home/index.html`, `canaco/static/` |

## Cómo correrlo

```bash
python3 -m venv canaco_env
source canaco_env/bin/activate
pip install -r requirements.txt
cd canaco
python manage.py runserver
```

Luego abre `http://localhost:8000/`.
