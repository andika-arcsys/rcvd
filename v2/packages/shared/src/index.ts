import type { components } from './api';

export * from './client';
export type { paths, components } from './api';

export type RolesConfig = components['schemas']['RolesConfig'];
export type Thresholds = components['schemas']['Thresholds'];
export type DiagnosticsReport = components['schemas']['DiagnosticsReport'];
export type HealthResponse = components['schemas']['HealthResponse'];
export type Access = 'full' | 'view' | 'none';

export {
  area,
  calibrate,
  calibrationStatus,
  criticalLimit,
  freezePair,
  heronCrossCheck,
  length,
  MeasureError,
  rodTest,
  span,
  spanWarning,
  tapeCheck,
  undistortPoint,
} from './measure';
export type {
  AreaResult,
  Calibration,
  Camera,
  FreezeResult,
  LengthResult,
  MeasureLimits,
  Point,
  RodResult,
  SegmentIn,
  SegmentMeasure,
  SpanResult,
  TapeResult,
} from './measure';
