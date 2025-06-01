from typing import Any
import uuid
from datetime import datetime, date

from fastapi import APIRouter
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep
from app import crud

router = APIRouter()


@router.get("/load-statistics")
def get_load_statistics(
    session: SessionDep, current_user: CurrentUser
) -> dict[str, Any]:
    """
    Get load statistics and analytics.
    """
    stats = crud.get_load_statistics(session=session)
    return stats


@router.get("/revenue-estimate")
def get_revenue_estimate(
    session: SessionDep, current_user: CurrentUser, load_id: uuid.UUID
) -> dict[str, Any]:
    """
    Get revenue estimate for a specific load.
    """
    revenue = crud.calculate_load_revenue(session=session, load_id=load_id)
    return {"load_id": load_id, "estimated_revenue": revenue}


@router.get("/instructor-workload")
def get_instructor_workload(
    session: SessionDep, current_user: CurrentUser, instructor_id: uuid.UUID | None = None
) -> dict[str, Any]:
    """
    Get instructor workload statistics.
    """
    if instructor_id:
        workload = crud.get_instructor_workload(session=session, instructor_id=instructor_id)
        return {"instructor_id": instructor_id, "workload": workload}
    else:
        # Get workload for all instructors
        from app.models import Instructor
        statement = select(Instructor)
        instructors = session.exec(statement).all()
        workloads = {}
        for instructor in instructors:
            workloads[str(instructor.id)] = crud.get_instructor_workload(session=session, instructor_id=instructor.id)
        return {"all_instructors_workload": workloads}


@router.get("/daily-capacity/{target_date}")
def get_daily_capacity(
    session: SessionDep, current_user: CurrentUser, target_date: date
) -> dict[str, Any]:
    """
    Get daily capacity utilization for a specific date.
    """
    from app.models import Load, Aircraft
    from sqlmodel import func
    
    # Get all loads for the target date
    statement = select(Load).where(func.date(Load.scheduled_time) == target_date)
    loads = session.exec(statement).all()
    
    total_capacity = 0
    total_used = 0
    loads_info = []
    
    for load in loads:
        aircraft = session.get(Aircraft, load.aircraft_id)
        if aircraft:
            capacity_info = crud.get_load_capacity_info(session=session, load_id=load.id)
            if capacity_info:
                total_capacity += aircraft.capacity
                total_used += capacity_info["current_jumpers"]
                loads_info.append({
                    "load_id": load.id,
                    "aircraft": aircraft.registration,
                    "capacity": aircraft.capacity,
                    "used": capacity_info["current_jumpers"],
                    "utilization": capacity_info["utilization_percentage"]
                })
    
    overall_utilization = (total_used / total_capacity * 100) if total_capacity > 0 else 0
    
    return {
        "date": target_date,
        "total_capacity": total_capacity,
        "total_used": total_used,
        "overall_utilization": overall_utilization,
        "loads": loads_info
    }


@router.get("/jump-type-distribution")
def get_jump_type_distribution(
    session: SessionDep, current_user: CurrentUser, start_date: date | None = None, end_date: date | None = None
) -> dict[str, Any]:
    """
    Get distribution of jump types over a date range.
    """
    from app.models import Jump, JumpType
    from sqlmodel import func
    
    statement = select(Jump.jump_type, func.count(Jump.id).label('count')).group_by(Jump.jump_type)
    
    if start_date:
        statement = statement.join(Load).where(func.date(Load.scheduled_time) >= start_date)
    if end_date:
        statement = statement.join(Load).where(func.date(Load.scheduled_time) <= end_date)
    
    results = session.exec(statement).all()
    
    distribution = {}
    total_jumps = 0
    for jump_type, count in results:
        distribution[jump_type.value] = count
        total_jumps += count
    
    # Calculate percentages
    percentages = {}
    for jump_type, count in distribution.items():
        percentages[jump_type] = (count / total_jumps * 100) if total_jumps > 0 else 0
    
    return {
        "date_range": {"start": start_date, "end": end_date},
        "total_jumps": total_jumps,
        "distribution": distribution,
        "percentages": percentages
    }


@router.get("/weather-impact")
def get_weather_impact(
    session: SessionDep, current_user: CurrentUser, days: int = 7
) -> dict[str, Any]:
    """
    Get weather impact on jumping operations over the last N days.
    """
    from app.models import WeatherReport, Load
    from sqlmodel import func
    from datetime import timedelta
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Get weather reports in date range
    weather_statement = select(WeatherReport).where(
        func.date(WeatherReport.date) >= start_date,
        func.date(WeatherReport.date) <= end_date
    )
    weather_reports = session.exec(weather_statement).all()
    
    # Count suitable vs unsuitable days
    suitable_days = 0
    tandem_suitable_days = 0
    student_suitable_days = 0
    
    daily_weather = {}
    for report in weather_reports:
        report_date = report.date.date()
        if report_date not in daily_weather:
            daily_weather[report_date] = {
                "tandem_suitable": False,
                "student_suitable": False,
                "fun_jumper_suitable": False,
                "conditions": []
            }
        
        daily_weather[report_date]["tandem_suitable"] = daily_weather[report_date]["tandem_suitable"] or report.suitable_for_tandems
        daily_weather[report_date]["student_suitable"] = daily_weather[report_date]["student_suitable"] or report.suitable_for_students
        daily_weather[report_date]["fun_jumper_suitable"] = daily_weather[report_date]["fun_jumper_suitable"] or report.suitable_for_fun_jumpers
        daily_weather[report_date]["conditions"].append({
            "time": report.date,
            "conditions": report.condition.value,
            "wind_speed": report.wind_speed,
            "visibility": report.visibility
        })
    
    for day_data in daily_weather.values():
        if day_data["tandem_suitable"]:
            tandem_suitable_days += 1
        if day_data["student_suitable"]:
            student_suitable_days += 1
        if day_data["tandem_suitable"] and day_data["student_suitable"] and day_data["fun_jumper_suitable"]:
            suitable_days += 1
    
    return {
        "date_range": {"start": start_date, "end": end_date, "days": days},
        "suitable_days": suitable_days,
        "tandem_suitable_days": tandem_suitable_days,
        "student_suitable_days": student_suitable_days,
        "daily_weather": daily_weather
    }
