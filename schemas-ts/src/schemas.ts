/*
Copyright (c) 2025, elk-MCP Project.
All rights reserved.
*/

import { z } from 'zod';

export const Pagination = z.object({
  page: z.number().int().min(1).max(100000),
  page_size: z.number().int().min(1).max(200),
});

export const TimeRange = z.object({
  start: z.string().min(1),
  end: z.string().min(1),
});

export const LogQueryFilters = z.object({
  level: z.array(z.string()).optional(),
  service: z.array(z.string()).optional(),
  keyword: z.string().optional(),
});

export const SortSpec = z.object({
  field: z.enum(['timestamp', '_score']).default('timestamp'),
  order: z.enum(['asc', 'desc']).default('desc'),
});

export const LogQueryRequest = z.object({
  tenant_id: z.string().min(1),
  pagination: Pagination,
  time_range: TimeRange,
  filters: LogQueryFilters.default({}),
  sort: SortSpec.default({ field: 'timestamp', order: 'desc' }),
  mode: z.enum(['page', 'cursor']).default('page'),
  cursor_after: z.array(z.union([z.string(), z.number()])).optional(),
});

export const AlertRuleRef = z.object({ id: z.string().min(1), severity: z.string().optional() });

export const AlertsQueryRequest = z.object({
  tenant_id: z.string().min(1),
  time_range: TimeRange,
  severity: z.array(z.enum(['low', 'medium', 'high'])).optional(),
  rules: z.array(AlertRuleRef).optional(),
});

export const StatsRequest = z.object({
  tenant_id: z.string().min(1),
  time_range: TimeRange,
  group_by: z.enum(['service', 'level', 'host']),
});

export type TLogQueryRequest = z.infer<typeof LogQueryRequest>;
export type TAlertsQueryRequest = z.infer<typeof AlertsQueryRequest>;
export type TStatsRequest = z.infer<typeof StatsRequest>;

