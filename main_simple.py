from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.users import router as users_router
from api.routes.series import router as series_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://panelsx.netlify.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users_router, prefix="/api/users")
app.include_router(series_router, prefix="/api/series")

@app.get("/")
def root():
    return {"message": "PanelX backend running on Railway 🚀"}
    