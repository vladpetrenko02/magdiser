from fastapi import FastAPI
from db_service.database import engine, Base
from db_service.routers import users
from ml_service import predict
from auth_service import auth
from activity_collection_service.routers import collect_router
from fastapi.middleware.cors import CORSMiddleware
from massive_operations_service.routers import massive_endpoint

app = FastAPI()

# Додаємо CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Дозволити запити з будь-якого домену
    allow_credentials=True,
    allow_methods=["*"],  # Дозволити всі методи (GET, POST, PUT, DELETE тощо)
    allow_headers=["*"],  # Дозволити всі заголовки
)

Base.metadata.create_all(bind=engine)

app.include_router(users.router)
app.include_router(predict.router)
app.include_router(auth.router)
app.include_router(collect_router.router)
app.include_router(massive_endpoint.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True)