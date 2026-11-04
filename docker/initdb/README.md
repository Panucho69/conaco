# Datos iniciales de la base

MariaDB importa los archivos `.sql` de esta carpeta **solo la primera vez** que se crea el contenedor `db` (cuando el volumen `db_data` está vacío).

Aquí va `canaco.sql`, el respaldo de la base de XAMPP. No se sube a git porque contiene los usuarios y sus contraseñas cifradas.

Para volver a importarlo desde cero (esto **borra** los datos actuales del contenedor):

```bash
docker compose down -v
docker compose up -d
```
