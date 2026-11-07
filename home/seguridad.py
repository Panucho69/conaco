import os

# Imágenes que se aceptan al subir fotos (perfil, portada y galería)
EXTENSIONES_IMAGEN = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
TAMANO_MAXIMO = 5 * 1024 * 1024  # 5 MB
FIRMAS_IMAGEN = (b'\xff\xd8\xff', b'\x89PNG\r\n\x1a\n', b'GIF87a', b'GIF89a')


def validar_imagen(upload):
    """Devuelve un mensaje de error si el archivo no es una imagen válida, o None si está bien."""
    extension = os.path.splitext(upload.name)[1].lower()
    if extension not in EXTENSIONES_IMAGEN:
        return f'"{upload.name}" no es una imagen. Formatos permitidos: JPG, PNG, GIF y WEBP.'
    if upload.size > TAMANO_MAXIMO:
        return f'"{upload.name}" pesa más de 5 MB.'

    # Revisa los primeros bytes: un archivo renombrado a .jpg no pasa
    cabecera = upload.read(12)
    upload.seek(0)
    es_webp = cabecera[:4] == b'RIFF' and cabecera[8:12] == b'WEBP'
    if not (cabecera.startswith(FIRMAS_IMAGEN) or es_webp):
        return f'"{upload.name}" no es una imagen válida.'
    return None


def obtener_ip_cliente(request):
    """IP real del visitante, para que django-axes cuente los intentos fallidos de cada quien."""
    # En Azure todas las peticiones llegan desde su proxy, que pone la IP real en X-Client-IP.
    # Fuera de Azure esos encabezados los podría falsificar el visitante, así que se ignoran.
    if os.environ.get('WEBSITE_HOSTNAME'):
        ip = request.META.get('HTTP_X_CLIENT_IP') or request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0]
        ip = ip.strip()
        if ip.startswith('['):  # IPv6 con puerto: [2001:db8::1]:443
            ip = ip[1:ip.find(']')]
        elif ip.count(':') == 1:  # IPv4 con puerto: 187.1.2.3:443
            ip = ip.split(':')[0]
        if ip:
            return ip
    return request.META.get('REMOTE_ADDR')
