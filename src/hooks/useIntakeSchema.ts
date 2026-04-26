/**
 * Fetches and caches tenant-specific intake schema from backend.
 * Uses React Query + Axios with JWT authorization header.
 */

import axios from "axios";
import { useQuery } from "@tanstack/react-query";

import type { FormSchemaResponse } from "../types/intake";

interface UseIntakeSchemaArgs {
  tenantId: string;
  token: string;
}

export function useIntakeSchema({ tenantId, token }: UseIntakeSchemaArgs) {
  return useQuery<FormSchemaResponse>({
    queryKey: ["intake-schema", tenantId],
    enabled: Boolean(tenantId && token),
    staleTime: 5 * 60 * 1000,
    queryFn: async () => {
      const response = await axios.get<FormSchemaResponse>("/api/v1/intake/schema", {
        params: { tenant_id: tenantId },
        headers: { Authorization: `Bearer ${token}` },
      });
      return response.data;
    },
  });
}
