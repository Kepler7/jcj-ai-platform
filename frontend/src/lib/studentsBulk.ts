import { apiForm } from "./apiClient";

export type BulkRowError = {
  row: number;
  field?: string | null;
  message: string;
};

export type BulkStudentsPreviewResponse = {
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  will_create_classes: string[];
  errors: BulkRowError[];
  sample: any[];
};

export type BulkStudentsApplyResponse = {
  created_students: number;
  created_classes: number;
  created_student_class_links: number;
  skipped_rows: number;
};

export async function bulkStudentsPreview(params: { file: File; schoolId?: string }) {
  const form = new FormData();
  form.append("file", params.file);

  const qs = params.schoolId ? `?school_id=${encodeURIComponent(params.schoolId)}` : "";
  return apiForm<BulkStudentsPreviewResponse>(`/v1/students/bulk/preview${qs}`, form, { auth: true });
}

export async function bulkStudentsApply(params: { file: File; schoolId?: string }) {
  const form = new FormData();
  form.append("file", params.file);

  const qs = params.schoolId ? `?school_id=${encodeURIComponent(params.schoolId)}` : "";
  return apiForm<BulkStudentsApplyResponse>(`/v1/students/bulk/apply${qs}`, form, { auth: true });
}