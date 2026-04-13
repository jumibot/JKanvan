from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.infrastructure.database import init_db
from app.interfaces.routers import admin, auth, groups, priorities, projects, tags, tasks, todos
from app.interfaces.routers import users

app = FastAPI(title="Tasks API", version="7.0.0")

init_db()

app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(priorities.router)
app.include_router(projects.router)
app.include_router(groups.router)
app.include_router(tasks.router)
app.include_router(users.router)
app.include_router(todos.router)
app.include_router(tags.router)
app.include_router(tags.assign_router)

_FRONTEND = Path(__file__).parent.parent / "frontend"

app.mount("/static", StaticFiles(directory=_FRONTEND), name="frontend")


@app.get("/", include_in_schema=False)
def kanban():
    return FileResponse(_FRONTEND / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}
