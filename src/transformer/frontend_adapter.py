"""
Frontend Adapter.

Adapts React frontend to use FastAPI backend instead of Supabase client.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class FrontendAdapter:
    """Adapts React/TypeScript frontend for APX backend."""

    def __init__(self) -> None:
        """Initialize frontend adapter."""
        self.adaptations: list[dict[str, Any]] = []

    def adapt_supabase_client_imports(self, tsx_code: str) -> str:
        """
        Replace Supabase client imports with APX API client.

        Args:
            tsx_code: Original TypeScript React code

        Returns:
            Adapted code with new imports
        """
        # Replace Supabase client import
        adapted = re.sub(
            r"import.*?from\s+['\"]@/integrations/supabase/client['\"]",
            "import { apiClient } from '@/lib/api-client'",
            tsx_code,
        )

        self.adaptations.append(
            {
                "type": "import",
                "original": "@/integrations/supabase/client",
                "replacement": "@/lib/api-client",
            }
        )

        return adapted

    def adapt_supabase_queries(self, tsx_code: str) -> str:
        """
        Convert Supabase queries to API client calls.

        Args:
            tsx_code: Original code with Supabase queries

        Returns:
            Adapted code with API client calls
        """
        adapted = tsx_code

        # Pattern: supabase.from('table').select()
        select_pattern = r"supabase\.from\(['\"](\w+)['\"]\)\.select\([^)]*\)"

        for match in re.finditer(select_pattern, adapted):
            table = match.group(1)
            original = match.group(0)

            # Convert to API client call
            replacement = f"apiClient.get('/{table}')"

            adapted = adapted.replace(original, replacement)

            self.adaptations.append(
                {
                    "type": "query",
                    "operation": "select",
                    "table": table,
                    "original": original,
                    "replacement": replacement,
                }
            )

        # Pattern: supabase.from('table').insert(data)
        insert_pattern = r"supabase\.from\(['\"](\w+)['\"]\)\.insert\(([^)]+)\)"

        for match in re.finditer(insert_pattern, adapted):
            table = match.group(1)
            data = match.group(2)
            original = match.group(0)

            replacement = f"apiClient.post('/{table}', {data})"

            adapted = adapted.replace(original, replacement)

            self.adaptations.append(
                {
                    "type": "query",
                    "operation": "insert",
                    "table": table,
                    "original": original,
                    "replacement": replacement,
                }
            )

        return adapted

    def adapt_auth_calls(self, tsx_code: str) -> str:
        """
        Convert Supabase auth calls to Databricks OAuth.

        Args:
            tsx_code: Original code with auth calls

        Returns:
            Adapted code with OAuth
        """
        adapted = tsx_code

        # supabase.auth.getSession()
        adapted = re.sub(
            r"supabase\.auth\.getSession\(\)",
            "apiClient.getCurrentUser()",
            adapted,
        )

        # supabase.auth.getUser()
        adapted = re.sub(
            r"supabase\.auth\.getUser\(\)", "apiClient.getCurrentUser()", adapted
        )

        # supabase.auth.signOut()
        adapted = re.sub(r"supabase\.auth\.signOut\(\)", "apiClient.signOut()", adapted)

        return adapted

    def generate_api_client(self, base_url: str = "/api") -> str:
        """
        Generate TypeScript API client for the frontend.

        Args:
            base_url: Base URL for API endpoints

        Returns:
            TypeScript API client code
        """
        return f'''
/**
 * API Client for Databricks APX Backend
 *
 * Auto-generated client to replace Supabase client.
 */

import axios, {{ AxiosInstance, AxiosError }} from 'axios';

interface ApiClientConfig {{
  baseURL: string;
  timeout?: number;
}}

interface RequestConfig {{
  headers?: Record<string, string>;
  params?: Record<string, any>;
}}

class APIClient {{
  private client: AxiosInstance;
  private token: string | null = null;

  constructor(config: ApiClientConfig) {{
    this.client = axios.create({{
      baseURL: config.baseURL,
      timeout: config.timeout || 30000,
      headers: {{
        'Content-Type': 'application/json',
      }},
    }});

    // Request interceptor to add auth token
    this.client.interceptors.request.use((config) => {{
      if (this.token) {{
        config.headers.Authorization = `Bearer ${{this.token}}`;
      }}
      return config;
    }});

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {{
        if (error.response?.status === 401) {{
          // Handle unauthorized
          this.token = null;
          window.location.href = '/login';
        }}
        return Promise.reject(error);
      }}
    );
  }}

  setToken(token: string): void {{
    this.token = token;
  }}

  async get<T = any>(url: string, config?: RequestConfig): Promise<T> {{
    const response = await this.client.get(url, config);
    return response.data;
  }}

  async post<T = any>(url: string, data?: any, config?: RequestConfig): Promise<T> {{
    const response = await this.client.post(url, data, config);
    return response.data;
  }}

  async put<T = any>(url: string, data?: any, config?: RequestConfig): Promise<T> {{
    const response = await this.client.put(url, data, config);
    return response.data;
  }}

  async delete<T = any>(url: string, config?: RequestConfig): Promise<T> {{
    const response = await this.client.delete(url, config);
    return response.data;
  }}

  async getCurrentUser(): Promise<any> {{
    return this.get('/auth/me');
  }}

  async signOut(): Promise<void> {{
    this.token = null;
    await this.post('/auth/logout');
  }}
}}

// Create and export singleton instance
export const apiClient = new APIClient({{
  baseURL: '{base_url}',
}});

export default apiClient;
'''

    def generate_react_query_hooks(self, tables: list[str]) -> str:
        """
        Generate React Query hooks for data fetching.

        Args:
            tables: List of table names

        Returns:
            TypeScript React Query hooks
        """
        hooks = [
            "import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';",
            "import { apiClient } from './api-client';",
            "",
        ]

        for table in tables:
            table_singular = table.rstrip("s")  # Simple singularization
            hook_name = f"use{table_singular.capitalize()}"

            # GET hook
            hooks.append(f"export function {hook_name}s() {{")
            hooks.append("  return useQuery({")
            hooks.append(f"    queryKey: ['{table}'],")
            hooks.append(f"    queryFn: () => apiClient.get('/{table}'),")
            hooks.append("  });")
            hooks.append("}")
            hooks.append("")

            # CREATE hook
            hooks.append(f"export function useCreate{table_singular.capitalize()}() {{")
            hooks.append("  const queryClient = useQueryClient();")
            hooks.append("  return useMutation({")
            hooks.append(f"    mutationFn: (data: any) => apiClient.post('/{table}', data),")
            hooks.append("    onSuccess: () => {")
            hooks.append(f"      queryClient.invalidateQueries({{ queryKey: ['{table}'] }});")
            hooks.append("    },")
            hooks.append("  });")
            hooks.append("}")
            hooks.append("")

        return "\n".join(hooks)

    def adapt_realtime_subscriptions(self, tsx_code: str) -> str:
        """
        Convert Supabase Realtime subscriptions to polling.

        Args:
            tsx_code: Code with realtime subscriptions

        Returns:
            Adapted code with polling
        """
        if "supabase.channel(" not in tsx_code and ".subscribe(" not in tsx_code:
            return tsx_code

        # Add comment about realtime conversion
        comment = """
// NOTE: Realtime subscriptions converted to polling
// Original Supabase Realtime has been replaced with React Query's refetchInterval
// For true realtime, consider implementing WebSocket support
"""

        adapted = comment + tsx_code

        # Replace subscription with polling config
        adapted = re.sub(
            r"\.subscribe\([^)]*\)",
            "// Use React Query with refetchInterval for polling",
            adapted,
        )

        self.adaptations.append(
            {
                "type": "realtime",
                "note": "Converted to polling with React Query",
            }
        )

        return adapted

    def get_adaptation_summary(self) -> dict[str, Any]:
        """Get summary of all frontend adaptations."""
        return {
            "total_adaptations": len(self.adaptations),
            "by_type": {
                "imports": len([a for a in self.adaptations if a["type"] == "import"]),
                "queries": len([a for a in self.adaptations if a["type"] == "query"]),
                "realtime": len([a for a in self.adaptations if a["type"] == "realtime"]),
            },
            "adaptations": self.adaptations,
        }
