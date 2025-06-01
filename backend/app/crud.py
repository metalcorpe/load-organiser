import uuid
from typing import Any
from datetime import datetime

from sqlmodel import Session, select, and_

from app.core.security import get_password_hash, verify_password
from app.models import (
    Item, ItemCreate, User, UserCreate, UserUpdate,
    Aircraft, AircraftCreate, AircraftUpdate,
    Instructor, InstructorCreate, InstructorUpdate,
    Load, LoadCreate, LoadUpdate, LoadStatus,
    Jump, JumpCreate, JumpUpdate, JumpType,
    WeatherReport, WeatherReportCreate, WeatherReportUpdate
)


def create_user(*, session: Session, user_create: UserCreate) -> User:
    db_obj = User.model_validate(
        user_create, update={"hashed_password": get_password_hash(user_create.password)}
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_user(*, session: Session, db_user: User, user_in: UserUpdate) -> Any:
    user_data = user_in.model_dump(exclude_unset=True)
    extra_data = {}
    if "password" in user_data:
        password = user_data["password"]
        hashed_password = get_password_hash(password)
        extra_data["hashed_password"] = hashed_password
    db_user.sqlmodel_update(user_data, update=extra_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    session_user = session.exec(statement).first()
    return session_user


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    db_user = get_user_by_email(session=session, email=email)
    if not db_user:
        return None
    if not verify_password(password, db_user.hashed_password):
        return None
    return db_user


def create_item(*, session: Session, item_in: ItemCreate, owner_id: uuid.UUID) -> Item:
    db_item = Item.model_validate(item_in, update={"owner_id": owner_id})
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


# Aircraft CRUD operations
def create_aircraft(*, session: Session, aircraft_in: AircraftCreate) -> Aircraft:
    db_aircraft = Aircraft.model_validate(aircraft_in)
    session.add(db_aircraft)
    session.commit()
    session.refresh(db_aircraft)
    return db_aircraft


def get_aircraft(*, session: Session, aircraft_id: uuid.UUID) -> Aircraft | None:
    return session.get(Aircraft, aircraft_id)


def get_aircrafts(*, session: Session, skip: int = 0, limit: int = 100) -> list[Aircraft]:
    statement = select(Aircraft).where(Aircraft.is_active == True).offset(skip).limit(limit)
    return list(session.exec(statement).all())


def update_aircraft(*, session: Session, db_aircraft: Aircraft, aircraft_in: AircraftUpdate) -> Aircraft:
    aircraft_data = aircraft_in.model_dump(exclude_unset=True)
    db_aircraft.sqlmodel_update(aircraft_data)
    session.add(db_aircraft)
    session.commit()
    session.refresh(db_aircraft)
    return db_aircraft


# Instructor CRUD operations
def create_instructor(*, session: Session, instructor_in: InstructorCreate) -> Instructor:
    db_instructor = Instructor.model_validate(instructor_in)
    session.add(db_instructor)
    session.commit()
    session.refresh(db_instructor)
    return db_instructor


def get_instructor(*, session: Session, instructor_id: uuid.UUID) -> Instructor | None:
    return session.get(Instructor, instructor_id)


def get_instructors(*, session: Session, skip: int = 0, limit: int = 100, 
                   tandem_only: bool = False, aff_only: bool = False) -> list[Instructor]:
    statement = select(Instructor).where(Instructor.is_active == True)
    
    if tandem_only:
        statement = statement.where(Instructor.tandem_certified == True)
    if aff_only:
        statement = statement.where(Instructor.aff_certified == True)
    
    statement = statement.offset(skip).limit(limit)
    return list(session.exec(statement).all())


def update_instructor(*, session: Session, db_instructor: Instructor, instructor_in: InstructorUpdate) -> Instructor:
    instructor_data = instructor_in.model_dump(exclude_unset=True)
    db_instructor.sqlmodel_update(instructor_data)
    session.add(db_instructor)
    session.commit()
    session.refresh(db_instructor)
    return db_instructor


# Load CRUD operations
def create_load(*, session: Session, load_in: LoadCreate) -> Load:
    db_load = Load.model_validate(load_in)
    session.add(db_load)
    session.commit()
    session.refresh(db_load)
    return db_load


def get_load(*, session: Session, load_id: uuid.UUID) -> Load | None:
    return session.get(Load, load_id)


def get_loads(*, session: Session, skip: int = 0, limit: int = 100, 
              date_filter: datetime | None = None, status: LoadStatus | None = None) -> list[Load]:
    statement = select(Load)
    
    if date_filter:
        statement = statement.where(Load.scheduled_time >= date_filter)
    if status:
        statement = statement.where(Load.status == status)
    
    statement = statement.order_by(Load.scheduled_time).offset(skip).limit(limit)
    return list(session.exec(statement).all())


def update_load(*, session: Session, db_load: Load, load_in: LoadUpdate) -> Load:
    load_data = load_in.model_dump(exclude_unset=True)
    db_load.sqlmodel_update(load_data)
    session.add(db_load)
    session.commit()
    session.refresh(db_load)
    return db_load


def get_available_load_capacity(*, session: Session, load_id: uuid.UUID) -> int:
    """Get remaining capacity for a load"""
    load = session.get(Load, load_id)
    if not load:
        return 0
    
    current_jumpers = len(load.jumps)
    return load.aircraft.capacity - current_jumpers


# Jump CRUD operations
def create_jump(*, session: Session, jump_in: JumpCreate) -> Jump:
    # Validate load capacity
    load = session.get(Load, jump_in.load_id)
    if not load:
        raise ValueError("Load not found")
    
    current_capacity = get_available_load_capacity(session=session, load_id=jump_in.load_id)
    if current_capacity <= 0:
        raise ValueError("Load is at full capacity")
    
    # Validate instructor assignment for tandems and AFF
    if jump_in.jump_type in [JumpType.TANDEM, JumpType.AFF]:
        if not jump_in.instructor_id:
            raise ValueError(f"{jump_in.jump_type.value} jumps require an instructor")
        
        instructor = session.get(Instructor, jump_in.instructor_id)
        if not instructor:
            raise ValueError("Instructor not found")
        
        if jump_in.jump_type == JumpType.TANDEM and not instructor.tandem_certified:
            raise ValueError("Instructor not certified for tandem jumps")
        
        if jump_in.jump_type == JumpType.AFF and not instructor.aff_certified:
            raise ValueError("Instructor not certified for AFF jumps")
    
    db_jump = Jump.model_validate(jump_in)
    session.add(db_jump)
    session.commit()
    session.refresh(db_jump)
    return db_jump


def get_jump(*, session: Session, jump_id: uuid.UUID) -> Jump | None:
    return session.get(Jump, jump_id)


def get_jumps(*, session: Session, skip: int = 0, limit: int = 100,
              load_id: uuid.UUID | None = None, jump_type: JumpType | None = None) -> list[Jump]:
    statement = select(Jump)
    
    if load_id:
        statement = statement.where(Jump.load_id == load_id)
    if jump_type:
        statement = statement.where(Jump.jump_type == jump_type)
    
    statement = statement.order_by(Jump.exit_order).offset(skip).limit(limit)
    return list(session.exec(statement).all())


def update_jump(*, session: Session, db_jump: Jump, jump_in: JumpUpdate) -> Jump:
    jump_data = jump_in.model_dump(exclude_unset=True)
    
    # Validate instructor change if needed
    if "instructor_id" in jump_data or "jump_type" in jump_data:
        new_instructor_id = jump_data.get("instructor_id", db_jump.instructor_id)
        new_jump_type = jump_data.get("jump_type", db_jump.jump_type)
        
        if new_jump_type in [JumpType.TANDEM, JumpType.AFF] and new_instructor_id:
            instructor = session.get(Instructor, new_instructor_id)
            if instructor:
                if new_jump_type == JumpType.TANDEM and not instructor.tandem_certified:
                    raise ValueError("Instructor not certified for tandem jumps")
                if new_jump_type == JumpType.AFF and not instructor.aff_certified:
                    raise ValueError("Instructor not certified for AFF jumps")
    
    db_jump.sqlmodel_update(jump_data)
    session.add(db_jump)
    session.commit()
    session.refresh(db_jump)
    return db_jump


def delete_jump(*, session: Session, jump_id: uuid.UUID) -> bool:
    jump = session.get(Jump, jump_id)
    if jump:
        session.delete(jump)
        session.commit()
        return True
    return False


# Weather Report CRUD operations
def create_weather_report(*, session: Session, weather_in: WeatherReportCreate) -> WeatherReport:
    db_weather = WeatherReport.model_validate(weather_in)
    session.add(db_weather)
    session.commit()
    session.refresh(db_weather)
    return db_weather


def get_latest_weather_report(*, session: Session) -> WeatherReport | None:
    statement = select(WeatherReport).order_by(WeatherReport.date.desc())
    return session.exec(statement).first()


def get_weather_reports(*, session: Session, skip: int = 0, limit: int = 100,
                       start_date: datetime | None = None) -> list[WeatherReport]:
    statement = select(WeatherReport)
    
    if start_date:
        statement = statement.where(WeatherReport.date >= start_date)
    
    statement = statement.order_by(WeatherReport.date.desc()).offset(skip).limit(limit)
    return list(session.exec(statement).all())


# Analytics and statistics
def get_load_statistics(*, session: Session, load_id: uuid.UUID) -> dict:
    """Get statistics for a specific load"""
    load = session.get(Load, load_id)
    if not load:
        return {}
    
    jumps = load.jumps
    total_jumpers = len(jumps)
    tandem_count = sum(1 for j in jumps if j.jump_type == JumpType.TANDEM)
    aff_count = sum(1 for j in jumps if j.jump_type == JumpType.AFF)
    fun_jumper_count = sum(1 for j in jumps if j.jump_type == JumpType.FUN_JUMPER)
    
    capacity_utilization = (total_jumpers / load.aircraft.capacity) * 100 if load.aircraft.capacity > 0 else 0
    
    # Basic revenue estimate (these would be configurable)
    revenue_rates = {
        JumpType.TANDEM: 250.0,
        JumpType.AFF: 350.0,
        JumpType.FUN_JUMPER: 25.0
    }
    
    revenue_estimate = (
        tandem_count * revenue_rates[JumpType.TANDEM] +
        aff_count * revenue_rates[JumpType.AFF] +
        fun_jumper_count * revenue_rates[JumpType.FUN_JUMPER]
    )
    
    return {
        "total_jumpers": total_jumpers,
        "tandem_count": tandem_count,
        "aff_count": aff_count,
        "fun_jumper_count": fun_jumper_count,
        "capacity_utilization": round(capacity_utilization, 1),
        "revenue_estimate": revenue_estimate
    }


def get_instructor_schedule(*, session: Session, instructor_id: uuid.UUID, 
                           date_filter: datetime | None = None) -> list[Jump]:
    """Get an instructor's scheduled jumps"""
    statement = select(Jump).where(Jump.instructor_id == instructor_id)
    
    if date_filter:
        # Join with Load to filter by date
        statement = statement.join(Load).where(Load.scheduled_time >= date_filter)
    
    return list(session.exec(statement).all())
