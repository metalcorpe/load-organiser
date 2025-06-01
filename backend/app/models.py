import uuid
from datetime import datetime
from enum import Enum

from pydantic import EmailStr
from sqlmodel import Field, Relationship, SQLModel


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=40)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=40)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
    password: str | None = Field(default=None, min_length=8, max_length=40)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=40)
    new_password: str = Field(min_length=8, max_length=40)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    items: list["Item"] = Relationship(back_populates="owner", cascade_delete=True)


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Shared properties
class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Properties to receive on item creation
class ItemCreate(ItemBase):
    pass


# Properties to receive on item update
class ItemUpdate(ItemBase):
    title: str | None = Field(default=None, min_length=1, max_length=255)  # type: ignore


# Database model, database table inferred from class name
class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="items")


# Properties to return via API, id is always required
class ItemPublic(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=40)


# Skydiving Load Organizer Models

# Enums for jump types and statuses
class JumpType(str, Enum):
    TANDEM = "tandem"
    AFF = "aff"
    FUN_JUMPER = "fun_jumper"


class LoadStatus(str, Enum):
    PLANNING = "planning"
    CONFIRMED = "confirmed"
    BOARDED = "boarded"
    DEPARTED = "departed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AFFlevel(str, Enum):
    LEVEL_1 = "level_1"
    LEVEL_2 = "level_2" 
    LEVEL_3 = "level_3"
    LEVEL_4 = "level_4"
    LEVEL_5 = "level_5"
    LEVEL_6 = "level_6"
    LEVEL_7 = "level_7"
    GRADUATE = "graduate"


class WeatherCondition(str, Enum):
    GOOD = "good"
    MARGINAL = "marginal"
    POOR = "poor"


# Aircraft model
class AircraftBase(SQLModel):
    registration: str = Field(max_length=20, unique=True, index=True)
    model: str = Field(max_length=100)
    capacity: int = Field(ge=2, le=50)  # 2-50 seats
    is_active: bool = True


class AircraftCreate(AircraftBase):
    pass


class AircraftUpdate(SQLModel):
    registration: str | None = Field(default=None, max_length=20)
    model: str | None = Field(default=None, max_length=100)
    capacity: int | None = Field(default=None, ge=2, le=50)
    is_active: bool | None = None


class Aircraft(AircraftBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    loads: list["Load"] = Relationship(back_populates="aircraft")


class AircraftPublic(AircraftBase):
    id: uuid.UUID


class AircraftsPublic(SQLModel):
    data: list[AircraftPublic]
    count: int


# Instructor model
class InstructorBase(SQLModel):
    name: str = Field(max_length=255)
    email: EmailStr = Field(max_length=255)
    tandem_certified: bool = False
    aff_certified: bool = False
    is_active: bool = True


class InstructorCreate(InstructorBase):
    pass


class InstructorUpdate(SQLModel):
    name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)
    tandem_certified: bool | None = None
    aff_certified: bool | None = None
    is_active: bool | None = None


class Instructor(InstructorBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    jumps: list["Jump"] = Relationship(back_populates="instructor")


class InstructorPublic(InstructorBase):
    id: uuid.UUID


class InstructorsPublic(SQLModel):
    data: list[InstructorPublic]
    count: int


# Load model (aircraft load)
class LoadBase(SQLModel):
    aircraft_id: uuid.UUID = Field(foreign_key="aircraft.id")
    scheduled_time: datetime
    altitude: int = Field(ge=3000, le=18000, default=10000)  # feet
    status: LoadStatus = LoadStatus.PLANNING
    notes: str | None = Field(default=None, max_length=500)


class LoadCreate(LoadBase):
    pass


class LoadUpdate(SQLModel):
    aircraft_id: uuid.UUID | None = Field(default=None, foreign_key="aircraft.id")
    scheduled_time: datetime | None = None
    altitude: int | None = Field(default=None, ge=3000, le=18000)
    status: LoadStatus | None = None
    notes: str | None = Field(default=None, max_length=500)


class Load(LoadBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    aircraft: Aircraft = Relationship(back_populates="loads")
    jumps: list["Jump"] = Relationship(back_populates="load", cascade_delete=True)


class LoadPublic(LoadBase):
    id: uuid.UUID
    created_at: datetime
    aircraft: AircraftPublic
    jumps: list["JumpPublic"] = []


class LoadsPublic(SQLModel):
    data: list[LoadPublic]
    count: int


# Jump model (individual jumper on a load)
class JumpBase(SQLModel):
    load_id: uuid.UUID = Field(foreign_key="load.id")
    jumper_name: str = Field(max_length=255)
    jump_type: JumpType
    exit_order: int = Field(ge=1)
    instructor_id: uuid.UUID | None = Field(default=None, foreign_key="instructor.id")
    aff_level: AFFlevel | None = None
    customer_email: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=500)


class JumpCreate(JumpBase):
    pass


class JumpUpdate(SQLModel):
    load_id: uuid.UUID | None = Field(default=None, foreign_key="load.id")
    jumper_name: str | None = Field(default=None, max_length=255)
    jump_type: JumpType | None = None
    exit_order: int | None = Field(default=None, ge=1)
    instructor_id: uuid.UUID | None = Field(default=None, foreign_key="instructor.id")
    aff_level: AFFlevel | None = None
    customer_email: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=500)


class Jump(JumpBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    load: Load = Relationship(back_populates="jumps")
    instructor: Instructor | None = Relationship(back_populates="jumps")


class JumpPublic(JumpBase):
    id: uuid.UUID
    created_at: datetime
    instructor: InstructorPublic | None = None


class JumpsPublic(SQLModel):
    data: list[JumpPublic]
    count: int


# Weather report model
class WeatherReportBase(SQLModel):
    date: datetime
    wind_speed: int = Field(ge=0, le=100)  # mph
    wind_direction: int = Field(ge=0, le=360)  # degrees
    visibility: float = Field(ge=0.0, le=20.0)  # miles
    cloud_ceiling: int | None = Field(default=None, ge=0, le=50000)  # feet
    condition: WeatherCondition
    suitable_for_tandems: bool = True
    suitable_for_students: bool = True
    suitable_for_fun_jumpers: bool = True


class WeatherReportCreate(WeatherReportBase):
    pass


class WeatherReportUpdate(SQLModel):
    date: datetime | None = None
    wind_speed: int | None = Field(default=None, ge=0, le=100)
    wind_direction: int | None = Field(default=None, ge=0, le=360)
    visibility: float | None = Field(default=None, ge=0.0, le=20.0)
    cloud_ceiling: int | None = Field(default=None, ge=0, le=50000)
    condition: WeatherCondition | None = None
    suitable_for_tandems: bool | None = None
    suitable_for_students: bool | None = None
    suitable_for_fun_jumpers: bool | None = None


class WeatherReport(WeatherReportBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class WeatherReportPublic(WeatherReportBase):
    id: uuid.UUID
    created_at: datetime


class WeatherReportsPublic(SQLModel):
    data: list[WeatherReportPublic]
    count: int


# Load summary with statistics
class LoadSummary(SQLModel):
    total_jumpers: int
    tandem_count: int
    aff_count: int
    fun_jumper_count: int
    capacity_utilization: float
    revenue_estimate: float | None = None


class LoadWithSummary(LoadPublic):
    summary: LoadSummary
