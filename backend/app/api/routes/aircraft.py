import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import Aircraft, AircraftCreate, AircraftPublic, AircraftUpdate, Message
from app import crud

router = APIRouter()


@router.get("/", response_model=list[AircraftPublic])
def read_aircraft(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve aircraft.
    """
    aircrafts = crud.get_aircrafts(session=session, skip=skip, limit=limit)
    return aircrafts


@router.get("/{id}", response_model=AircraftPublic)
def read_aircraft_by_id(session: SessionDep, current_user: CurrentUser, id: uuid.UUID) -> Any:
    """
    Get aircraft by ID.
    """
    aircraft = session.get(Aircraft, id)
    if not aircraft:
        raise HTTPException(status_code=404, detail="Aircraft not found")
    return aircraft


@router.post("/", response_model=AircraftPublic)
def create_aircraft(
    *, session: SessionDep, current_user: CurrentUser, aircraft_in: AircraftCreate
) -> Any:
    """
    Create new aircraft.
    """
    # Check for duplicate registration
    existing = session.exec(
        select(Aircraft).where(Aircraft.registration == aircraft_in.registration)
    ).first()
    if existing:
        raise HTTPException(
            status_code=400, 
            detail="Aircraft with this registration already exists"
        )
    
    aircraft = Aircraft.model_validate(aircraft_in)
    session.add(aircraft)
    session.commit()
    session.refresh(aircraft)
    return aircraft


@router.put("/{id}", response_model=AircraftPublic)
def update_aircraft(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    aircraft_in: AircraftUpdate,
) -> Any:
    """
    Update an aircraft.
    """
    aircraft = session.get(Aircraft, id)
    if not aircraft:
        raise HTTPException(status_code=404, detail="Aircraft not found")
    
    # Check for duplicate registration if being updated
    if aircraft_in.registration and aircraft_in.registration != aircraft.registration:
        existing = session.exec(
            select(Aircraft).where(Aircraft.registration == aircraft_in.registration)
        ).first()
        if existing:
            raise HTTPException(
                status_code=400, 
                detail="Aircraft with this registration already exists"
            )
    
    update_dict = aircraft_in.model_dump(exclude_unset=True)
    aircraft.sqlmodel_update(update_dict)
    session.add(aircraft)
    session.commit()
    session.refresh(aircraft)
    return aircraft


@router.delete("/{id}")
def delete_aircraft(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Message:
    """
    Delete an aircraft.
    """
    aircraft = session.get(Aircraft, id)
    if not aircraft:
        raise HTTPException(status_code=404, detail="Aircraft not found")
    
    # Check if aircraft has any loads
    loads_count = session.exec(
        select(func.count()).select_from(Aircraft).where(Aircraft.id == id)
    ).one()
    if loads_count > 0:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete aircraft with existing loads"
        )
    
    session.delete(aircraft)
    session.commit()
    return Message(message="Aircraft deleted successfully")
