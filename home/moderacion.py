"""Moderación automática de comentarios.

Un comentario se publica solo, a menos que tenga lenguaje ofensivo (groserías, insultos,
racismo, homofobia, etc.) o enlaces: en ese caso queda pendiente hasta que el equipo lo revise.
Para agregar o quitar palabras, edita las listas de abajo (sin acentos ni mayúsculas).
"""
import re
import unicodedata

# Se marca cualquier palabra que EMPIECE con estas raíces (pendej -> pendejo, pendeja, pendejadas)
RAICES = [
    # Groserías e insultos
    'pendej', 'chingad', 'chingar', 'chingu', 'chinga', 'cabron', 'mierd', 'pinche', 'culer',
    'mamad', 'mamon', 'ojete', 'putit', 'putaz', 'putiz', 'putisim', 'hijueput', 'hdp', 'malparid',
    'gilipoll', 'imbecil', 'estupid', 'idiot', 'baboso', 'babosa', 'tarad', 'retrasad', 'subnormal',
    'cojud', 'huevon', 'guevon', 'weon', 'pelotud', 'boludo', 'carajo', 'coño',
    'verguer', 'vergaz', 'zorrona', 'prostitut', 'perro asqueroso', 'perra asquerosa',
    # Discriminación (racismo, clasismo, homofobia y otros)
    'maric', 'mayate', 'travelo', 'sudaca', 'gachupin', 'negrat', 'negrit de mierda',
    'prieto asqueroso', 'pata rajada', 'indiada', 'mugroso',
    'te voy a matar', 'ojala te mueras', 'matate', 'suicidate',
    # Inglés
    'fuck', 'shit', 'bitch', 'bastard', 'nigg', 'faggot', 'retard', 'motherf', 'asshole', 'dumbass',
]

# Se marcan solo si la palabra completa coincide (con o sin plural), para no confundir
# palabras normales: "puta" sí, "computadora" no; "naco" sí, "Canaco" no.
PALABRAS = [
    'puto', 'puta', 'verga', 'joto', 'jota', 'culo', 'naco', 'naca', 'zorra', 'perra', 'pito',
    'mamada', 'wey pendejo', 'tonto', 'tonta', 'menso', 'mensa', 'gordo asqueroso', 'simio',
    'chacha', 'gata', 'indio', 'india', 'prieto', 'prieta', 'negro', 'negra', 'chino cochino',
    'sidoso', 'mongol', 'mogolico', 'mongolico', 'cerdo', 'cerda', 'basura', 'escoria', 'lacra',
    'cunt', 'dick', 'whore', 'slut',
]

# Estas, solas, no son ofensivas ("negro", "indio", "gata"...); solo cuentan si van junto a un insulto
NEUTRAS_SOLAS = {'negro', 'negra', 'indio', 'india', 'prieto', 'prieta', 'chacha', 'gata', 'cerdo', 'cerda',
                 'basura', 'tonto', 'tonta', 'menso', 'mensa', 'simio', 'mongol', 'perra'}

LEET = str.maketrans({'4': 'a', '@': 'a', '3': 'e', '1': 'i', '!': 'i', '0': 'o', '5': 's', '$': 's', '7': 't', '+': 't'})
ENLACE = re.compile(r'(https?://|www\.|\b[a-z0-9-]+\.(com|net|org|mx|ru|xyz|info|biz|top)\b)', re.I)


def normalizar(texto):
    """Minúsculas, sin acentos, sin trucos (p3nd3jo, puuuto, p.u.t.o) y sin letras repetidas."""
    texto = texto.lower().translate(LEET)
    # Quita acentos pero conserva la ñ
    texto = texto.replace('ñ', '\0')
    texto = ''.join(c for c in unicodedata.normalize('NFKD', texto) if not unicodedata.combining(c))
    texto = texto.replace('\0', 'ñ')
    # Letras sueltas separadas por puntos, guiones o espacios: "p.u.t.o" -> "puto"
    texto = re.sub(r'\b(?:[a-zñ][\s.\-_*]+){2,}[a-zñ]\b', lambda m: re.sub(r'[\s.\-_*]', '', m.group()), texto)
    texto = re.sub(r'[^a-zñ\s]', ' ', texto)
    # Letras repetidas: "puuuuto" -> "puto" (se aplica igual a las listas para que coincidan)
    texto = re.sub(r'(.)\1+', r'\1', texto)
    return ' '.join(texto.split())


def _patron(lista, completa):
    partes = sorted({normalizar(p) for p in lista}, key=len, reverse=True)
    cuerpo = '|'.join(re.escape(p).replace(r'\ ', r'\s+') for p in partes)
    return re.compile(rf'\b(?:{cuerpo})(?:e?s)?\b' if completa else rf'\b(?:{cuerpo})', re.I)


_RAICES = _patron(RAICES, completa=False)
_INSULTOS = _patron([p for p in PALABRAS if p not in NEUTRAS_SOLAS], completa=True)
_NEUTRAS = _patron(NEUTRAS_SOLAS, completa=True)


def motivo_revision(texto):
    """Devuelve por qué el comentario debe revisarse a mano, o '' si se puede publicar directo."""
    if ENLACE.search(texto):
        return 'Contiene enlaces'
    limpio = normalizar(texto)
    if _RAICES.search(limpio) or _INSULTOS.search(limpio):
        return 'Lenguaje ofensivo'
    # "negro", "indio"... solo cuentan si el comentario también trae un insulto (ya revisado arriba)
    # o si van en mayúsculas sostenidas, que suelen ser ataques ("INDIO")
    if _NEUTRAS.search(limpio) and texto.isupper() and len(texto) > 3:
        return 'Lenguaje ofensivo'
    if len(texto) > 20 and sum(c.isupper() for c in texto) / max(1, sum(c.isalpha() for c in texto)) > 0.7:
        return 'Escrito todo en mayúsculas'
    return ''
