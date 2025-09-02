from datetime import datetime
from beanie import Document
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from pymongo import IndexModel


class User(Document):
    email: EmailStr
    hashed_password: str
    full_name: str
    is_active: bool = True
    is_admin: bool = False
    created_at: datetime = datetime.now()

    class Settings:
        name = "users"
        indexes = [
            IndexModel("email", unique=True),
        ]


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    is_active: bool
    is_admin: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str


class SearchHistory(Document):
    user_id: str
    search_params: Dict[str, Any]
    results_count: int
    timestamp: datetime = datetime.utcnow()

    class Settings:
        name = "search_history"
        indexes = [
            IndexModel("user_id"),
            IndexModel("timestamp"),
        ]


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
        name = "Imovel"  # Nome da "collection" no MongoDB
