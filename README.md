# Conaco

Aplicación web construida con **Django** para la gestión de un blog/CMS: publicaciones, categorías, comentarios, galería de imágenes y perfiles de usuario.

## Descripción

Conaco permite administrar contenido editorial de un sitio web: los usuarios pueden crear publicaciones (con estado de borrador o publicado), organizarlas por categorías, adjuntarles una galería de imágenes y recibir comentarios moderables. Cada usuario cuenta con un perfil extendido con foto y datos adicionales.

## Tecnologías

- **Python** / **Django 4.2**
- **MariaDB** (`mysqlclient`) como motor de base de datos
- **python-decouple** para el manejo de variables de entorno

## Modelos principales

| Modelo | Descripción |
|---|---|
| `Archivo` | Archivos subidos al sistema (imágenes, documentos), asociados a un usuario. |
| `Perfil` | Datos extendidos del usuario (apellidos, foto de perfil). |
| `Categoria` | Categorías para clasificar las publicaciones. |
| `Publicacion` | Entradas del blog, con título, resumen, contenido, categoría, autor, imagen de portada y estado (borrador/publicado). |
| `GaleriaPublicacion` | Imágenes adicionales asociadas a una publicación. |
| `Comentario` | Comentarios de usuarios sobre una publicación, con estado de moderación (pendiente/aprobado/bloqueado). |

## Estructura del proyecto

```
conaco/
├── conaco/            # Configuración del proyecto (settings, urls, wsgi/asgi)
├── core/              # App principal: modelos, vistas y migraciones
├── manage.py
├── requirements.txt
└── .gitignore
```

## Instalación

1. Clona el repositorio:
   ```bash
   git clone https://github.com/Panucho69/conaco.git
   cd conaco
   ```

2. Crea y activa un entorno virtual:
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```

3. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

4. Ten un servidor **MariaDB** corriendo y crea la base de datos:
   ```sql
   CREATE DATABASE conaco_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   CREATE USER 'conaco_user'@'localhost' IDENTIFIED BY 'tu-password';
   GRANT ALL PRIVILEGES ON conaco_db.* TO 'conaco_user'@'localhost';
   FLUSH PRIVILEGES;
   ```

5. Crea un archivo `.env` en la raíz del proyecto con las variables de entorno necesarias:
   ```env
   SECRET_KEY=tu-clave-secreta
   DB_NAME=conaco_db
   DB_USER=conaco_user
   DB_PASSWORD=tu-password
   DB_HOST=localhost
   DB_PORT=3306
   ```

6. Aplica las migraciones:
   ```bash
   python manage.py migrate
   ```

7. Crea un superusuario (opcional, para acceder al panel de administración):
   ```bash
   python manage.py createsuperuser
   ```

8. Levanta el servidor de desarrollo:
   ```bash
   python manage.py runserver
   ```

9. Accede a la aplicación en `http://localhost:8000/` y al panel de administración en `http://localhost:8000/admin/`.

## Estado

Proyecto en desarrollo.
