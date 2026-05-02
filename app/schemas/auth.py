from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    company_name: str
    company_slug: str


class EmployeeRegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    company_slug: str


class CompanyRegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    company_name: str
    company_slug: str
    super_admin_token: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
