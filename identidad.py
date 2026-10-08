"""Reconocer a que persona corresponde un nombre escrito a mano en el formulario.

El Lider escribe su nombre en el formulario; aqui se decide a quien de la lista
se refiere. Es deliberadamente conservador: solo devuelve una persona cuando la
coincidencia es unica y clara. Ante la duda no asigna (mejor que un Lider no vea
una acta suya a que vea la de otra persona), y deja una sugerencia para que quien
aprueba la confirme y quede guardada como alias.
"""

import difflib
import re
import unicodedata

TITULOS = {"ing", "inga", "arq", "arqa", "lic", "licda", "dr", "dra", "sr", "sra", "srta", "ingeniero", "arquitecto", "licenciado", "don", "dona"}


def _norm(texto):
    t = unicodedata.normalize("NFD", str(texto or ""))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")

    return re.sub(r"[^a-z0-9]+", " ", t.casefold()).strip()


def _tokens(texto):
    return [w for w in _norm(texto).split() if w not in TITULOS]


def _nombres_de(persona):
    return [persona["nombre"]] + list(persona.get("alias") or [])


def _inicial_o_igual(escrito, completo):
    return escrito == completo or (len(escrito) == 1 and completo.startswith(escrito))


def _puntaje(escrito, persona):
    """Que tan bien calza `escrito` con la persona: 3 igual, 2 contenido/iniciales,
    1 parecido por letras, 0 nada. Devuelve (nivel, similitud)."""

    t = _tokens(escrito)
    mejor = (0, 0.0)

    for nombre in _nombres_de(persona):
        c = _tokens(nombre)

        if not t or not c:
            continue

        sim = difflib.SequenceMatcher(None, " ".join(t), " ".join(c)).ratio()

        if t == c:
            nivel = 3
        elif len(t) >= 2 and (set(t) <= set(c) or set(c) <= set(t)):
            nivel = 2   # "Marcos Ruiz" contra "Marcos Ruiz Perez"
        elif len(t) >= 2 and len(t) <= len(c) and t[0] == c[0] and all(_inicial_o_igual(a, b) for a, b in zip(t, c)):
            nivel = 2   # "Marcos R." contra "Marcos Ruiz"
        elif (sim >= 0.88 and len(t) == len(c)
              and all(len(a) >= 3 and len(b) >= 3 and difflib.SequenceMatcher(None, a, b).ratio() >= 0.8 for a, b in zip(t, c))):
            nivel = 1   # errores de tipeo (palabra por palabra, nunca sobre iniciales ni letras sueltas)
        else:
            nivel = 0

        mejor = max(mejor, (nivel, sim))

    return mejor


def reconocer(escrito, personas):
    """(persona | None, sugerencia | None). `sugerencia` es la persona mas
    parecida cuando no se pudo asignar con seguridad (para que alguien la confirme)."""

    if not _tokens(escrito):
        return None, None

    puntajes = sorted(((_puntaje(escrito, p), p) for p in personas), key=lambda x: (x[0][0], x[0][1]), reverse=True)

    if not puntajes:
        return None, None

    (nivel, sim), mejor = puntajes[0]
    segundo = puntajes[1][0] if len(puntajes) > 1 else (0, 0.0)

    # Hay que ser unico: si otra persona calza igual de bien, no se asigna.
    clara = nivel >= 2 or (nivel == 1 and sim - segundo[1] >= 0.06)
    unica = segundo[0] < nivel or (segundo[0] == nivel and segundo[1] < sim - 0.06 and nivel < 2)

    if nivel > 0 and clara and unica:
        return mejor, None

    candidata = mejor if (nivel > 0 or sim >= 0.6) else None

    return None, candidata
