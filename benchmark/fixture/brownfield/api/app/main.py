from fastapi import FastAPI
from .routers import teams, agendas, items

app = FastAPI(title="Pauta API")
app.include_router(teams.router, prefix="/teams", tags=["teams"])
app.include_router(agendas.router, prefix="/agendas", tags=["agendas"])
app.include_router(items.router, prefix="/items", tags=["items"])


@app.get("/health")
def health():
    return {"status": "ok"}
