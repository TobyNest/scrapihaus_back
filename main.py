from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from beanie import init_beanie
import motor.motor_asyncio
from models import Imovel, User, UserCreate, UserLogin, UserResponse, Token, SearchHistory
from auth import (
    get_password_hash, 
    authenticate_user, 
    create_access_token, 
    get_current_active_user,
    get_current_admin_user,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_current_user_optional,
)
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import os
from fastapi import Request
from datetime import datetime, timedelta

# free quota configuration (env) - number of free requests allowed per anonymous IP (permanent)
FREE_REQUESTS_LIMIT = int(os.getenv("FREE_REQUESTS_LIMIT", "20"))


load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("MONGODB_URL"))
    await init_beanie(database=client.housings, document_models=[Imovel, User, SearchHistory])
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://tobynest.github.io","http://localhost:3000","https://scrapihaus.vercel.app"],  # ajuste conforme a porta do seu frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Endpoints de autenticação
@app.post("/auth/register", response_model=UserResponse, status_code=201)
async def register_user(user_data: UserCreate):
    # Verifica se usuário já existe
    existing_user = await User.find_one(User.email == user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=400, 
            detail="Email already registered"
        )
    
    # Cria novo usuário
    hashed_password = get_password_hash(user_data.password)
    user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name
    )
    await user.create()
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
    is_active=user.is_active,
    is_admin=getattr(user, "is_admin", False),
    created_at=user.created_at
    )


@app.post("/auth/login", response_model=Token)
async def login_user(user_data: UserLogin):
    user = await authenticate_user(user_data.email, user_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
    is_active=current_user.is_active,
    is_admin=getattr(current_user, "is_admin", False),
    created_at=current_user.created_at
    )


@app.get("/admin/users", response_model=list[UserResponse])
async def admin_list_users(admin_user: User = Depends(get_current_admin_user)):
    """Lista todos os usuários (somente admin)."""
    users = await User.find_all().to_list()
    return [
        UserResponse(
            id=str(u.id),
            email=u.email,
            full_name=u.full_name,
            is_active=u.is_active,
            is_admin=getattr(u, "is_admin", False),
            created_at=u.created_at,
        )
        for u in users
    ]

@app.delete("/admin/users/{user_id}")
async def admin_delete_user(user_id: str, admin_user: User = Depends(get_current_admin_user)):
    """Deleta um usuário por id (somente admin)."""
    user = await User.get(user_id)
    if not user:
        user = await User.find_one(User.id == user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await user.delete()
    return {"message": "User deleted successfully"}


@app.get("/housings/", response_model=list[Imovel])
async def get_housings(
    request: Request,
    current_user: User | None = Depends(get_current_user_optional),
    # pesquisar tipo, bairro, area, quartos, banheiros, vagas_garagem
    tipo: str = None,
    bairro: list[str] | None = Query(None),
    quartos: int = None,
    banheiros: int = None,
    vagas_garagem: int = None,
    area_min: float = None,
    area_max: float = None,
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
    if area_min is not None and area_min < 0:
        raise HTTPException(
            status_code=400, detail="area_min must be a non-negative float"
        )
    if area_max is not None and area_max < 0:
        raise HTTPException(
            status_code=400, detail="area_max must be a non-negative float"
        )
    if area_min is not None and area_max is not None and area_min > area_max:
        raise HTTPException(
            status_code=400, detail="area_min cannot be greater than area_max"
        )

    # determine client IP early (used for anonymous quota and for saving history)
    client_ip = request.client.host if request.client else "unknown"

    # Enforce free anonymous quota per client IP when user is not authenticated
    if current_user is None:
        anon_id = f"anonymous:{client_ip}"
        # count previous anonymous searches persisted in DB for this IP
        anon_count = await SearchHistory.find(SearchHistory.user_id == anon_id).count()
        if anon_count >= FREE_REQUESTS_LIMIT:
            # quota exceeded -> require authentication
            raise HTTPException(status_code=401, detail="Free request quota exceeded; please register or login")

    query: dict = {}
    if tipo:
        query["tipo"] = tipo
    if bairro:
        query["bairro"] = {"$in": bairro}
    if quartos is not None:
        query["quartos"] = quartos
    if banheiros is not None:
        query["banheiros"] = banheiros
    if vagas_garagem is not None:
        query["vagas_garagem"] = vagas_garagem
    if area_min is not None or area_max is not None:
        area_query: dict = {}
        if area_min is not None:
            area_query["$gte"] = area_min
        if area_max is not None:
            area_query["$lte"] = area_max
        query["area_privativa"] = area_query

    if query:
        housings = await Imovel.find(query).to_list()
    else:
        housings = await Imovel.find_all().to_list()

    # Salva a consulta no histórico
    search_params = {}
    if tipo:
        search_params["tipo"] = tipo
    if bairro:
        search_params["bairro"] = bairro
    if quartos is not None:
        search_params["quartos"] = quartos
    if banheiros is not None:
        search_params["banheiros"] = banheiros
    if vagas_garagem is not None:
        search_params["vagas_garagem"] = vagas_garagem
    if area_min is not None:
        search_params["area_min"] = area_min
    if area_max is not None:
        search_params["area_max"] = area_max

    # Salva no histórico (usa id do usuário autenticado ou marca como anonymous:<ip>)
    user_id = str(current_user.id) if current_user else f"anonymous:{client_ip}"
    search_history = SearchHistory(
        user_id=user_id,
        search_params=search_params,
        results_count=len(housings)
    )
    await search_history.create()

    return housings


@app.get("/my-searches", response_model=list[SearchHistory])
async def get_my_search_history(
    current_user: User = Depends(get_current_active_user),
    limit: int = 50,
    skip: int = 0
):
    """Obtém o histórico de pesquisas do usuário atual"""
    if limit > 100:
        limit = 100  # Limita para evitar sobrecarga
    
    search_history = await SearchHistory.find(
        SearchHistory.user_id == str(current_user.id)
    ).sort(-SearchHistory.timestamp).skip(skip).limit(limit).to_list()
    
    return search_history


@app.delete("/my-searches/{search_id}")
async def delete_search_history(
    search_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Remove uma pesquisa específica do histórico"""
    search_history = await SearchHistory.find_one(
        SearchHistory.id == search_id,
        SearchHistory.user_id == str(current_user.id)
    )
    
    if not search_history:
        raise HTTPException(status_code=404, detail="Search history not found")
    
    await search_history.delete()
    return {"message": "Search history deleted successfully"}


@app.delete("/my-searches")
async def clear_search_history(current_user: User = Depends(get_current_active_user)):
    """Limpa todo o histórico de pesquisas do usuário"""
    await SearchHistory.find(SearchHistory.user_id == str(current_user.id)).delete()
    return {"message": "Search history cleared successfully"}


@app.post("/housings/", response_model=Imovel, status_code=201)
async def create_housing(
    housing: Imovel,
    current_user: User = Depends(get_current_active_user)
):
    await housing.create()
    return housing
