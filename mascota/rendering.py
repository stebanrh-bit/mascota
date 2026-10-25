"""Muestreo de capturas en coordenadas lógicas, también con escalado HiDPI."""


def logical_pixel(image, x, y):
    ratio = image.devicePixelRatio()
    px, py = round(x * ratio), round(y * ratio)
    if not (0 <= px < image.width() and 0 <= py < image.height()):
        raise ValueError('El punto está fuera de la captura.')
    return image.pixelColor(px, py)
