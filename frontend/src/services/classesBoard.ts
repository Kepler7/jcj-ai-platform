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

export type TeacherItem = {
  id: string;
  email: string;
  role: "teacher";
  school_id: string;
  is_active: boolean;
};

export async function createClass(schoolId: string, name: string): Promise<ClassItem> {
  // POST /v1/classes
  return api<ClassItem>("/v1/classes", {
    method: "POST",
    auth: true,
    body: {
      school_id: schoolId,
      name,
    },
  });
}

export async function fetchSchoolClasses(schoolId: string): Promise<ClassItem[]> {
  // Nuevo endpoint limpio del backend
  // GET /v1/classes/by-school/{school_id}
  return api<ClassItem[]>(`/v1/classes/by-school/${schoolId}`, { auth: true });
}

export async function fetchMyClasses(): Promise<ClassItem[]> {
  // GET /v1/classes/me
  return api<ClassItem[]>("/v1/classes/me", { auth: true });
}

export async function fetchSchoolTeachers(schoolId: string): Promise<TeacherItem[]> {
  return api<TeacherItem[]>(`/v1/users/by-school/${schoolId}/teachers`, { auth: true });
}

export async function fetchClassStudents(classId: string): Promise<StudentItem[]> {
  // GET /v1/classes/{class_id}/students
  return api<StudentItem[]>(`/v1/classes/${classId}/students`, { auth: true });
}

export async function fetchClassTeachers(classId: string): Promise<TeacherItem[]> {
  return api<TeacherItem[]>(`/v1/classes/${classId}/teachers`, { auth: true });
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

export async function createTeacher(params: {
  schoolId: string;
  email: string;
  password: string;
}): Promise<TeacherItem> {
  return api<TeacherItem>("/v1/users", {
    method: "POST",
    auth: true,
    body: {
      email: params.email,
      password: params.password,
      role: "teacher",
      school_id: params.schoolId,
    },
  });
}

export async function assignTeacherToClass(classId: string, teacherId: string) {
  return api(`/v1/classes/${classId}/teachers/${teacherId}`, {
    method: "POST",
    auth: true,
  });
}

export async function unassignTeacherFromClass(classId: string, teacherId: string) {
  return api(`/v1/classes/${classId}/teachers/${teacherId}`, {
    method: "DELETE",
    auth: true,
  });
}

export async function replaceClassTeachers(classId: string, teacherIds: string[]) {
  return api(`/v1/classes/${classId}/teachers`, {
    method: "PUT",
    auth: true,
    body: { teacher_ids: teacherIds },
  });
}
