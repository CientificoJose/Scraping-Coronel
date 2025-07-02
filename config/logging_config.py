import logging
import logging.config
from .settings import LOGGING_CONFIG

def setup_logging():
    """Configura el logging para la aplicación."""
    try:
        logging.config.dictConfig(LOGGING_CONFIG)
        # logging.getLogger().info("Logging configurado exitosamente.") # Comentado para no ser muy verboso al inicio
    except Exception as e:
        # Fallback a configuración básica si dictConfig falla
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        logging.getLogger().error(f"Error al configurar logging desde dictConfig: {e}. Usando configuración básica.")

# Configurar logging cuando este módulo es importado por primera vez
# setup_logging()
# Decidí no llamar a setup_logging() aquí para que el punto de entrada main.py tenga el control
# de cuándo se inicializa el logging. Esto da más flexibilidad.
# El main.py importará esta función y la llamará.
