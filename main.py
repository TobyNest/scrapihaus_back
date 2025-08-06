from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from beanie import init_beanie
import motor.motor_asyncio
from models import Imovel  # Importe seu modelo Beanie
from dotenv import load_dotenv
from contextlib import asynccontextmanager
import os

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("MONGODB_URL"))
    await init_beanie(database=client.housings, document_models=[Imovel])
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://tobynest.github.io","http://localhost:3000"],  # ajuste conforme a porta do seu frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/housings/", response_model=list[Imovel])
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
        filters.append(Imovel.tipo == tipo)
    if bairro:
        filters.append(Imovel.bairro == bairro)
    if quartos is not None:
        filters.append(Imovel.quartos == quartos)
    if banheiros is not None:
        filters.append(Imovel.banheiros == banheiros)
    if vagas_garagem is not None:
        filters.append(Imovel.vagas_garagem == vagas_garagem)

    if filters:
        housings = await Imovel.find(*filters).to_list()
    else:
        housings = await Imovel.find_all().to_list()

    return housings


@app.post("/housings/", response_model=Imovel, status_code=201)
async def create_housing(housing: Imovel):
    await housing.create()
    return housing
