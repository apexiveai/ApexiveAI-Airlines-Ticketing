
import json
import os
import re
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    func,
    select,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

APP_NAME = "ApexiveAI Airline Ticketing API"
API_PREFIX = "/api/v1"
DEMO_MODE = os.getenv("AIRLINE_DEMO_MODE", "true").lower() == "true"

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{(BASE_DIR / 'airline_ticketing.db').as_posix()}",
)

engine_options = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_options)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


# ---------------------------------------------------------
# Database
# ---------------------------------------------------------

class Base(DeclarativeBase):
    pass


class Booking(Base):
    __tablename__ = "airline_bookings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    tenant_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    offer_id: Mapped[str] = mapped_column(String(200), nullable=False)
    traveler_name: Mapped[str] = mapped_column(String(200), nullable=False)
    traveler_email: Mapped[str] = mapped_column(String(320), nullable=False)

    origin: Mapped[str] = mapped_column(String(3), nullable=False)
    destination: Mapped[str] = mapped_column(String(3), nullable=False)
    departure_date: Mapped[date] = mapped_column(Date, nullable=False)

    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="MMK")

    booking_status: Mapped[str] = mapped_column(
        String(50), default="PENDING_CONFIRMATION"
    )
    payment_status: Mapped[str] = mapped_column(
        String(50), default="NOT_PAID"
    )
    ticket_status: Mapped[str] = mapped_column(
        String(50), default="NOT_ISSUED"
    )

    provider_reference: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class SeatAssignment(Base):
    __tablename__ = "airline_seat_assignments"
    __table_args__ = (
        UniqueConstraint("offer_id", "seat_number", name="uq_offer_seat"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    booking_id: Mapped[str] = mapped_column(
        ForeignKey("airline_bookings.id"), unique=True, nullable=False
    )
    offer_id: Mapped[str] = mapped_column(String(200), nullable=False)
    seat_number: Mapped[str] = mapped_column(String(4), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class FlightSchedule(Base):
    __tablename__ = "airline_flight_schedules"
    __table_args__ = (
        UniqueConstraint(
            "flight_number", "departure_at", name="uq_flight_departure"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    flight_number: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    origin: Mapped[str] = mapped_column(String(3), nullable=False)
    destination: Mapped[str] = mapped_column(String(3), nullable=False)
    departure_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    arrival_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    aircraft_registration: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="SCHEDULED", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class CrewMember(Base):
    __tablename__ = "airline_crew_members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    employee_code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class CrewAssignment(Base):
    __tablename__ = "airline_crew_assignments"
    __table_args__ = (
        UniqueConstraint("flight_id", "crew_member_id", name="uq_flight_crew_member"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    flight_id: Mapped[str] = mapped_column(
        ForeignKey("airline_flight_schedules.id"), nullable=False
    )
    crew_member_id: Mapped[str] = mapped_column(
        ForeignKey("airline_crew_members.id"), nullable=False
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class MaintenanceWorkOrder(Base):
    __tablename__ = "airline_maintenance_work_orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    work_order_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    aircraft_registration: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="OPEN", nullable=False)
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------
# API schemas
# ---------------------------------------------------------

class FlightSearchRequest(BaseModel):
    origin: str = Field(min_length=3, max_length=3, examples=["RGN"])
    destination: str = Field(min_length=3, max_length=3, examples=["BKK"])
    departure_date: date
    passengers: int = Field(default=1, ge=1, le=9)


class TravelerBookingRequest(BaseModel):
    offer_id: str = Field(min_length=1, max_length=200)
    traveler_name: str = Field(min_length=2, max_length=200)
    traveler_email: EmailStr
    idempotency_key: str = Field(min_length=8, max_length=100)
    tenant_id: str | None = Field(default=None, max_length=100)


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str | None
    offer_id: str
    traveler_name: str
    traveler_email: str
    origin: str
    destination: str
    departure_date: date
    amount: Decimal
    currency: str
    booking_status: str
    payment_status: str
    ticket_status: str
    provider_reference: str | None
    created_at: datetime


class SeatAssignmentRequest(BaseModel):
    seat_number: str = Field(pattern=r"^(?:[1-9]|[12][0-9]|30)[A-F]$")


class FlightScheduleRequest(BaseModel):
    flight_number: str = Field(min_length=2, max_length=10, pattern=r"^[A-Za-z0-9-]+$")
    origin: str = Field(min_length=3, max_length=3)
    destination: str = Field(min_length=3, max_length=3)
    departure_at: datetime
    arrival_at: datetime
    aircraft_registration: str = Field(min_length=2, max_length=20)
    status: str = Field(default="SCHEDULED", pattern=r"^(SCHEDULED|DELAYED|CANCELLED|DEPARTED|ARRIVED)$")


class FlightStatusRequest(BaseModel):
    status: str = Field(pattern=r"^(SCHEDULED|DELAYED|CANCELLED|DEPARTED|ARRIVED)$")


class CrewMemberRequest(BaseModel):
    employee_code: str = Field(min_length=2, max_length=30)
    full_name: str = Field(min_length=2, max_length=200)
    role: str = Field(min_length=2, max_length=50)


class CrewAssignmentRequest(BaseModel):
    crew_member_id: str


class MaintenanceWorkOrderRequest(BaseModel):
    work_order_number: str = Field(min_length=2, max_length=50)
    aircraft_registration: str = Field(min_length=2, max_length=20)
    category: str = Field(min_length=2, max_length=50)
    description: str = Field(min_length=2, max_length=2000)
    status: str = Field(default="OPEN", pattern=r"^(OPEN|IN_PROGRESS|COMPLETED|DEFERRED)$")
    due_at: datetime | None = None


class MaintenanceStatusRequest(BaseModel):
    status: str = Field(pattern=r"^(OPEN|IN_PROGRESS|COMPLETED|DEFERRED)$")


# ---------------------------------------------------------
# Demo flight provider
# Replace this adapter with an authorized airline/GDS API.
# These offers are simulated and are NOT bookable flights.
# ---------------------------------------------------------

def build_demo_offers(request: FlightSearchRequest) -> list[dict]:
    origin = request.origin.upper()
    destination = request.destination.upper()

    if origin == destination:
        raise HTTPException(
            status_code=422,
            detail="Origin and destination must be different.",
        )

    route = f"{origin}-{destination}-{request.departure_date.isoformat()}"

    return [
        {
            "offer_id": f"DEMO-{route}-01",
            "provider": "DEMO_SIMULATOR",
            "is_demo": True,
            "airline": "Demo Airline A",
            "flight_number": "DA101",
            "origin": origin,
            "destination": destination,
            "departure_date": request.departure_date.isoformat(),
            "departure_time": "09:00",
            "arrival_time": "11:30",
            "duration_minutes": 150,
            "passengers": request.passengers,
            "amount": "185000.00",
            "currency": "MMK",
            "availability_status": "SIMULATED",
        },
        {
            "offer_id": f"DEMO-{route}-02",
            "provider": "DEMO_SIMULATOR",
            "is_demo": True,
            "airline": "Demo Airline B",
            "flight_number": "DB202",
            "origin": origin,
            "destination": destination,
            "departure_date": request.departure_date.isoformat(),
            "departure_time": "14:00",
            "arrival_time": "16:45",
            "duration_minutes": 165,
            "passengers": request.passengers,
            "amount": "245000.00",
            "currency": "MMK",
            "availability_status": "SIMULATED",
        },
    ]


# ---------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------

app = FastAPI(
    title=APP_NAME,
    version="0.1.0",
    description=(
        "Airline ticketing development API. Flight offers and "
        "demo-payment actions are simulated, not live transactions."
    ),
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": APP_NAME,
        "demo_mode": DEMO_MODE,
        "database": "configured",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get(f"{API_PREFIX}/providers")
def list_providers():
    return {
        "providers": [
            {
                "provider_id": "DEMO_SIMULATOR",
                "provider_type": "flight_search",
                "status": "SIMULATED",
                "is_live": False,
            }
        ],
        "message": (
            "No live airline, payment, or ticketing provider is connected."
        ),
    }


@app.post(f"{API_PREFIX}/flights/search")
def search_flights(request: FlightSearchRequest):
    if request.departure_date < date.today():
        raise HTTPException(
            status_code=422,
            detail="Departure date cannot be in the past.",
        )

    offers = build_demo_offers(request)

    return {
        "mode": "DEMO",
        "is_live_inventory": False,
        "search": request.model_dump(mode="json"),
        "results": offers,
        "warning": (
            "These are simulated offers. Prices, schedules, and seats "
            "are not verified with an airline."
        ),
    }


@app.post(
    f"{API_PREFIX}/bookings",
    response_model=BookingResponse,
)
def create_booking(request: TravelerBookingRequest):
    if not DEMO_MODE:
        raise HTTPException(
            status_code=503,
            detail="Booking creation is disabled until a live provider is configured.",
        )

    # Only accept offer IDs generated by this demo adapter.
    match = re.fullmatch(
        r"DEMO-([A-Z]{3})-([A-Z]{3})-(\d{4}-\d{2}-\d{2})-(01|02)",
        request.offer_id,
    )
    if not match:
        raise HTTPException(
            status_code=422,
            detail="Unknown offer. Search flights again to obtain a demo offer.",
        )

    origin, destination, departure_text, option = match.groups()

    if origin == destination:
        raise HTTPException(status_code=422, detail="Invalid route.")

    departure_date = date.fromisoformat(departure_text)
    if departure_date < date.today():
        raise HTTPException(status_code=422, detail="Offer departure date has passed.")

    amount = Decimal("185000.00") if option == "01" else Decimal("245000.00")

    with SessionLocal() as db:
        existing = db.scalar(
            select(Booking).where(
                Booking.idempotency_key == request.idempotency_key
            )
        )
        if existing:
            if (
                existing.offer_id != request.offer_id
                or existing.traveler_email.lower()
                != str(request.traveler_email).lower()
            ):
                raise HTTPException(
                    status_code=409,
                    detail="Idempotency key was already used for a different request.",
                )
            return existing

        booking = Booking(
            id=str(uuid.uuid4()),
            idempotency_key=request.idempotency_key,
            tenant_id=request.tenant_id,
            offer_id=request.offer_id,
            traveler_name=request.traveler_name,
            traveler_email=str(request.traveler_email),
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            amount=amount,
            currency="MMK",
            booking_status="PENDING_CONFIRMATION",
            payment_status="NOT_PAID",
            ticket_status="NOT_ISSUED",
        )

        db.add(booking)

        try:
            db.commit()
            db.refresh(booking)
            return booking
        except IntegrityError:
            db.rollback()
            existing = db.scalar(
                select(Booking).where(
                    Booking.idempotency_key == request.idempotency_key
                )
            )
            if existing:
                return existing
            raise HTTPException(
                status_code=409,
                detail="Could not create booking. Retry with a new idempotency key.",
            )


@app.get(
    f"{API_PREFIX}/bookings/{{booking_id}}",
    response_model=BookingResponse,
)
def get_booking(booking_id: str):
    with SessionLocal() as db:
        booking = db.get(Booking, booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found.")
        return booking


@app.post(
    f"{API_PREFIX}/bookings/{{booking_id}}/demo-payment-confirmation",
    response_model=BookingResponse,
)
def demo_payment_confirmation(
    booking_id: str,
    x_demo_payment_reference: str = Header(
        default="LOCAL-DEMO-PAYMENT",
        alias="X-Demo-Payment-Reference",
    ),
):
    if not DEMO_MODE:
        raise HTTPException(
            status_code=403,
            detail="Demo payment confirmation is disabled.",
        )

    if not x_demo_payment_reference.startswith("LOCAL-DEMO-"):
        raise HTTPException(
            status_code=422,
            detail="Only LOCAL-DEMO- references are accepted in demo mode.",
        )

    with SessionLocal() as db:
        booking = db.get(Booking, booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found.")

        if booking.payment_status == "NOT_PAID":
            booking.payment_status = "DEMO_CONFIRMED"
            booking.booking_status = "PAYMENT_DEMO_CONFIRMED_TICKET_PENDING"
            booking.provider_reference = x_demo_payment_reference
            db.commit()
            db.refresh(booking)

        # IMPORTANT: demo payment never issues a real ticket.
        return booking


@app.get(f"{API_PREFIX}/core/overview")
def get_core_overview():
    with SessionLocal() as db:
        return {
            "system": "Myanmar International Airlines Core System",
            "mode": "DEMO" if DEMO_MODE else "INTEGRATION_REQUIRED",
            "modules": {
                "pss": {
                    "bookings": db.scalar(select(func.count()).select_from(Booking)) or 0,
                    "seat_assignments": db.scalar(
                        select(func.count()).select_from(SeatAssignment)
                    ) or 0,
                    "live_provider_connected": False,
                },
                "operations": {
                    "scheduled_flights": db.scalar(
                        select(func.count()).select_from(FlightSchedule)
                    ) or 0,
                    "crew_members": db.scalar(
                        select(func.count()).select_from(CrewMember)
                    ) or 0,
                },
                "mro": {
                    "open_work_orders": db.scalar(
                        select(func.count()).select_from(MaintenanceWorkOrder).where(
                            MaintenanceWorkOrder.status != "COMPLETED"
                        )
                    ) or 0,
                },
            },
            "limitations": [
                "No Amadeus, Sabre, Navitaire, Jeppesen, AMOS, SAP, or Maximo connection is configured.",
                "This application does not issue real tickets or determine aircraft airworthiness.",
            ],
        }


@app.post(f"{API_PREFIX}/bookings/{{booking_id}}/seat-assignment")
def assign_booking_seat(booking_id: str, request: SeatAssignmentRequest):
    with SessionLocal() as db:
        booking = db.get(Booking, booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found.")

        existing = db.scalar(
            select(SeatAssignment).where(SeatAssignment.booking_id == booking_id)
        )
        if existing:
            if existing.seat_number == request.seat_number:
                return existing
            raise HTTPException(
                status_code=409,
                detail="A seat is already assigned to this booking.",
            )

        assignment = SeatAssignment(
            id=str(uuid.uuid4()),
            booking_id=booking.id,
            offer_id=booking.offer_id,
            seat_number=request.seat_number,
        )
        db.add(assignment)
        try:
            db.commit()
            db.refresh(assignment)
            return assignment
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="That seat is already assigned for this flight offer.",
            )


@app.get(f"{API_PREFIX}/operations/flights")
def list_flight_schedules():
    with SessionLocal() as db:
        return db.scalars(
            select(FlightSchedule).order_by(FlightSchedule.departure_at)
        ).all()


@app.post(f"{API_PREFIX}/operations/flights", status_code=201)
def create_flight_schedule(request: FlightScheduleRequest):
    origin = request.origin.upper()
    destination = request.destination.upper()
    if origin == destination:
        raise HTTPException(status_code=422, detail="Origin and destination must differ.")
    if request.arrival_at <= request.departure_at:
        raise HTTPException(
            status_code=422, detail="Arrival must be later than departure."
        )

    flight = FlightSchedule(
        id=str(uuid.uuid4()),
        flight_number=request.flight_number.upper(),
        origin=origin,
        destination=destination,
        departure_at=request.departure_at,
        arrival_at=request.arrival_at,
        aircraft_registration=request.aircraft_registration.upper(),
        status=request.status,
    )
    with SessionLocal() as db:
        db.add(flight)
        try:
            db.commit()
            db.refresh(flight)
            return flight
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="A flight with this number and departure time already exists.",
            )


@app.patch(f"{API_PREFIX}/operations/flights/{{flight_id}}/status")
def update_flight_status(flight_id: str, request: FlightStatusRequest):
    with SessionLocal() as db:
        flight = db.get(FlightSchedule, flight_id)
        if not flight:
            raise HTTPException(status_code=404, detail="Flight schedule not found.")
        flight.status = request.status
        db.commit()
        db.refresh(flight)
        return flight


@app.get(f"{API_PREFIX}/operations/crew")
def list_crew_members():
    with SessionLocal() as db:
        return db.scalars(
            select(CrewMember).order_by(CrewMember.employee_code)
        ).all()


@app.post(f"{API_PREFIX}/operations/crew", status_code=201)
def create_crew_member(request: CrewMemberRequest):
    crew_member = CrewMember(
        id=str(uuid.uuid4()),
        employee_code=request.employee_code.upper(),
        full_name=request.full_name,
        role=request.role.upper(),
    )
    with SessionLocal() as db:
        db.add(crew_member)
        try:
            db.commit()
            db.refresh(crew_member)
            return crew_member
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="A crew member with this employee code already exists.",
            )


@app.post(f"{API_PREFIX}/operations/flights/{{flight_id}}/crew", status_code=201)
def assign_crew_member(flight_id: str, request: CrewAssignmentRequest):
    with SessionLocal() as db:
        flight = db.get(FlightSchedule, flight_id)
        if not flight:
            raise HTTPException(status_code=404, detail="Flight schedule not found.")
        crew_member = db.get(CrewMember, request.crew_member_id)
        if not crew_member:
            raise HTTPException(status_code=404, detail="Crew member not found.")
        if not crew_member.active:
            raise HTTPException(status_code=409, detail="Crew member is inactive.")

        conflicting_assignment = db.scalar(
            select(CrewAssignment.id)
            .join(FlightSchedule, CrewAssignment.flight_id == FlightSchedule.id)
            .where(
                CrewAssignment.crew_member_id == crew_member.id,
                FlightSchedule.departure_at < flight.arrival_at,
                FlightSchedule.arrival_at > flight.departure_at,
            )
        )
        if conflicting_assignment:
            raise HTTPException(
                status_code=409,
                detail="Crew member already has an overlapping flight assignment.",
            )

        assignment = CrewAssignment(
            id=str(uuid.uuid4()),
            flight_id=flight_id,
            crew_member_id=crew_member.id,
        )
        db.add(assignment)
        try:
            db.commit()
            db.refresh(assignment)
            return assignment
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="This crew member is already assigned to the flight.",
            )


@app.get(f"{API_PREFIX}/operations/flights/{{flight_id}}/crew")
def list_flight_crew(flight_id: str):
    with SessionLocal() as db:
        if not db.get(FlightSchedule, flight_id):
            raise HTTPException(status_code=404, detail="Flight schedule not found.")
        assignments = db.execute(
            select(CrewAssignment, CrewMember)
            .join(CrewMember, CrewAssignment.crew_member_id == CrewMember.id)
            .where(CrewAssignment.flight_id == flight_id)
            .order_by(CrewMember.employee_code)
        ).all()
        return [
            {
                "assignment_id": assignment.id,
                "crew_member_id": member.id,
                "employee_code": member.employee_code,
                "full_name": member.full_name,
                "role": member.role,
                "active": member.active,
            }
            for assignment, member in assignments
        ]


@app.get(f"{API_PREFIX}/maintenance/work-orders")
def list_maintenance_work_orders():
    with SessionLocal() as db:
        return db.scalars(
            select(MaintenanceWorkOrder).order_by(MaintenanceWorkOrder.opened_at.desc())
        ).all()


@app.post(f"{API_PREFIX}/maintenance/work-orders", status_code=201)
def create_maintenance_work_order(request: MaintenanceWorkOrderRequest):
    work_order = MaintenanceWorkOrder(
        id=str(uuid.uuid4()),
        work_order_number=request.work_order_number.upper(),
        aircraft_registration=request.aircraft_registration.upper(),
        category=request.category.upper(),
        description=request.description,
        status=request.status,
        due_at=request.due_at,
    )
    with SessionLocal() as db:
        db.add(work_order)
        try:
            db.commit()
            db.refresh(work_order)
            return work_order
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="A work order with this number already exists.",
            )


@app.patch(f"{API_PREFIX}/maintenance/work-orders/{{work_order_id}}/status")
def update_maintenance_work_order_status(
    work_order_id: str, request: MaintenanceStatusRequest
):
    with SessionLocal() as db:
        work_order = db.get(MaintenanceWorkOrder, work_order_id)
        if not work_order:
            raise HTTPException(status_code=404, detail="Work order not found.")
        work_order.status = request.status
        db.commit()
        db.refresh(work_order)
        return work_order
