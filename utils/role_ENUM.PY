from enum import Enum
from typing import Dict


class RoleEnum(str, Enum):
    PATIENT_DENTAL = "patient_dental"
    PATIENT_DIABETES = "patient_diabetes"
    DOCTOR_DENTAL = "doctor_dental"
    DOCTOR_ENDOCRINE = "doctor_endocrine"


ROLE_DISPLAY_NAME: Dict[RoleEnum, str] = {
    RoleEnum.PATIENT_DENTAL: "Bệnh nhân nha khoa",
    RoleEnum.PATIENT_DIABETES: "Bệnh nhân đái tháo đường",
    RoleEnum.DOCTOR_DENTAL: "Bác sĩ nha khoa",
    RoleEnum.DOCTOR_ENDOCRINE: "Bác sĩ nội tiết",
}

ROLE_DESCRIPTION: Dict[RoleEnum, str] = {
    RoleEnum.PATIENT_DENTAL: "Dành cho người cần tư vấn về các vấn đề răng miệng, nha chu, và chăm sóc sức khỏe răng miệng",
    RoleEnum.PATIENT_DIABETES: "Dành cho người mắc đái tháo đường cần tư vấn về mối liên hệ giữa bệnh đái tháo đường và sức khỏe răng miệng",
    RoleEnum.DOCTOR_DENTAL: "Dành cho bác sĩ nha khoa cần tư vấn về tác động của đái tháo đường đến điều trị nha khoa",
    RoleEnum.DOCTOR_ENDOCRINE: "Dành cho bác sĩ nội tiết cần hiểu về biến chứng răng miệng ở bệnh nhân đái tháo đường",
}
