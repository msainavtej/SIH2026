import cv2
import numpy as np

class Zone:
    def __init__(self, zone_id, zone_type, polygon, border_direction=None):
        self.zone_id = zone_id
        self.zone_type = zone_type
        # polygon is a list of [x, y] coordinates
        self.polygon = np.array(polygon, np.int32).reshape((-1, 1, 2))
        self.border_direction = border_direction

    def contains_point(self, point):
        """
        Check if a given point (x, y) is inside the zone polygon.
        Returns 1 if inside, -1 if outside, 0 if on edge.
        """
        # point2PolygonTest returns positive distance if inside
        result = cv2.pointPolygonTest(self.polygon, (float(point[0]), float(point[1])), measureDist=False)
        return result >= 0

class ZoneManager:
    def __init__(self):
        self.zones = {}
        
    def add_zone(self, zone_dict):
        """
        Adds a zone from a dictionary (e.g., loaded from yaml).
        """
        z = Zone(
            zone_id=zone_dict['id'],
            zone_type=zone_dict.get('type', 'normal'),
            polygon=zone_dict['polygon'],
            border_direction=zone_dict.get('border_direction')
        )
        self.zones[z.zone_id] = z
        
    def load_from_yaml(self, filepath):
        import yaml
        import os
        if not os.path.exists(filepath):
            return
        with open(filepath, "r") as f:
            config = yaml.safe_load(f)
        for zone_dict in config.get("zones", []):
            self.add_zone(zone_dict)
        
    def check_point_in_zones(self, point):
        """
        Returns a list of zone IDs that contain the given point.
        """
        active_zones = []
        for z_id, zone in self.zones.items():
            if zone.contains_point(point):
                active_zones.append(z_id)
        return active_zones
