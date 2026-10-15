export interface User {
  id: string;
  email: string;
  display_name: string;
  is_staff: boolean;
  is_superuser?: boolean;
  is_active?: boolean;
  created_at: string;
}

export interface AdminOverview {
  reports: {
    total: number;
    lost_open: number;
    found_open: number;
    returned: number;
    withdrawn: number;
    expired: number;
    hidden: number;
    removed: number;
    flagged?: number;
    total_abuse_flags?: number;
  };
  claims: {
    total: number;
    pending: number;
    approved: number;
    completed: number;
    rejected: number;
  };
  custody: {
    total_transfers: number;
    pending_transfers: number;
  };
  users: {
    total: number;
    active: number;
    suspended: number;
    staff: number;
  };
  locations: {
    active_count: number;
  };
  system: {
    nim_enabled: boolean;
    nim_model: string;
    embeddings_count: number;
    audit_events_count: number;
  };
}

export interface AuditEventItem {
  id: string;
  actor: string | null;
  actor_email: string | null;
  actor_name: string;
  action: string;
  entity_type: string;
  entity_id: string;
  request_id: string;
  metadata_redacted: Record<string, any>;
  created_at: string;
}

export interface AdminReportItem {
  id: string;
  report_type: 'LOST' | 'FOUND';
  category: string;
  title: string;
  public_description: string;
  status: 'OPEN' | 'WITHDRAWN' | 'EXPIRED' | 'RETURNED';
  visibility: 'ACTIVE' | 'HIDDEN' | 'REMOVED';
  last_seen_at?: string;
  found_at?: string;
  last_seen_location_name?: string;
  found_location_name?: string;
  current_holding_location_name?: string;
  created_by_email?: string;
  abuse_flags_count?: number;
  flag_details?: Array<{
    id: string;
    reporter_email: string;
    reason: string;
    reason_display: string;
    details: string;
    created_at: string;
  }>;
  created_at: string;
  updated_at: string;
}

export interface AdminUserItem {
  id: string;
  email: string;
  display_name: string;
  is_active: boolean;
  is_staff: boolean;
  is_superuser: boolean;
  created_at: string;
  updated_at: string;
  memberships: {
    id: string;
    location_name: string;
    role: string;
    is_active: boolean;
  }[];
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface Location {
  id: string;
  name: string;
  location_type: 'LIBRARY' | 'SECURITY_OFFICE' | 'BUS_SERVICE' | 'OTHER';
  description: string;
  is_active: boolean;
}

export interface ReportImage {
  id: string;
  url: string;
  content_type: string;
  size_bytes: number;
}

export interface ItemReport {
  id: string;
  report_type: 'LOST' | 'FOUND';
  category: 'ELECTRONICS' | 'BAG' | 'CLOTHING' | 'DOCUMENT' | 'ACCESSORY' | 'KEYS' | 'BOTTLE' | 'OTHER';
  title: string;
  public_description: string;
  last_seen_at?: string;
  found_at?: string;
  last_seen_location?: Location;
  found_location?: Location;
  current_holding_location?: Location;
  status: 'OPEN' | 'WITHDRAWN' | 'EXPIRED' | 'RETURNED';
  images?: ReportImage[];
  created_at: string;
}

export interface MatchCandidate {
  candidate_report_id: string;
  category: string;
  title: string;
  public_description: string;
  safe_location_label: string;
  reported_at: string;
  match_label: string;
}

export interface MatchResponse {
  report_id: string;
  retrieval_mode: 'hybrid' | 'keyword_baseline';
  matches: MatchCandidate[];
}

export interface ClaimEvidence {
  id: string;
  evidence_type: 'TEXT' | 'IMAGE' | 'OTHER';
  private_value: string;
  created_at: string;
}

export interface Claim {
  id: string;
  report: string;
  report_title: string;
  claimant: string;
  claimant_email: string;
  status: 'PENDING' | 'NEEDS_INFO' | 'APPROVED' | 'REJECTED' | 'CANCELLED' | 'COMPLETED';
  claimant_statement: string;
  review_note_private?: string;
  decision_at?: string;
  created_at: string;
  evidences?: ClaimEvidence[];
}

export interface CustodyEvent {
  id: string;
  report: string;
  event_type: 'REGISTERED' | 'TRANSFER_REQUESTED' | 'TRANSFER_ACCEPTED' | 'HANDOVER_COMPLETED' | 'CORRECTION';
  from_location?: string;
  from_location_name?: string;
  to_location?: string;
  to_location_name?: string;
  actor: string;
  actor_email: string;
  note_private?: string;
  occurred_at: string;
  created_at: string;
}

const API_BASE = '/api/v1';

function getCookie(name: string): string | null {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop()?.split(';').shift() || null;
  return null;
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Accept': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const csrfToken = getCookie('csrftoken');
  if (csrfToken && options.method && options.method !== 'GET') {
    headers['X-CSRFToken'] = csrfToken;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
    credentials: 'include',
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const errorMsg = data?.error?.message || data?.detail || 'Request failed';
    throw new Error(errorMsg);
  }

  return data as T;
}

export const api = {
  auth: {
    login: (credentials: { email: string; password: string }) =>
      request<{ message: string; user: User }>('/auth/login/', {
        method: 'POST',
        body: JSON.stringify(credentials),
      }),
    register: (payload: { email: string; password: string; display_name: string }) =>
      request<{ message: string; user: User }>('/auth/register/', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    logout: () => request<{ message: string }>('/auth/logout/', { method: 'POST' }),
    me: () => request<{ user: User }>('/auth/me/'),
  },

  locations: {
    list: async () => {
      const data = await request<Location[] | { results: Location[]; count: number }>('/locations/');
      if (Array.isArray(data)) return data;
      if (data && Array.isArray(data.results)) return data.results;
      return [];
    },
  },

  reports: {
    list: (params: Record<string, string> = {}) => {
      const search = new URLSearchParams(params).toString();
      return request<{ results: ItemReport[]; count: number } | ItemReport[]>(`/reports/${search ? `?${search}` : ''}`);
    },
    get: (id: string) => request<ItemReport>(`/reports/${id}/`),
    createLost: (payload: {
      title: string;
      category: string;
      public_description: string;
      last_seen_at?: string;
      last_seen_location?: string;
      private_description?: string;
      distinguishing_details?: Record<string, unknown>;
    }) =>
      request<ItemReport>('/reports/lost/', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    createFound: (payload: {
      title: string;
      category: string;
      public_description: string;
      found_at?: string;
      found_location?: string;
      current_holding_location?: string;
      private_description?: string;
      distinguishing_details?: Record<string, unknown>;
    }) =>
      request<ItemReport>('/reports/found/', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    withdraw: (id: string) =>
      request<{ message: string }>(`/reports/${id}/withdraw/`, { method: 'POST' }),
    flag: (id: string, reason: string, details?: string) =>
      request<{ message: string; flag_id: string }>(`/reports/${id}/flag/`, {
        method: 'POST',
        body: JSON.stringify({ reason, details: details || '' }),
      }),
    uploadImage: (id: string, file: File) => {
      const formData = new FormData();
      formData.append('image', file);
      return request<{ id: string; url: string; content_type: string; size_bytes: number }>(`/reports/${id}/images/`, {
        method: 'POST',
        body: formData,
      });
    },
  },

  matching: {
    getMatches: (reportId: string) =>
      request<MatchResponse>(`/reports/${reportId}/matches/`),
    sendFeedback: (reportId: string, candidateReportId: string, feedback: string) =>
      request<{ message: string }>(`/reports/${reportId}/feedback/`, {
        method: 'POST',
        body: JSON.stringify({ candidate_report_id: candidateReportId, feedback }),
      }),
  },

  claims: {
    create: (reportId: string, statement: string) =>
      request<Claim>(`/reports/${reportId}/claims/`, {
        method: 'POST',
        body: JSON.stringify({ claimant_statement: statement }),
      }),
    myClaims: () => request<Claim[]>('/claims/mine/'),
    staffClaims: () => request<Claim[]>('/claims/staff/'),
    get: (claimId: string) => request<Claim>(`/claims/${claimId}/`),
    addEvidence: (claimId: string, evidenceType: string, privateValue: string) =>
      request<ClaimEvidence>(`/claims/${claimId}/evidence/`, {
        method: 'POST',
        body: JSON.stringify({ evidence_type: evidenceType, private_value: privateValue }),
      }),
    decide: (claimId: string, decision: 'approve' | 'reject', note: string) =>
      request<Claim>(`/claims/${claimId}/${decision}/`, {
        method: 'POST',
        body: JSON.stringify({ note }),
      }),
    completeHandover: (claimId: string) =>
      request<{ message: string }>(`/claims/${claimId}/complete-handover/`, { method: 'POST' }),
  },

  custody: {
    getHistory: (reportId: string) =>
      request<CustodyEvent[]>(`/reports/${reportId}/custody/`),
    pendingTransfers: () =>
      request<CustodyEvent[]>('/custody/transfers/pending/'),
    requestTransfer: (reportId: string, toLocationId: string, note?: string) =>
      request<CustodyEvent>(`/reports/${reportId}/custody/transfers/`, {
        method: 'POST',
        body: JSON.stringify({ to_location_id: toLocationId, note_private: note }),
      }),
    acceptTransfer: (custodyId: string, note?: string) =>
      request<CustodyEvent>(`/custody/transfers/${custodyId}/accept/`, {
        method: 'POST',
        body: JSON.stringify({ note_private: note }),
      }),
  },

  admin: {
    overview: () => request<AdminOverview>('/admin/overview/'),
    auditEvents: (params?: { action?: string; search?: string }) => {
      const qs = params ? new URLSearchParams(params as Record<string, string>).toString() : '';
      return request<PaginatedResponse<AuditEventItem> | AuditEventItem[]>(`/admin/audit-events/${qs ? `?${qs}` : ''}`);
    },
    reports: (params?: { visibility?: string; report_type?: string; search?: string; flagged?: string }) => {
      const qs = params ? new URLSearchParams(params as Record<string, string>).toString() : '';
      return request<PaginatedResponse<AdminReportItem> | AdminReportItem[]>(`/admin/reports/${qs ? `?${qs}` : ''}`);
    },
    moderateReport: (id: string, visibility: 'ACTIVE' | 'HIDDEN' | 'REMOVED', reason?: string) =>
      request<{ message: string; report: AdminReportItem }>(`/admin/reports/${id}/moderate/`, {
        method: 'POST',
        body: JSON.stringify({ visibility, reason }),
      }),
    users: (params?: { search?: string; is_active?: string }) => {
      const qs = params ? new URLSearchParams(params as Record<string, string>).toString() : '';
      return request<PaginatedResponse<AdminUserItem> | AdminUserItem[]>(`/admin/users/${qs ? `?${qs}` : ''}`);
    },
    suspendUser: (id: string, is_active: boolean, reason?: string) =>
      request<{ message: string; user: AdminUserItem }>(`/admin/users/${id}/suspend/`, {
        method: 'POST',
        body: JSON.stringify({ is_active, reason }),
      }),
  },

  health: {
    ready: () => request<{ status: string; checks: Record<string, string> }>('/health/ready/'),
  },
};
