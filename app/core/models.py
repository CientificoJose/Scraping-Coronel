"""
Modelos de datos con Pydantic para el ecosistema Scraping-Coronel.
Proporciona validación estricta, serialización limpia y compatibilidad con diccionarios.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator


class Dimensiones(BaseModel):
    """Dimensiones y peso estimados para logística y envíos en Tiendanube."""
    peso_kg: float = Field(default=0.05, description="Peso en kilogramos")
    ancho_cm: float = Field(default=5.0, description="Ancho del paquete en cm")
    alto_cm: float = Field(default=5.0, description="Alto del paquete en cm")
    profundidad_cm: float = Field(default=5.0, description="Profundidad del paquete en cm")

    @classmethod
    def default_fallback(cls) -> "Dimensiones":
        return cls(peso_kg=0.05, ancho_cm=5.0, alto_cm=5.0, profundidad_cm=5.0)


class Producto(BaseModel):
    """Modelo canónico de producto sincronizado."""
    codigo: str = Field(..., description="SKU base (ej: COR-12345)")
    codigo_de_barras: Optional[str] = Field(default="", description="Código de barras EAN/UPC")
    descripcion: str = Field(default="", description="Nombre o título del producto")
    precio: str = Field(default="0", description="Precio base mayorista como string (ej: $1.250,00)")
    imagen_url: Optional[str] = Field(default="", description="URL remota de la imagen")
    imagen_local: Optional[str] = Field(default="", description="Ruta local si se descargó en disco")
    variante: Optional[str] = Field(default=None, description="Variante o atributo si aplica")
    categoria: Optional[str] = Field(default="", description="Categoría principal")
    subcategoria: Optional[str] = Field(default="", description="Subcategoría o etiquetas")
    
    # Dimensiones
    peso_kg: Optional[str] = Field(default="0.05", description="Peso estimado")
    ancho_cm: Optional[str] = Field(default="5.0", description="Ancho estimado")
    alto_cm: Optional[str] = Field(default="5.0", description="Alto estimado")
    profundidad_cm: Optional[str] = Field(default="5.0", description="Profundidad estimada")

    @field_validator("codigo", mode="before")
    @classmethod
    def normalizar_codigo(cls, v: Any) -> str:
        if v is None:
            return ""
        return str(v).strip().replace(" ", "")

    def get_precio_float(self) -> float:
        """Parsea el precio string con formato monetario latinoamericano a float puro."""
        try:
            limpio = (
                str(self.precio)
                .replace("$", "")
                .replace(" ", "")
                .replace(".", "")
                .replace(",", ".")
            )
            return float(limpio)
        except Exception:
            return 0.0

    def calcular_precio_venta(self, margen_ganancia: float) -> float:
        """Calcula el precio final de venta al público aplicando el porcentaje de margen."""
        base = self.get_precio_float()
        return round(base * (1.0 + (margen_ganancia / 100.0)), 2)

    def to_dict(self) -> Dict[str, Any]:
        """Exporta a diccionario compatible con el esquema heredado del proyecto."""
        return self.model_dump()

    @classmethod
    def from_row(cls, row: tuple) -> "Producto":
        """Instancia un producto a partir de una tupla de la tabla SQLite productos."""
        return cls(
            codigo=str(row[0] or ""),
            codigo_de_barras=str(row[1] or ""),
            descripcion=str(row[2] or ""),
            precio=str(row[3] or "0"),
            imagen_url=str(row[4] or ""),
            imagen_local=str(row[5] or ""),
            variante=str(row[6]).replace("-", "") if row[6] else None,
            categoria=str(row[7] or ""),
            subcategoria=str(row[8] or ""),
            peso_kg=str(row[9] or "0.05"),
            ancho_cm=str(row[10] or "5.0"),
            alto_cm=str(row[11] or "5.0"),
            profundidad_cm=str(row[12] or "5.0"),
        )
