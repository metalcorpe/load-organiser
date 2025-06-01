from typing import Any
import uuid

from fastapi import APIRouter, HTTPException
from sqlmodel import func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import Instructor, InstructorCreate, InstructorPublic, InstructorUpdate, InstructorsPublic, Message
from app import crud

router = APIRouter()


@router.get("/", response_model=InstructorsPublic)
def read_instructors(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve instructors.
    """

    count_statement = select(func.count()).select_from(Instructor)
    count = session.exec(count_statement).one()

    statement = select(Instructor).offset(skip).limit(limit)
    instructors = session.exec(statement).all()

    return InstructorsPublic(data=instructors, count=count)


@router.get("/{id}", response_model=InstructorPublic)
def read_instructor(session: SessionDep, current_user: CurrentUser, id: uuid.UUID) -> Any:
    """
    Get instructor by ID.
    """
    instructor = session.get(Instructor, id)
    if not instructor:
        raise HTTPException(status_code=404, detail="Instructor not found")
    return instructor


@router.post("/", response_model=InstructorPublic)
def create_instructor(
    *, session: SessionDep, current_user: CurrentUser, instructor_in: InstructorCreate
) -> Any:
    """
    Create new instructor.
    """
    instructor = crud.create_instructor(session=session, instructor_create=instructor_in)
    return instructor


@router.put("/{id}", response_model=InstructorPublic)
def update_instructor(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    instructor_in: InstructorUpdate,
) -> Any:
    """
    Update an instructor.
    """
    instructor = session.get(Instructor, id)
    if not instructor:
        raise HTTPException(status_code=404, detail="Instructor not found")
    
    update_dict = instructor_in.model_dump(exclude_unset=True)
    instructor.sqlmodel_update(update_dict)
    session.add(instructor)
    session.commit()
    session.refresh(instructor)
    return instructor


@router.delete("/{id}")
def delete_instructor(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Message:
    """
    Delete an instructor.
    """
    instructor = session.get(Instructor, id)
    if not instructor:
        raise HTTPException(status_code=404, detail="Instructor not found")
    session.delete(instructor)
    session.commit()
    return Message(message="Instructor deleted successfully")


@router.get("/tandem-certified/", response_model=InstructorsPublic)
def read_tandem_instructors(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve tandem-certified instructors.
    """
    instructors = crud.get_tandem_instructors(session=session, skip=skip, limit=limit)
    count = len(instructors)
    return InstructorsPublic(data=instructors, count=count)


@router.get("/aff-certified/", response_model=InstructorsPublic)
def read_aff_instructors(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve AFF-certified instructors.
    """
    instructors = crud.get_aff_instructors(session=session, skip=skip, limit=limit)
    count = len(instructors)
    return InstructorsPublic(data=instructors, count=count)
