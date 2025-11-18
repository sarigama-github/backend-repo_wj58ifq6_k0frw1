import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents
import schemas as app_schemas

app = FastAPI(title="DocDor API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Utilities
def serialize_value(v: Any):
    try:
        from bson import ObjectId  # type: ignore
    except Exception:
        ObjectId = None  # noqa: N806

    if ObjectId and isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, list):
        return [serialize_value(i) for i in v]
    if isinstance(v, dict):
        return {k: serialize_value(val) for k, val in v.items()}
    return v


def serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {k: serialize_value(v) for k, v in doc.items()}


@app.get("/")
def read_root():
    return {"message": "DocDor backend is running"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from DocDor API"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": [],
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, "name") else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:  # pragma: no cover - info only
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:  # pragma: no cover - info only
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# Schema explorer for frontend tooling
@app.get("/schema")
def get_schema():
    models = {}
    for name in dir(app_schemas):
        obj = getattr(app_schemas, name)
        if isinstance(obj, type) and issubclass(obj, BaseModel) and obj is not BaseModel:
            models[name] = obj.model_json_schema()
    return {"models": models}


# Request models (reuse core pydantic classes directly)
PatientModel = app_schemas.Patient
AppointmentModel = app_schemas.Appointment
PrescriptionModel = app_schemas.Prescription


# Patients
@app.post("/patients")
def create_patient(patient: PatientModel):
    patient_id = create_document("patient", patient)
    return {"id": patient_id}


@app.get("/patients")
def search_patients(q: Optional[str] = Query(default=None, description="name or phone contains")):
    flt = {}
    if q:
        # simple OR search with regex
        flt = {
            "$or": [
                {"name": {"$regex": q, "$options": "i"}},
                {"phone": {"$regex": q}},
            ]
        }
    items = [serialize_doc(d) for d in get_documents("patient", flt, limit=50)]
    return {"items": items}


# Appointments
@app.post("/appointments")
def create_appointment(appointment: AppointmentModel):
    appt_id = create_document("appointment", appointment)
    return {"id": appt_id}


@app.get("/appointments")
def list_appointments(
    doctor_id: Optional[str] = None,
    patient_id: Optional[str] = None,
    status: Optional[str] = None,
    type: Optional[str] = None,  # clinic | online
    limit: int = 50,
):
    flt: Dict[str, Any] = {}
    if doctor_id:
        flt["doctor_id"] = doctor_id
    if patient_id:
        flt["patient_id"] = patient_id
    if status:
        flt["status"] = status
    if type:
        flt["type"] = type

    docs = get_documents("appointment", flt, limit=limit)
    return {"items": [serialize_doc(d) for d in docs]}


# Prescription
@app.post("/prescriptions")
def create_prescription(prescription: PrescriptionModel):
    # basic guard: appointment/doctor/patient ids exist could be validated later
    presc_id = create_document("prescription", prescription)
    return {"id": presc_id}


@app.get("/prescriptions")
def list_prescriptions(patient_id: Optional[str] = None, appointment_id: Optional[str] = None):
    flt: Dict[str, Any] = {}
    if patient_id:
        flt["patient_id"] = patient_id
    if appointment_id:
        flt["appointment_id"] = appointment_id
    docs = get_documents("prescription", flt, limit=100)
    return {"items": [serialize_doc(d) for d in docs]}


# Simple metrics for Doctor Home
@app.get("/metrics/doctor/{doctor_id}")
def doctor_metrics(doctor_id: str):
    total_appts = len(get_documents("appointment", {"doctor_id": doctor_id}))
    completed = len(
        get_documents("appointment", {"doctor_id": doctor_id, "status": "completed"})
    )
    upcoming = get_documents(
        "appointment",
        {"doctor_id": doctor_id, "status": "scheduled"},
        limit=20,
    )
    # Return just enough for the home wireframe
    return {
        "totals": {
            "appointments": total_appts,
            "completed": completed,
        },
        "upcoming": [
            {
                "patient_id": a.get("patient_id"),
                "visit_count": a.get("visit_count", 1),
                "visit_kind": a.get("visit_kind", "consultation"),
                "type": a.get("type"),
                "scheduled_at": serialize_value(a.get("scheduled_at")),
                "appointment_id": str(a.get("_id")),
            }
            for a in upcoming
        ],
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
