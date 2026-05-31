from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from .build import construire
from .config import lister_sites

FRONTEND = Path(__file__).resolve().parent.parent.parent / "frontend"

app = FastAPI(title="Vigie")


@app.get("/api/sites")
def sites():
    return {"sites": lister_sites()}


@app.get("/api/conditions")
def conditions(site: str = "bayonne-nive"):
    return JSONResponse(construire(site))


app.mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="frontend")
