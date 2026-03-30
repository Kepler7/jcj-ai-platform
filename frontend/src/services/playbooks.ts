import { api } from "../lib/apiClient";

export type PlaybookSyncStartResponse = {
  ok: boolean;
  job_id: string;
  status: string;
};

export type PlaybookSyncStatusResponse = {
  id?: number;
  job_id: string;
  status: string;
  input_source?: string | null;
  output_path?: string | null;
  trigger_type?: string | null;
  error_message?: string | null;
  result?: {
    loaded_count?: number;
    chroma_collection?: string;
    [key: string]: unknown;
  } | null;
  created_at?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  is_finished?: boolean;
  is_failed?: boolean;
};

export async function startPlaybookSync(): Promise<PlaybookSyncStartResponse> {
  return api<PlaybookSyncStartResponse>("/v1/playbooks/sync", {
    method: "POST",
    auth: true,
  });
}

export async function getLatestPlaybookSync(): Promise<PlaybookSyncStatusResponse> {
  return api<PlaybookSyncStatusResponse>("/v1/playbooks/sync/latest", {
    method: "GET",
    auth: true,
  });
}

export async function getPlaybookSyncByJobId(
  jobId: string
): Promise<PlaybookSyncStatusResponse> {
  return api<PlaybookSyncStatusResponse>(`/v1/playbooks/sync/${jobId}`, {
    method: "GET",
    auth: true,
  });
}