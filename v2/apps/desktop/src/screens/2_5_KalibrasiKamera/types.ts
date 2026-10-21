export interface CalibrationOut {
  code: number;
  message: string;
  photos: number;
  readable: number;
  rms: number | null;
  band: string | null;
  camera_matrix: number[] | null;
  dist_coeffs: number[] | null;
  image_width: number | null;
  image_height: number | null;
  written: boolean;
}

export interface MarkerOut {
  marker_id: number;
  x_mm: number;
  y_mm: number;
  z_mm: number;
  distance_mm: number;
}

export interface ArucoOut {
  camera_id: string;
  marker_mm: number;
  dictionary: string;
  markers: MarkerOut[];
  message: string;
  preview_jpeg: string | null;
}

export const BOARD_URL = 'https://visionbrick.com/camera-calibration-with-opencv/';
export const ARUCO_URL =
  'https://visionbrick.com/measuring-depth-from-a-single-camera-using-aruco-markers-in-opencv/';
export const VIDEO_URL = 'https://www.youtube.com/watch?v=TaNCWCANeAo';
