from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ✅ Import route PROPERLY
from api.routes.images import router as images_router

app = FastAPI()

# ✅ CORS (so frontend can talk to backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Register route
app.include_router(images_router, prefix="/api/images")


@app.get("/")
def root():
    return {"message": "PanelX backend is alive 🚀"}