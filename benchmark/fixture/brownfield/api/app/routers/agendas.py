from fastapi import APIRouter
router = APIRouter()


@router.get("/{team_id}")
def list_agendas(team_id: int):
    return []


@router.post("/")
def create_agenda(team_id: int, title: str):
    """Creates in 'draft'. State transitions are not implemented."""
    return {"id": 1, "state": "draft"}
