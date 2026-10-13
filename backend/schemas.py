"""JSON boundary. Assessment field names are intentionally camelCase."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    password: str


class RegisterInput(LoginInput):
    password: str = Field(min_length=8, max_length=128)


class SiteInput(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    clientName: str = Field(min_length=1, max_length=160)
    address: str = Field(min_length=1, max_length=300)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    roofAreaM2: float | None = Field(default=None, gt=0, le=100_000)
    peakKwp: float = Field(gt=0, le=1000)

    @field_validator("clientName", "address", mode="before")
    @classmethod
    def strip_nonempty(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value


def site_from_row(row) -> dict:
    return {
        "id": row["id"],
        "clientName": row["client_name"],
        "address": row["address"],
        "latitude": row["latitude"],
        "longitude": row["longitude"],
        "roofAreaM2": row["roof_area_m2"],
        "peakKwp": row["peak_kwp"],
    }
