from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes.users import router as users_router
from api.routes.series import router as series_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://panelsx.netlify.app",           # Old Netlify
        "https://panel-x-frontend.vercel.app",   # New Vercel ← ADD THIS
        "http://localhost:5173",                  # Local dev
        "http://localhost:3000",                  # Local dev alt
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users_router, prefix="/api/users")
app.include_router(series_router, prefix="/api/series")

@app.get("/")
def root():
    return {"message": "PanelX backend running on Railway"}

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.detail},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal server error"},
    )