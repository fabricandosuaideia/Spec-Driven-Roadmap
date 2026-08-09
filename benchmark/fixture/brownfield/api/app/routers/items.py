from fastapi import APIRouter
router = APIRouter()


@router.post("/")
def propose_item(agenda_id: int, title: str, minutes: int = 10):
    return {"id": 1}


@router.get("/{agenda_id}")
def list_items(agenda_id: int):
    """Returns insertion order. Voting does not exist, so there is nothing to sort by."""
    return []
