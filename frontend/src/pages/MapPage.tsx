import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import { mediaApi } from '@/services/api';
import { MapMarker, Media } from '@/types';
import { MapPinIcon } from '@heroicons/react/24/outline';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix for default marker icons in React-Leaflet
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

// Custom marker icon
const photoIcon = new L.Icon({
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

function MapBounds({ markers }: { markers: MapMarker[] }) {
  const map = useMap();
  
  useEffect(() => {
    if (markers.length > 0) {
      const bounds = L.latLngBounds(
        markers.map((m) => [m.latitude, m.longitude])
      );
      map.fitBounds(bounds, { padding: [50, 50] });
    }
  }, [markers, map]);
  
  return null;
}

export default function MapPage() {
  const [selectedMarker, setSelectedMarker] = useState<MapMarker | null>(null);
  
  // Fetch map data
  const { data: markers, isLoading } = useQuery<MapMarker[]>({
    queryKey: ['mapData'],
    queryFn: async () => {
      const response = await mediaApi.getMapData();
      return response.data;
    },
  });
  
  // Group markers by location (cluster nearby markers)
  const clusterMarkers = (markers: MapMarker[], threshold: number = 0.01) => {
    const clusters: { lat: number; lng: number; markers: MapMarker[] }[] = [];
    
    markers.forEach((marker) => {
      const existingCluster = clusters.find(
        (c) =>
          Math.abs(c.lat - marker.latitude) < threshold &&
          Math.abs(c.lng - marker.longitude) < threshold
      );
      
      if (existingCluster) {
        existingCluster.markers.push(marker);
      } else {
        clusters.push({
          lat: marker.latitude,
          lng: marker.longitude,
          markers: [marker],
        });
      }
    });
    
    return clusters;
  };
  
  const clusters = markers ? clusterMarkers(markers) : [];
  
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <MapPinIcon className="w-7 h-7" />
          Map
        </h1>
        <p className="text-dark-500 dark:text-dark-400">
          {markers?.length || 0} photos with location data
        </p>
      </div>
      
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      ) : markers && markers.length > 0 ? (
        <div className="card overflow-hidden" style={{ height: 'calc(100vh - 200px)' }}>
          <MapContainer
            center={[markers[0].latitude, markers[0].longitude]}
            zoom={10}
            style={{ height: '100%', width: '100%' }}
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            
            <MapBounds markers={markers} />
            
            {clusters.map((cluster, index) => (
              <Marker
                key={index}
                position={[cluster.lat, cluster.lng]}
                icon={photoIcon}
                eventHandlers={{
                  click: () => setSelectedMarker(cluster.markers[0]),
                }}
              >
                <Popup>
                  <div className="w-48">
                    {cluster.markers[0].thumbnail && (
                      <img
                        src={cluster.markers[0].thumbnail}
                        alt=""
                        className="w-full h-32 object-cover rounded mb-2"
                      />
                    )}
                    <p className="font-medium">
                      {cluster.markers.length} photo{cluster.markers.length !== 1 ? 's' : ''}
                    </p>
                    {cluster.markers[0].taken_at && (
                      <p className="text-sm text-dark-500">
                        {new Date(cluster.markers[0].taken_at).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                </Popup>
              </Marker>
            ))}
          </MapContainer>
        </div>
      ) : (
        <div className="text-center py-20">
          <MapPinIcon className="w-16 h-16 mx-auto text-dark-300 mb-4" />
          <h3 className="text-lg font-medium mb-2">No location data</h3>
          <p className="text-dark-500">
            Photos with GPS coordinates will appear on the map
          </p>
        </div>
      )}
    </div>
  );
}
