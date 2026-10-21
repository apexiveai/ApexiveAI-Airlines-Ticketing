".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8018 --reload

## Myanmar International Airlines Core System foundation

This project now provides a local API foundation for three airline core-system
areas, alongside its existing demo booking flow:

- **PSS** — demo flight search and booking, plus a seat-assignment endpoint
  for a booking. A seat can only be assigned once per offer.
- **Operations and crew** — create flight schedules and crew records, then
  assign active crew members to scheduled flights.
- **MRO** — create aircraft maintenance work orders and update their status.

Start the API from the `backend` directory, then open
`http://127.0.0.1:8018/docs` for request/response examples. The main endpoints
are:

| Purpose | Endpoint |
| --- | --- |
| Core module summary | `GET /api/v1/core/overview` |
| Assign a seat to a booking | `POST /api/v1/bookings/{booking_id}/seat-assignment` |
| Flight schedules | `GET, POST /api/v1/operations/flights` |
| Update flight status | `PATCH /api/v1/operations/flights/{flight_id}/status` |
| Crew members | `GET, POST /api/v1/operations/crew` |
| Assign crew to flight | `POST /api/v1/operations/flights/{flight_id}/crew` |
| View flight crew | `GET /api/v1/operations/flights/{flight_id}/crew` |
| Maintenance work orders | `GET, POST /api/v1/maintenance/work-orders` |
| Update work-order status | `PATCH /api/v1/maintenance/work-orders/{work_order_id}/status` |

The API stores these records in the configured database. It is a development
foundation, not a connection to Myanmar International Airlines' production
systems: no Amadeus Altéa, Sabre Sonic, Navitaire, Jeppesen, Sabre AirCentre,
AMOS, SAP, or IBM Maximo credentials/adapters are configured. Flight offers
and payments remain simulated, seats are not live inventory, and these
maintenance records must not be treated as aircraft release-to-service or
airworthiness approvals. Production integration requires authorized vendor
access, agreed data mappings, and operational/security validation.