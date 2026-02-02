from app.routers import auth, admin, orders, driver
from app.core import database
from app import models

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static Files (for uploads)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Include Routers
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(orders.router)
app.include_router(driver.router)

@app.on_event("startup")
async def startup():
    async with database.engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)


@app.get("/")
def root():
    return {"message": "Welcome to DOT Backend", "status": "running"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
