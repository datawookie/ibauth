from pydantic import BaseModel


class SessionFeaturesModel(BaseModel):
    env: str
    wlms: bool
    realtime: bool
    bond: bool
    optionChains: bool
    calendar: bool
    newMf: bool


class SessionDetailsModel(BaseModel):
    PAPER_USER_NAME: str | None = None
    IS_PENDING_APPLICANT: bool
    SF_ENABLED: bool
    HARDWARE_INFO: str
    UNIQUE_LOGIN_ID: str
    AUTH_TIME: int
    SF_CONFIG: str
    USER_NAME: str
    CREDENTIAL_TYPE: int
    IS_FREE_TRIAL: bool
    LOGIN_TYPE: int
    LANDING_APP: str
    COUNTERPARTY: str
    CREDENTIAL: str
    RESULT: bool
    IP: str
    USER_ID: int
    EXPIRES: int
    TOKEN: str
    took: int
    IS_MASTER: bool
    features: SessionFeaturesModel
    region: str
