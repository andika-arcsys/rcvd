/** Tipe data modul ukur. Ambang datang dari pemanggil, bukan dari angka di fungsi. */

export type Point = readonly [number, number];

export type Camera = {
  fx: number;
  fy: number;
  cx: number;
  cy: number;
  dist: readonly [number, number, number, number, number];
};

export type MeasureLimits = {
  uncertainty_k: number;
  valid_max_rel: number;
  estimate_max_rel: number;
  camera_file_required_for_valid: boolean;
  rod_length_m: number;
  rod_tolerance_pct: number;
  freeze_max_delta_cm: number;
  rope_tolerance_pct: number;
  warning_ratio: number;
  critical_inch_16: number;
  critical_inch_8: number;
  heron_rel_tol: number;
  boundary_tol: number;
  undistort_iterations: number;
  resurvey_months: number;
  min_baseline_px: number;
};

export type Calibration = {
  scale_m_per_px: number;
  rel_uncert: number;
  sigma_scale_rel: number;
  status: string;
  click_sigma_px: number;
  uncertainty_k: number;
  camera: Camera | null;
  nodes: readonly [Point, Point];
  baseline_hint: string | null;
};

export type LengthResult = { meters: number; uncertainty_2sigma_m: number };

export type AreaResult = {
  area_m2: number;
  uncertainty_2sigma_m2: number;
  sides_m: readonly number[];
  diagonals_m: readonly number[];
  heron_m2: number | null;
};

export type RodResult = { passed: boolean; error_pct: number };
export type FreezeResult = { passed: boolean; delta_m: number };
export type TapeResult = { passed: boolean; error_pct: number };

export type SegmentIn = { id: string; pairs: readonly (readonly [number, number])[] };

export type SegmentMeasure = { id: string; a_m: number; b_m: number; length_m: number };

export type SpanResult = {
  length_left_m: number;
  length_right_m: number;
  length_total_m: number;
  segments: readonly SegmentMeasure[];
  recommendation: string;
  recommendation_message: string;
  warning: boolean;
  critical_limit_m: number;
  cut_segment_id: string;
  cut_offset_m: number;
};
