from enum import Enum

class Role(str, Enum):
    platform_admin = "platform_admin"
    school_admin = "school_admin"
    teacher = "teacher"
