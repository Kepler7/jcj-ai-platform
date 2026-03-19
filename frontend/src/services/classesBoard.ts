import { api } from "../lib/apiClient";

export type ClassItem = {
  id: string;
  name: string;
  school_id: string;
};

export type StudentItem = {
  id: string;
  full_name: string;
  age?: number | null;
  notes?: string | null;
};

export async function fetchSchoolClasses(schoolId: string): Promise<ClassItem[]> {
  // Nuevo endpoint limpio del backend
  // GET /v1/classes/by-school/{school_id}
  return api<ClassItem[]>(`/v1/classes/by-school/${schoolId}`, { auth: true });
}

export async function fetchClassStudents(classId: string): Promise<StudentItem[]> {
  // GET /v1/classes/{class_id}/students
  return api<StudentItem[]>(`/v1/classes/${classId}/students`, { auth: true });
}

export async function assignStudentToClass(classId: string, studentId: string) {
  // POST /v1/classes/{class_id}/students/{student_id}
  return api(`/v1/classes/${classId}/students/${studentId}`, {
    method: "POST",
    auth: true,
  });
}

export async function unassignStudentFromClass(classId: string, studentId: string) {
  // DELETE /v1/classes/{class_id}/students/{student_id}
  return api(`/v1/classes/${classId}/students/${studentId}`, {
    method: "DELETE",
    auth: true,
  });
}