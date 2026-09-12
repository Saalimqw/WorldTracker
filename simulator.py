"""
AntiGravity — OSINT Simulation Engine (simulator.py)
Generates highly realistic mock data for advanced intelligence layers
(Nuclear, Military, Cyber, Ships, Aviation, etc.) since free live APIs do not exist for these.
"""

import sqlite3
import time
import random
import uuid
import logging
from datetime import datetime, timezone, timedelta

# Import the fallback summary generator so we get good AI descriptions
from scraper import fallback_summary, insert_event, init_db, event_exists

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("AntiGravity.Simulator")

DB_PATH = "worldmonitor.db"

# ─── Bounding Boxes & Hotspots ────────────────────────────────────────────────
# Helps generate coordinates that make geographical sense
HOTSPOTS = {
    "MIDDLE_EAST": {"lat": (12.0, 35.0), "lng": (35.0, 60.0)},
    "UKRAINE_RUSSIA": {"lat": (45.0, 52.0), "lng": (30.0, 40.0)},
    "SOUTH_CHINA_SEA": {"lat": (5.0, 22.0), "lng": (105.0, 120.0)},
    "RED_SEA": {"lat": (12.0, 28.0), "lng": (33.0, 43.0)},
    "TAIWAN_STRAIT": {"lat": (22.0, 26.0), "lng": (118.0, 122.0)},
    "EUROPE": {"lat": (40.0, 60.0), "lng": (-10.0, 30.0)},
    "NORTH_AMERICA": {"lat": (30.0, 50.0), "lng": (-125.0, -70.0)},
    "AFRICA_SAHEL": {"lat": (10.0, 20.0), "lng": (-15.0, 30.0)},
    "GLOBAL_OCEAN": {"lat": (-50.0, 50.0), "lng": (-180.0, 180.0)}, # rough approx
}

def random_coord(region: str = "GLOBAL") -> tuple[float, float]:
    if region == "GLOBAL":
        return random.uniform(-60, 70), random.uniform(-180, 180)
    box = HOTSPOTS.get(region, {"lat": (-60, 70), "lng": (-180, 180)})
    return random.uniform(*box["lat"]), random.uniform(*box["lng"])

# ─── Event Generators ─────────────────────────────────────────────────────────

def generate_conflict() -> dict:
    region = random.choice(["MIDDLE_EAST", "UKRAINE_RUSSIA", "AFRICA_SAHEL", "RED_SEA"])
    lat, lng = random_coord(region)
    factions = [("State Military", "Rebel Insurgents"), ("Coalition Forces", "Paramilitary Group"), ("Naval Patrol", "Pirate Skiffs")]
    f1, f2 = random.choice(factions)
    titles = [
        f"Heavy Artillery Exchange Between {f1} and {f2} in Contested Zone",
        f"Unmanned Aerial Drone Strike Neutralizes High-Value Target",
        f"Escalating Armed Clashes Involving Mechanized Infantry Units",
        f"Asymmetric Naval Skirmish Reported Near Critical Chokepoint",
        f"Widespread Air Raid Sirens Active Across Northern Defensive Sector"
    ]
    title = random.choice(titles)
    
    summaries = [
        f"TACTICAL UPDATE: Geolocated footage confirms significant kinetic activity involving {f1}. Initial battle damage assessments suggest multiple casualties and infrastructure degradation. Hostile forces are utilizing electronic warfare to jam local communications. Situation remains highly fluid.",
        f"INTELLIGENCE BRIEF: Elevated risk profile in the sector following unexpected mobilization by {f2}. Satellite surveillance reveals forward deployment of artillery assets. Allied commands have issued a shelter-in-place directive for civilian populations within a 50km radius.",
        f"FLASH REPORT: Imminent threat warning issued after {f1} engaged hostile elements. Thermal imaging detects secondary explosions, likely indicating an ammunition depot strike. Regional stability indices have dropped by 14% in the last 6 hours."
    ]
    
    return {
        "title": title,
        "layer": random.choice(["CONFLICT_ZONES", "ARMED_CONFLICT"]),
        "source": "OSINT-TACTICAL",
        "latitude": lat, "longitude": lng,
        "magnitude": random.uniform(5.0, 8.5),
        "ai_summary": random.choice(summaries)
    }

def generate_military() -> dict:
    region = random.choice(["SOUTH_CHINA_SEA", "TAIWAN_STRAIT", "EUROPE", "MIDDLE_EAST", "NORTH_AMERICA"])
    lat, lng = random_coord(region)
    titles = [
        "Unscheduled Naval Exercise Involving Carrier Strike Group",
        "QRA Fighter Squadron Scrambled to Intercept Unknown Aircraft",
        "Massive Troop and Armor Massing Observed via Low-Earth Orbit Satellite",
        "Strategic Nuclear Bomber Flight Path Deviation Detected",
        "Covert Military Transport Convoy Movement Near Border"
    ]
    
    summaries = [
        "STRATEGIC ALERT: OSINT analysts have detected anomalous troop movements consistent with rapid deployment doctrine. Signals intelligence (SIGINT) intercepts suggest a localized communications blackout is imminent. Advising heightened posture for regional assets.",
        "AEROSPACE WARNING: Air traffic control radars tracked unauthorized airspace incursions. Quick Reaction Alert (QRA) interceptors achieved visual contact but targets dispersed. This represents a 40% increase in probing flights over the past month.",
        "NAVAL POSTURE: A coalition carrier strike group has unexpectedly altered course, imposing a de-facto exclusion zone. Open-source AIS tracking data shows commercial vessels actively rerouting to avoid the operational theater. Escalation probability is marked at ELEVATED."
    ]

    return {
        "title": random.choice(titles),
        "layer": random.choice(["MILITARY_ACTIVITY", "INTEL_HOTSPOTS", "MILITARY_BASES"]),
        "source": "DEF-MONITOR-PRO",
        "latitude": lat, "longitude": lng,
        "magnitude": random.uniform(4.0, 7.5),
        "ai_summary": random.choice(summaries)
    }

def generate_nuclear() -> dict:
    lat, lng = random_coord(random.choice(["EUROPE", "NORTH_AMERICA", "MIDDLE_EAST"]))
    titles = [
        "Elevated Gamma Radiation Isotope Signatures Detected",
        "Uranium Enrichment Centrifuge Activity Spike Confirmed",
        "Unscheduled Emergency Shutdown of Nuclear Reactor Core",
        "Anomalous Readings from Civilian Radiological Sensors",
        "High-Risk Transport of Orphan Gamma Irradiator Detected"
    ]
    summaries = [
        "CBRN ALERT: Localized radiological sensors indicate a sustained spike in gamma background levels exceeding normal operational parameters by 300%. The IAEA has been notified. Probability of a minor containment breach is currently under investigation.",
        "NUCLEAR WATCH: Synthetic Aperture Radar (SAR) imagery reveals heavy transport vehicles departing the enrichment facility under cover of darkness. This pattern strongly correlates with clandestine material transfer protocols. Risk assessment is CRITICAL.",
        "INFRASTRUCTURE CRITICAL: Grid telemetry shows a sudden 4GW drop correlating with an emergency SCRAM of the primary reactor. Thermal signatures indicate secondary venting is active. Public health risk is currently assessed as LOW, but monitoring continues."
    ]
    return {
        "title": random.choice(titles),
        "layer": random.choice(["NUCLEAR_SITES", "RADIATION_WATCH", "GAMMA_IRRADIATORS"]),
        "source": "IAEA-SIM-NET",
        "latitude": lat, "longitude": lng,
        "magnitude": random.uniform(6.0, 9.9),
        "ai_summary": random.choice(summaries)
    }

def generate_cyber() -> dict:
    lat, lng = random_coord("GLOBAL")
    titles = [
        "Massive BGP Route Hijacking Attempt Targeting Core Routers",
        "State-Sponsored DDoS Botnet Crippling Financial Sector API",
        "Undersea Fiber-Optic Cable Severed; Data Throttling Active",
        "Widespread GPS Spoofing and GNSS Jamming Radius Expanding",
        "Advanced Persistent Threat (APT) Zero-Day Intrusion Detected"
    ]
    summaries = [
        "CYBERCOM BRIEF: Deep packet inspection algorithms have isolated a highly sophisticated malware payload propagating through critical industrial control systems (ICS). Attribution algorithms point to a state-aligned APT group. Mitigation protocols initiated.",
        "NETWORK OUTAGE: Global internet topology maps show a catastrophic loss of connectivity in the region, highly likely due to physical sabotage of submarine cable landing stations. Regional bandwidth is degraded by 78%.",
        "SIGINT ALERT: Open-source ADS-B aircraft data reveals widespread GPS spoofing anomalies, causing commercial flights to report false coordinates up to 150 nautical miles off-course. This EW (Electronic Warfare) bubble is expanding at 10km/hr."
    ]
    return {
        "title": random.choice(titles),
        "layer": random.choice(["CYBER_THREATS", "INTERNET_DISRUPTIONS", "UNDERSEA_CABLES", "GPS_JAMMING"]),
        "source": "CYBER-INTEL",
        "latitude": lat, "longitude": lng,
        "magnitude": random.uniform(5.0, 9.0),
        "ai_summary": random.choice(summaries)
    }

def generate_transit() -> dict:
    region = random.choice(["GLOBAL_OCEAN", "RED_SEA", "SOUTH_CHINA_SEA"])
    lat, lng = random_coord(region)
    titles = [
        "LNG Cargo Carrier Deviating from Designated Trade Route",
        "Commercial Aviation Transponder Lost in Restricted Airspace",
        "Naval Blockade Enforcing Stoppage at Strategic Chokepoint",
        "Unidentified Submersible Loitering Near Critical Infrastructure",
        "Commercial Flight Declares Emergency (Squawk 7700) Over Ocean"
    ]
    summaries = [
        "MARITIME THREAT: AIS tracking data indicates a clustering of 'dark fleet' vessels operating with spoofed transponders. Coast guard assets have been dispatched to intercept. The disruption is causing a 12% drop in daily tonnage through the chokepoint.",
        "AVIATION INCIDENT: Air traffic control lost secondary radar contact with a civilian airliner traversing a known conflict zone. Military radar tracks suggest a rapid descent profile. Search and rescue (SAR) grids are being formulated.",
        "LOGISTICS DISRUPTION: Supply chain analytics flag a critical delay in mineral transport vessels due to sudden naval exercises in the strait. Global commodity markets are pricing in a temporary shortage of rare earth elements."
    ]
    return {
        "title": random.choice(titles),
        "layer": random.choice(["SHIP_TRAFFIC", "AVIATION", "TRADE_ROUTES", "CHOKEPOINTS"]),
        "source": "TRANSIT-RADAR",
        "latitude": lat, "longitude": lng,
        "magnitude": random.uniform(3.0, 6.0),
        "ai_summary": random.choice(summaries)
    }

def generate_space() -> dict:
    lat, lng = random_coord("GLOBAL")
    titles = [
        "Reconnaissance Satellite Executing Evasive Orbital Maneuver",
        "Classified Spaceport Launch Preparations Detected via Thermal",
        "Kessler Syndrome Warning: Debris Field Intersecting LEO",
        "Global CII (Critical Infrastructure Instability) Index Spike",
        "Critical Minerals Supply Chain Disruption Identified"
    ]
    summaries = [
        "SPACE COMMAND: Orbital tracking networks have cataloged an unannounced maneuver by a military reconnaissance satellite, significantly altering its ground track to overfly highly sensitive test ranges. Counter-surveillance protocols activated.",
        "INFRASTRUCTURE WATCH: The AI-driven Critical Infrastructure Instability (CII) index has spiked above the 90th percentile for this region, correlating with anomalous energy grid fluctuations and compromised telecommunications nodes.",
        "ORBITAL HAZARD: A fragmentation event in Low Earth Orbit (LEO) has created a high-density debris cloud. Collision probability for commercial constellations has risen by 15%. Automated collision avoidance maneuvers are being executed."
    ]
    return {
        "title": random.choice(titles),
        "layer": random.choice(["SPACEPORTS", "ORBITAL_SURVEILLANCE", "CRITICAL_MINERALS", "CII_INSTABILITY"]),
        "source": "SAT-COM-PRO",
        "latitude": lat, "longitude": lng,
        "magnitude": random.uniform(3.0, 6.0),
        "ai_summary": random.choice(summaries)
    }

def generate_disaster() -> dict:
    lat, lng = random_coord("GLOBAL")
    titles = [
        "Category 5 Super Typhoon Undergoing Rapid Intensification",
        "Uncontrolled Megafire Spreading Towards Dense Urban Center",
        "Catastrophic Flooding Inundating Agricultural Heartlands",
        "Massive Volcanic Ash Plume Forcing Total Aviation Grounding",
        "Unprecedented Climate Anomaly Triggering Mass Displacement"
    ]
    summaries = [
        "CLIMATE EMERGENCY: Weather satellites report unprecedented intensification rates for this cyclonic system. Storm surge models predict catastrophic inundation of coastal infrastructure. Evacuation orders impact over 2 million residents. Disaster relief staging is heavily constrained.",
        "GEO-HAZARD: Multispectral satellite imaging reveals a rapidly expanding thermal anomaly. The megafire has breached primary containment lines. Air quality indices have exceeded hazardous thresholds up to 500km downwind. State of emergency declared.",
        "HUMANITARIAN CRISIS: Extreme precipitation events have overwhelmed localized dam infrastructure. NGOs report immediate displacement of 50,000+ individuals. The risk of waterborne disease vectors is categorized as SEVERE over the next 72 hours."
    ]
    return {
        "title": random.choice(titles),
        "layer": random.choice(["SEVERE_WEATHER", "FIRES", "NATURAL_EVENTS", "CLIMATE_ANOMALIES"]),
        "source": "GEO-SAT-INTEL",
        "latitude": lat, "longitude": lng,
        "magnitude": random.uniform(6.0, 9.5),
        "ai_summary": random.choice(summaries)
    }

GENERATORS = [
    generate_conflict, generate_military, generate_nuclear, 
    generate_cyber, generate_transit, generate_space, generate_disaster
]

# ─── Simulation Loop ──────────────────────────────────────────────────────────

def run_simulation(conn: sqlite3.Connection, batch_size: int = 15):
    """Generate a batch of mock events across various intelligence layers."""
    new_events = []
    
    for _ in range(batch_size):
        # Pick a random category generator
        generator = random.choice(GENERATORS)
        event = generator()
        
        event["event_id"] = f"SIM_{uuid.uuid4().hex[:12].upper()}"
        event["category"] = event["layer"]
        event["timestamp"] = datetime.now(tz=timezone.utc).isoformat()
        event["url"] = ""
        
        # If the generator provided a rich AI summary, keep it, otherwise fallback
        if "ai_summary" not in event:
            event["ai_summary"] = fallback_summary(event)
        
        insert_event(conn, event)
        new_events.append(event)
        
    log.info(f"Simulated {batch_size} new global OSINT events.")

if __name__ == "__main__":
    log.info("Starting AntiGravity OSINT Simulation Engine...")
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    
    # Do an initial large seed so the map looks populated immediately
    run_simulation(conn, batch_size=250)
    
    try:
        while True:
            time.sleep(15)  # Inject 3-5 new events every 15 seconds
            run_simulation(conn, batch_size=random.randint(3, 8))
    except KeyboardInterrupt:
        log.info("Simulator stopped.")
        conn.close()
