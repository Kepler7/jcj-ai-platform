# Este archivo existe SOLO para que SQLAlchemy registre los modelos
# cuando arranca la app. No pongas lógica aquí.

from app.modules.schools.models import School  # noqa: F401
from app.modules.users.models import User  # noqa: F401
from app.modules.students.models import Student  # noqa: F401
from app.modules.reports.models import StudentReport  # noqa: F401
from app.modules.ai_reports.models import AIReport  # noqa: F401
from app.modules.ai_jobs.models import AIJob  # noqa: F401

# 👇 NUEVO
from app.modules.guardians.models import Guardian  # noqa: F401
from app.modules.share_links.models import ShareLink  # noqa: F401
