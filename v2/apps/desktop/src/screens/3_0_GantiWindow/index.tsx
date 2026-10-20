import { Navigate, useSearchParams } from 'react-router-dom';

export default function GantiWindowScreen() {
  const [params] = useSearchParams();
  const fitur = params.get('fitur');
  const to = fitur ? `/live?fitur=${encodeURIComponent(fitur)}` : '/live';
  return <Navigate to={to} replace />;
}
