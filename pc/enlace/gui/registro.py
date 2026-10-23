import logging


def configurar(nombre, detallado=False):
    nivel = logging.DEBUG if detallado else logging.INFO
    logging.basicConfig(
        level=nivel,
        format=f"%(asctime)s [{nombre}] %(name)s %(levelname)s: %(message)s",
    )