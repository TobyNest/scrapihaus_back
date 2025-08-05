from datetime import datetime
from beanie import Document
from pydantic import BaseModel


class Imovel(Document):
    data_coleta: datetime
    bairro: str
    tipo: str  #  ("casa", "apartamento", "lote/terreno")
    endereco: str
    area_privativa: int
    valor_total: float
    valor_m2: float
    condominio: float
    quartos: int
    iptu: float
    banheiros: int
    vagas_garagem: int
    link: str

    class Settings:
        name = "housings"  # Nome da "collection" no MongoDB
