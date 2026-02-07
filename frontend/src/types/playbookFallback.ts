export type PlaybookFallbackEvent = {
  id: string;
  school_id: string;
  student_id: string;
  report_id: string;
  ai_report_id: string | null;

  topic_nucleo: string | null;
  context: string | string[] | null; // en tu meta a veces viene lista
  reason: string;

  query_text: string | null;
  model_output_summary: string | null;

  created_by_user_id: string | null;
  created_at: string;
  resolved_at: string | null;
};
