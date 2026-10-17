import type { components } from './api';

export * from './client';
export type { paths, components } from './api';

export type RolesConfig = components['schemas']['RolesConfig'];
export type Thresholds = components['schemas']['Thresholds'];
export type DiagnosticsReport = components['schemas']['DiagnosticsReport'];
export type HealthResponse = components['schemas']['HealthResponse'];
export type Access = 'full' | 'view' | 'none';
