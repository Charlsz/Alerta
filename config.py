# config.py
from dataclasses import dataclass, field
from typing import Dict

@dataclass
class IRAConfig:
    # Ponderaciones de los sub-índices
    w_spc: float = 0.5
    w_sep: float = 0.3
    w_sve: float = 0.2

    # Umbrales de lluvia extrema (percentil histórico)
    precip_extrema_percentil: float = 95.0

    # Umbrales de temperatura crítica por cultivo (°C)
    tmax_critica_por_cultivo: Dict[str, float] = field(default_factory=lambda: {
        "maiz": 34.0,
        "arroz": 35.0,
        "papa": 28.0,
        "cafe": 30.0,
        "default": 33.0,
    })

    # Paginación SODA API
    soda_page_size: int = 50_000

    # Ruta de datos
    data_raw: str = "data/raw"
    data_processed: str = "data/processed"
    data_features: str = "data/features"

    # Clasificación IRA
    ira_niveles: Dict[str, tuple] = field(default_factory=lambda: {
        "Bajo":    (0.00, 0.25),
        "Medio":   (0.25, 0.50),
        "Alto":    (0.50, 0.75),
        "Crítico": (0.75, 1.00),
    })
