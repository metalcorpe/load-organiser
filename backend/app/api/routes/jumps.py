from typing import Any
import uuid

from fastapi import APIRouter, HTTPException
from sqlmodel import func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import Jump, JumpCreate, JumpPublic, JumpUpdate, JumpsPublic, Message, JumpType
from app import crud

router = APIRouter()


@router.get("/", response_model=JumpsPublic)
def read_jumps(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve jumps.
    """

    count_statement = select(func.count()).select_from(Jump)
    count = session.exec(count_statement).one()

    statement = select(Jump).offset(skip).limit(limit)
    jumps = session.exec(statement).all()

    return JumpsPublic(data=jumps, count=count)


@router.get("/{id}", response_model=JumpPublic)
def read_jump(session: SessionDep, current_user: CurrentUser, id: uuid.UUID) -> Any:
    """
    Get jump by ID.
    """
    jump = session.get(Jump, id)
    if not jump:
        raise HTTPException(status_code=404, detail="Jump not found")
    return jump


@router.post("/", response_model=JumpPublic)
def create_jump(
    *, session: SessionDep, current_user: CurrentUser, jump_in: JumpCreate
) -> Any:
    """
    Create new jump.
    """
    try:
        jump = crud.create_jump(session=session, jump_create=jump_in)
        return jump
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{id}", response_model=JumpPublic)
def update_jump(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    jump_in: JumpUpdate,
) -> Any:
    """
    Update a jump.
    """
    jump = session.get(Jump, id)
    if not jump:
        raise HTTPException(status_code=404, detail="Jump not found")
    
    update_dict = jump_in.model_dump(exclude_unset=True)
    jump.sqlmodel_update(update_dict)
    session.add(jump)
    session.commit()
    session.refresh(jump)
    return jump


@router.delete("/{id}")
def delete_jump(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Message:
    """
    Delete a jump.
    """
    jump = session.get(Jump, id)
    if not jump:
        raise HTTPException(status_code=404, detail="Jump not found")
    session.delete(jump)
    session.commit()
    return Message(message="Jump deleted successfully")


@router.get("/by-type/{jump_type}", response_model=JumpsPublic)
def read_jumps_by_type(
    session: SessionDep, current_user: CurrentUser, jump_type: JumpType, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve jumps by type.
    """
    statement = select(Jump).where(Jump.jump_type == jump_type).offset(skip).limit(limit)
    jumps = session.exec(statement).all()
    count = len(jumps)
    return JumpsPublic(data=jumps, count=count)


@router.get("/by-load/{load_id}", response_model=JumpsPublic)
def read_jumps_by_load(
    session: SessionDep, current_user: CurrentUser, load_id: uuid.UUID, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve jumps for a specific load.
    """
    statement = select(Jump).where(Jump.load_id == load_id).offset(skip).limit(limit)
    jumps = session.exec(statement).all()
    count = len(jumps)
    return JumpsPublic(data=jumps, count=count)


@router.get("/by-instructor/{instructor_id}", response_model=JumpsPublic)
def read_jumps_by_instructor(
    session: SessionDep, current_user: CurrentUser, instructor_id: uuid.UUID, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve jumps for a specific instructor.
    """
    statement = select(Jump).where(Jump.instructor_id == instructor_id).offset(skip).limit(limit)
    jumps = session.exec(statement).all()
    count = len(jumps)
    return JumpsPublic(data=jumps, count=count)


@router.get("/tandems/", response_model=JumpsPublic)
def read_tandem_jumps(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve tandem jumps.
    """
    statement = select(Jump).where(Jump.jump_type == JumpType.TANDEM).offset(skip).limit(limit)
    jumps = session.exec(statement).all()
    count = len(jumps)
    return JumpsPublic(data=jumps, count=count)


@router.get("/aff/", response_model=JumpsPublic)
def read_aff_jumps(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve AFF jumps.
    """
    statement = select(Jump).where(Jump.jump_type == JumpType.AFF).offset(skip).limit(limit)
    jumps = session.exec(statement).all()
    count = len(jumps)
    return JumpsPublic(data=jumps, count=count)


@router.post("/{id}/assign-instructor")
def assign_instructor_to_jump(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID, instructor_id: uuid.UUID
) -> Message:
    """
    Assign an instructor to a jump.
    """
    try:
        crud.assign_instructor_to_jump(session=session, jump_id=id, instructor_id=instructor_id)
        return Message(message="Instructor assigned to jump successfully")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
