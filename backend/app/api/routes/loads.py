from typing import Any
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from sqlmodel import func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import Load, LoadCreate, LoadPublic, LoadUpdate, LoadsPublic, Message, LoadStatus
from app import crud

router = APIRouter()


@router.get("/", response_model=LoadsPublic)
def read_loads(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve loads.
    """

    count_statement = select(func.count()).select_from(Load)
    count = session.exec(count_statement).one()

    statement = select(Load).offset(skip).limit(limit)
    loads = session.exec(statement).all()

    return LoadsPublic(data=loads, count=count)


@router.get("/{id}", response_model=LoadPublic)
def read_load(session: SessionDep, current_user: CurrentUser, id: uuid.UUID) -> Any:
    """
    Get load by ID.
    """
    load = session.get(Load, id)
    if not load:
        raise HTTPException(status_code=404, detail="Load not found")
    return load


@router.post("/", response_model=LoadPublic)
def create_load(
    *, session: SessionDep, current_user: CurrentUser, load_in: LoadCreate
) -> Any:
    """
    Create new load.
    """
    load = crud.create_load(session=session, load_create=load_in)
    return load


@router.put("/{id}", response_model=LoadPublic)
def update_load(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    load_in: LoadUpdate,
) -> Any:
    """
    Update a load.
    """
    load = session.get(Load, id)
    if not load:
        raise HTTPException(status_code=404, detail="Load not found")
    
    update_dict = load_in.model_dump(exclude_unset=True)
    load.sqlmodel_update(update_dict)
    session.add(load)
    session.commit()
    session.refresh(load)
    return load


@router.delete("/{id}")
def delete_load(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Message:
    """
    Delete a load.
    """
    load = session.get(Load, id)
    if not load:
        raise HTTPException(status_code=404, detail="Load not found")
    session.delete(load)
    session.commit()
    return Message(message="Load deleted successfully")


@router.get("/by-status/{status}", response_model=LoadsPublic)
def read_loads_by_status(
    session: SessionDep, current_user: CurrentUser, status: LoadStatus, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve loads by status.
    """
    statement = select(Load).where(Load.status == status).offset(skip).limit(limit)
    loads = session.exec(statement).all()
    count = len(loads)
    return LoadsPublic(data=loads, count=count)


@router.get("/today/", response_model=LoadsPublic)
def read_todays_loads(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve today's loads.
    """
    today = datetime.now().date()
    statement = select(Load).where(func.date(Load.scheduled_time) == today).offset(skip).limit(limit)
    loads = session.exec(statement).all()
    count = len(loads)
    return LoadsPublic(data=loads, count=count)


@router.post("/{id}/add-jumper")
def add_jumper_to_load(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID, jumper_id: uuid.UUID
) -> Message:
    """
    Add a jumper to a load.
    """
    try:
        crud.add_jumper_to_load(session=session, load_id=id, jumper_id=jumper_id)
        return Message(message="Jumper added to load successfully")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{id}/remove-jumper/{jumper_id}")
def remove_jumper_from_load(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID, jumper_id: uuid.UUID
) -> Message:
    """
    Remove a jumper from a load.
    """
    try:
        crud.remove_jumper_from_load(session=session, load_id=id, jumper_id=jumper_id)
        return Message(message="Jumper removed from load successfully")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{id}/capacity")
def get_load_capacity(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> dict[str, Any]:
    """
    Get load capacity information.
    """
    capacity_info = crud.get_load_capacity_info(session=session, load_id=id)
    if not capacity_info:
        raise HTTPException(status_code=404, detail="Load not found")
    return capacity_info
