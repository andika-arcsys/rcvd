import type { ComponentType } from 'react';
import SplashScreen from './0_Splash';
import LoginScreen from './0_1_Login';
import PeranScreen from './0_2_Peran';
import DashboardScreen from './1_Dashboard';
import MisiScreen from './2_Misi';
import KalibrasiKameraScreen from './2_5_KalibrasiKamera';
import OpticalNativeViewScreen from './3_OpticalNativeView';
import GantiWindowScreen from './3_0_GantiWindow';
import AquaClearScreen from './3_1_AquaClear';
import HydroDetectScreen from './3_2_HydroDetect';
import SpatialSightScreen from './3_3_SpatialSight';
import PerformaScreen from './3_9_Performa';
import CanvasScreen from './3_4_Canvas';
import SnapshotScreen from './3_5_Snapshot';
import SimpanSnapshotScreen from './3_5_3_SimpanSnapshot';
import ReviewScreen from './4_Review';
import GalleryScreen from './5_Gallery';
import SpanScreen from './5_2_Span';
import LaporanScreen from './6_Laporan';
import PimsRbiScreen from './7_PimsRbi';
import AnalisisAiScreen from './8_AnalisisAi';
import SustainabilityScreen from './9_Sustainability';
import ArsipScreen from './10_Arsip';
import PengaturanScreen from './11_Pengaturan';
import PenutupanScreen from './12_Penutupan';

/** Peta kode layar -> komponen. Satu layar = satu folder. */
export const SCREEN_COMPONENTS: Record<string, ComponentType> = {
  '0': SplashScreen,
  '0.1': LoginScreen,
  '0.2': PeranScreen,
  '1': DashboardScreen,
  '2': MisiScreen,
  '2.5': KalibrasiKameraScreen,
  '3': OpticalNativeViewScreen,
  '3.0': GantiWindowScreen,
  '3.1': AquaClearScreen,
  '3.2': HydroDetectScreen,
  '3.3': SpatialSightScreen,
  '3.9': PerformaScreen,
  '3.4': CanvasScreen,
  '3.5': SnapshotScreen,
  '3.5.3': SimpanSnapshotScreen,
  '4': ReviewScreen,
  '5': GalleryScreen,
  '5.2': SpanScreen,
  '6': LaporanScreen,
  '7': PimsRbiScreen,
  '8': AnalisisAiScreen,
  '9': SustainabilityScreen,
  '10': ArsipScreen,
  '11': PengaturanScreen,
  '12': PenutupanScreen,
};
