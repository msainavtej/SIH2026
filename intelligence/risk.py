import yaml
import os

class RiskEngine:
    def __init__(self, config_path="configs/rules.yaml"):
        """
        Initializes the risk engine with configurable weights from yaml.
        """
        self.weights = {
            'restricted_zone': 40,
            'border_approach': 30,
            'night_movement': 20,
            'loitering': 15,
            'unauthorized_vehicle': 25
        }
        self.thresholds = {
            'dwell_intrusion_seconds': 2,
            'loitering_seconds': 30,
            'event_grace_period_seconds': 5
        }
        
        self.watchlist = {}
        
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                conf = yaml.safe_load(f)
                if conf:
                    if 'risk_weights' in conf:
                        self.weights.update(conf['risk_weights'])
                    if 'thresholds' in conf:
                        self.thresholds.update(conf['thresholds'])

        anpr_config_path = "configs/anpr.yaml"
        if os.path.exists(anpr_config_path):
            with open(anpr_config_path, "r") as f:
                anpr_conf = yaml.safe_load(f)
                if anpr_conf and 'watchlist' in anpr_conf:
                    for entry in anpr_conf['watchlist']:
                        self.watchlist[entry['plate']] = entry

    def evaluate(self, event_type, context):
        """
        Evaluates risk based on event type and context.
        Returns (risk_score, risk_level, reasons, breakdown)
        """
        score = 0
        reasons = []
        breakdown = {}
        
        # Check Watchlist
        plate = context.get('plate')
        is_unknown_vehicle = False
        
        if plate:
            if plate == "UNKNOWN":
                is_unknown_vehicle = True
                reasons.append("Unknown Plate")
                breakdown['plate_risk'] = 10
                score += 10
            elif plate in self.watchlist:
                entry = self.watchlist[plate]
                r_mod = entry.get('risk_modifier', 0)
                score += r_mod
                breakdown['watchlist_risk'] = r_mod
                reasons.append(f"Watchlist: {entry.get('label')}")
            else:
                is_unknown_vehicle = True
                reasons.append(f"Plate {plate} not in watchlist")
                
        if event_type == 'VEHICLE_DETECTED':
            if is_unknown_vehicle:
                score += 10 # Slight bump for unknown vehicle
                breakdown['vehicle_risk'] = 10
                reasons.append("Unknown vehicle detected")
                
        if event_type == 'WILDLIFE_ACTIVITY':
            score = 10 # Base low score for wildlife
            breakdown['wildlife_risk'] = 10
            reasons.append("Wildlife activity detected")

        if event_type == 'ZONE_INTRUSION':
            score += self.weights['restricted_zone']
            breakdown['zone_risk'] = self.weights['restricted_zone']
            zone_name = context.get('zone', 'Unknown Zone')
            reasons.append(f"Virtual Boundary Intrusion ({zone_name})")
            
            if context.get('direction') in ['N', 'NE', 'NW']: # Assuming North is border
                score += self.weights['border_approach']
                breakdown['movement_risk'] = self.weights['border_approach']
                reasons.append("Moving toward border")

            if context.get('dwell_time', 0) > self.thresholds['loitering_seconds']:
                score += self.weights['loitering']
                breakdown['loitering_risk'] = self.weights['loitering']
                reasons.append(f"Loitering detected")
                
        elif event_type == 'NIGHT_MOVEMENT':
            score += self.weights['night_movement']
            breakdown['time_risk'] = self.weights['night_movement']
            reasons.append("Movement detected during night hours")
            
        if context.get('is_night', False) and 'time_risk' not in breakdown:
            score += self.weights['night_movement']
            breakdown['time_risk'] = self.weights['night_movement']
            reasons.append("Movement detected during night hours")

        # Normalize score and deduplicate reasons
        score = min(100, max(0, score))
        reasons = list(dict.fromkeys(reasons)) # Preserves order, deduplicates
        
        # Determine level
        if score < 30:
            level = "LOW"
        elif score < 60:
            level = "MEDIUM"
        elif score < 90:
            level = "HIGH"
        else:
            level = "CRITICAL"
            
        return score, level, reasons, breakdown
