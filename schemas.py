"""
DocDor Database Schemas

Each Pydantic model below represents a MongoDB collection. The collection
name is the lowercase of the class name. Example: class User -> "user".

These schemas are used for request/response validation and to keep a
consistent structure across Doctor/Receptionist/Patient apps.
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Literal
from datetime import datetime

# Core identities
class User(BaseModel):
    role: Literal["doctor", "receptionist", "patient"] = Field(..., description="System role")
    email: Optional[EmailStr] = Field(None, description="Login email")
    phone: str = Field(..., description="Primary phone number")
    name: str = Field(..., description="Full name")
    password_hash: Optional[str] = Field(None, description="Hashed password (store hashed only)")
    two_factor_enabled: bool = Field(False, description="2FA toggle for staff")
    is_active: bool = Field(True, description="Account status")

class Doctor(BaseModel):
    user_id: str = Field(..., description="Reference to user")
    specialization: str = Field(..., description="Primary specialization")
    sub_specializations: Optional[List[str]] = Field(default=None, description="Other specialties")
    qualification: Optional[str] = None
    experience_years: Optional[int] = Field(default=None, ge=0)
    clinic_name: Optional[str] = None
    consultation_fee: Optional[float] = Field(default=None, ge=0)
    online_available: bool = True
    clinic_available: bool = True

class Patient(BaseModel):
    user_id: Optional[str] = Field(default=None, description="Reference to user if registered")
    name: str
    phone: str
    dob: Optional[str] = Field(default=None, description="YYYY-MM-DD")
    age: Optional[int] = Field(default=None, ge=0, le=120)
    gender: Optional[Literal["male", "female", "other"]] = None
    medical_history: Optional[List[str]] = Field(default=None, description="Major conditions")
    allergies: Optional[List[str]] = None
    notes: Optional[str] = None

# Appointments & consultation
class Appointment(BaseModel):
    doctor_id: str = Field(..., description="Doctor reference id")
    patient_id: str = Field(..., description="Patient reference id")
    type: Literal["clinic", "online"]
    status: Literal["scheduled", "completed", "cancelled"] = "scheduled"
    visit_kind: Literal["consultation", "follow-up"] = "consultation"
    scheduled_at: datetime
    reason: Optional[str] = None
    visit_count: Optional[int] = Field(default=1, ge=1, description="How many times patient consulted this doctor")
    video_session_id: Optional[str] = Field(default=None, description="Twilio/Agora session id for online")

# Prescription
class MedicationItem(BaseModel):
    drug_name: str
    dosage: str = Field(..., description="e.g., 500mg")
    frequency: str = Field(..., description="e.g., 1-0-1")
    duration: str = Field(..., description="e.g., 5 days")
    notes: Optional[str] = None

class LabItem(BaseModel):
    test_name: str
    notes: Optional[str] = None

class Prescription(BaseModel):
    appointment_id: str
    doctor_id: str
    patient_id: str
    symptoms: List[str]
    medications: List[MedicationItem] = []
    labs: List[LabItem] = []
    advice: Optional[str] = None
    follow_up_date: Optional[str] = Field(default=None, description="YYYY-MM-DD")
    pdf_url: Optional[str] = Field(default=None, description="Link to generated eRx PDF if any")

# Chat and Payments
class ChatMessage(BaseModel):
    room_id: str = Field(..., description="patient-doctor room id")
    sender_id: str
    receiver_id: str
    body: str
    media_url: Optional[str] = None
    sent_at: Optional[datetime] = None

class Payment(BaseModel):
    appointment_id: str
    amount: float = Field(..., ge=0)
    currency: Literal["INR", "USD"] = "INR"
    status: Literal["pending", "paid", "failed", "refunded"] = "pending"
    provider: Literal["stripe", "razorpay"]
    provider_payment_id: Optional[str] = None

# Catalogs for search (simple collections to seed or external integration later)
class Drug(BaseModel):
    name: str
    salt: Optional[str] = None

class LabTest(BaseModel):
    name: str
    category: Optional[str] = None
