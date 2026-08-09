from fastapi import APIRouter
router = APIRouter()


@router.get("/")
def list_teams():
    """Teams the caller belongs to. Membership table exists; roles do not yet."""
    return []


@router.post("/")
def create_team(name: str):
    return {"id": 1, "name": name}
