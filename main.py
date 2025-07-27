from fastapi import FastAPI, HTTPException
from beanie import init_beanie
import motor.motor_asyncio
from models import Housing  # Importe seu modelo Beanie
from dotenv import load_dotenv
from contextlib import asynccontextmanager
import os

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("MONGODB_URL"))
    await init_beanie(database=client.db_name, document_models=[Housing])
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/housings/", response_model=list[Housing])
async def get_housings(
    # pesquisar tipo, bairro, area, quartos, banheiros, vagas_garagem
    tipo: str = None,
    bairro: str = None,
    quartos: int = None,
    banheiros: int = None,
    vagas_garagem: int = None,
):
    # valida os parâmetros de pesquisa
    if quartos is not None and quartos < 0:
        raise HTTPException(
            status_code=400, detail="quartos must be a non-negative integer"
        )
    if banheiros is not None and banheiros < 0:
        raise HTTPException(
            status_code=400, detail="banheiros must be a non-negative integer"
        )
    if vagas_garagem is not None and vagas_garagem < 0:
        raise HTTPException(
            status_code=400, detail="vagas_garagem must be a non-negative integer"
        )

    filters = []
    if tipo:
        filters.append(Housing.tipo == tipo)
    if bairro:
        filters.append(Housing.bairro == bairro)
    if quartos is not None:
        filters.append(Housing.quartos == quartos)
    if banheiros is not None:
        filters.append(Housing.banheiros == banheiros)
    if vagas_garagem is not None:
        filters.append(Housing.vagas_garagem == vagas_garagem)

    if filters:
        housings = await Housing.find(*filters).to_list()
    else:
        housings = await Housing.find_all().to_list()

    return housings


@app.post("/housings/", response_model=Housing, status_code=201)
async def create_housing(housing: Housing):
    await housing.create()
    return housing
