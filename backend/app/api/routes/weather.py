from typing import Any
import uuid
from datetime import datetime, date

from fastapi import APIRouter, HTTPException
from sqlmodel import func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import WeatherReport, WeatherReportCreate, WeatherReportPublic, WeatherReportUpdate, WeatherReportsPublic, Message
from app import crud

router = APIRouter()


@router.get("/", response_model=WeatherReportsPublic)
def read_weather_reports(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve weather reports.
    """

    count_statement = select(func.count()).select_from(WeatherReport)
    count = session.exec(count_statement).one()

    statement = select(WeatherReport).offset(skip).limit(limit)
    reports = session.exec(statement).all()

    return WeatherReportsPublic(data=reports, count=count)


@router.get("/{id}", response_model=WeatherReportPublic)
def read_weather_report(session: SessionDep, current_user: CurrentUser, id: uuid.UUID) -> Any:
    """
    Get weather report by ID.
    """
    report = session.get(WeatherReport, id)
    if not report:
        raise HTTPException(status_code=404, detail="Weather report not found")
    return report


@router.post("/", response_model=WeatherReportPublic)
def create_weather_report(
    *, session: SessionDep, current_user: CurrentUser, weather_in: WeatherReportCreate
) -> Any:
    """
    Create new weather report.
    """
    weather = crud.create_weather_report(session=session, weather_create=weather_in)
    return weather


@router.put("/{id}", response_model=WeatherReportPublic)
def update_weather_report(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    weather_in: WeatherReportUpdate,
) -> Any:
    """
    Update a weather report.
    """
    report = session.get(WeatherReport, id)
    if not report:
        raise HTTPException(status_code=404, detail="Weather report not found")
    
    update_dict = weather_in.model_dump(exclude_unset=True)
    report.sqlmodel_update(update_dict)
    session.add(report)
    session.commit()
    session.refresh(report)
    return report


@router.delete("/{id}")
def delete_weather_report(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Message:
    """
    Delete a weather report.
    """
    report = session.get(WeatherReport, id)
    if not report:
        raise HTTPException(status_code=404, detail="Weather report not found")
    session.delete(report)
    session.commit()
    return Message(message="Weather report deleted successfully")


@router.get("/current/", response_model=WeatherReportPublic)
def read_current_weather(session: SessionDep, current_user: CurrentUser) -> Any:
    """
    Get the most recent weather report.
    """
    statement = select(WeatherReport).order_by(WeatherReport.date.desc()).limit(1)
    report = session.exec(statement).first()
    if not report:
        raise HTTPException(status_code=404, detail="No weather reports found")
    return report


@router.get("/today/", response_model=WeatherReportsPublic)
def read_todays_weather(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve today's weather reports.
    """
    today = datetime.now().date()
    statement = select(WeatherReport).where(
        func.date(WeatherReport.date) == today
    ).order_by(WeatherReport.date.desc()).offset(skip).limit(limit)
    reports = session.exec(statement).all()
    count = len(reports)
    return WeatherReportsPublic(data=reports, count=count)


@router.get("/suitable-for-jumping/", response_model=WeatherReportsPublic)
def read_suitable_weather(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve weather reports suitable for jumping.
    """
    statement = select(WeatherReport).where(
        WeatherReport.suitable_for_tandems == True,
        WeatherReport.suitable_for_students == True,
        WeatherReport.suitable_for_fun_jumpers == True
    ).order_by(WeatherReport.date.desc()).offset(skip).limit(limit)
    reports = session.exec(statement).all()
    count = len(reports)
    return WeatherReportsPublic(data=reports, count=count)


@router.get("/tandem-suitable/", response_model=WeatherReportsPublic)
def read_tandem_suitable_weather(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve weather reports suitable for tandem jumps.
    """
    statement = select(WeatherReport).where(
        WeatherReport.suitable_for_tandems == True
    ).order_by(WeatherReport.date.desc()).offset(skip).limit(limit)
    reports = session.exec(statement).all()
    count = len(reports)
    return WeatherReportsPublic(data=reports, count=count)


@router.get("/student-suitable/", response_model=WeatherReportsPublic)
def read_student_suitable_weather(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve weather reports suitable for student jumps.
    """
    statement = select(WeatherReport).where(
        WeatherReport.suitable_for_students == True
    ).order_by(WeatherReport.date.desc()).offset(skip).limit(limit)
    reports = session.exec(statement).all()
    count = len(reports)
    return WeatherReportsPublic(data=reports, count=count)
