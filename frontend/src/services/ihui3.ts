import { api } from "../lib/apiClient";

export type Ihui3WizardAnswerValue = "yes" | "no" | "sometimes";

export type Ihui3ValidationQuestion = {
  text?: string;
  question?: string; // compatibilidad temporal con wizard viejo
  why_it_matters?: string;
  nucleus?: string;
  subskill?: string;
  playbook_id: string;
  question_id: string;
};

export type Ihui3Hypothesis = {
  name: string;
  confidence?: "low" | "medium" | "high" | string;
  reasoning?: string;
};

export type Ihui3Strategy = {
  micro_objective?: string;
  steps?: string[];
  family_steps?: string[];
  frequency?: string;
  duration?: string;
  progress_indicator?: string;
  escalation?: string | null;
  status?: "requires_validation" | "validated" | string;
};

export type Ihui3ValidationAnswer = {
  playbook_id: string;
  question_id: string;
  answer: Ihui3WizardAnswerValue;
};

export type Ihui3WizardResponse = {
  ai_report_id: string;
  report_id: string;
  student_id: string;
  school_id: string;
  engine_version: "ihui_3";
  validation_status:
    | "needs_validation_answers"
    | "validated"
    | "validated_combined"
    | "pending_human_review"
    | string;
  wizard_required: boolean;
  questions: Ihui3ValidationQuestion[];
  wizard?: {
    questions?: Ihui3ValidationQuestion[];
    allowed_answers?: Ihui3WizardAnswerValue[];
    required?: boolean;
    decision?: string;
    selected_playbook_id?: string | null;
    combined_playbook_ids?: string[];
    confidence_after_validation?: "low" | "medium" | "high" | string;
    candidate_scores?: Array<Record<string, unknown>>;
    answers?: Ihui3ValidationAnswer[];
  };
  wizard_candidates?: Array<Record<string, unknown>>;
  wizard_result?: Record<string, unknown> | null;
  hypotheses: Ihui3Hypothesis[];
  strategy: Ihui3Strategy;
  match?: Record<string, unknown> | null;
  fallback_used: boolean;
  fallback_reason?: string | null;
  review_status?: string | null;
  validation_result?: Record<string, unknown> | null;
  answers: Ihui3ValidationAnswer[];
};

export type Ihui3SubmitAnswersResponse = {
  ai_report_id: string;
  validation_status: string;
  wizard_required: boolean;
  message: string;
};

export type Ihui3WizardSubmitState =
  | "idle"
  | "submitting_answers"
  | "refining_strategy"
  | "refreshing_result"
  | "success"
  | "error";

export function getIhui3WizardSubmitLabel(
  state: Ihui3WizardSubmitState
): string {
  switch (state) {
    case "submitting_answers":
      return "Enviando respuestas...";
    case "refining_strategy":
      return "Afinando estrategia...";
    case "refreshing_result":
      return "Actualizando resultado...";
    case "success":
      return "Estrategia actualizada";
    case "error":
      return "No se pudieron enviar las respuestas";
    default:
      return "Enviar respuestas";
  }
}

export function getIhui3Wizard(
  aiReportId: string
): Promise<Ihui3WizardResponse> {
  return api<Ihui3WizardResponse>(
    `/v1/ihui3/reports/${encodeURIComponent(aiReportId)}/wizard`,
    {
      auth: true,
    }
  );
}

export function submitIhui3ValidationAnswers(
  aiReportId: string,
  answers: Ihui3ValidationAnswer[]
): Promise<Ihui3SubmitAnswersResponse> {
  return api<Ihui3SubmitAnswersResponse>(
    `/v1/ihui3/reports/${encodeURIComponent(
      aiReportId
    )}/validation-answers`,
    {
      method: "POST",
      auth: true,
      body: { answers },
    }
  );
}

export type Ihui3SyncResponse = {
  status: string;
  source?: string | null;
  output?: string | null;
  items_count?: number;
  dictionary_items_count?: number;
  dictionary_output?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  error?: string | null;
};

export function syncIhui3Knowledge(): Promise<Ihui3SyncResponse> {
  return api<Ihui3SyncResponse>("/v1/ihui3/sync", {
    method: "POST",
    auth: true,
  });
}

export function getLatestIhui3Sync(): Promise<Ihui3SyncResponse> {
  return api<Ihui3SyncResponse>("/v1/ihui3/sync/latest", {
    auth: true,
  });
}