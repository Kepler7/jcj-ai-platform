export type Guardian = {
  id: string;

  student_id: string;
  school_id: string;

  full_name: string;
  whatsapp_phone: string | null;
  relationship: string | null;

  is_primary: boolean;
  is_active: boolean;

  // --- Comunicación ---
  consent_to_contact: boolean;
  receive_whatsapp: boolean;

  // --- Meta ---
  notes: string | null;

  created_at: string;
  updated_at: string;
};
