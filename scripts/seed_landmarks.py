"""
Seed script to populate the landmarks database with comprehensive Bonamoussadi references.
Creates a robust database of landmarks for enhanced location recognition.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_db_session
from app.models.database_models import Landmark
from loguru import logger

# Comprehensive Bonamoussadi landmarks database
BONAMOUSSADI_LANDMARKS = [
    # Major Markets and Commercial Centers
    {
        "name": "Marché Central Bonamoussadi",
        "landmark_type": "market",
        "area": "Bonamoussadi",
        "coordinates": "4.0616,-9.7031",
        "address": "Rue principale, Bonamoussadi, Douala",
        "aliases": ["Marché Central", "Grand Marché", "Marché Bona"],
        "common_references": ["près du marché", "au marché", "marché central", "grand marché"],
        "nearby_landmarks": ["Station Total", "Pharmacie du Marché", "École Publique"]
    },
    {
        "name": "Carrefour Bonamoussadi",
        "landmark_type": "commercial",
        "area": "Bonamoussadi",
        "coordinates": "4.0625,-9.7028",
        "address": "Carrefour principal, Bonamoussadi",
        "aliases": ["Carrefour Central", "Rond-point", "Carrefour Bona"],
        "common_references": ["au carrefour", "rond-point", "carrefour central"],
        "nearby_landmarks": ["Marché Central", "Pharmacie Moderne", "Banque Atlantique"]
    },
    
    # Healthcare Facilities
    {
        "name": "Hôpital de District Bonamoussadi",
        "landmark_type": "hospital",
        "area": "Bonamoussadi",
        "coordinates": "4.0608,-9.7045",
        "address": "Quartier Hôpital, Bonamoussadi",
        "aliases": ["Hôpital District", "Hôpital Bona", "CHD Bonamoussadi"],
        "common_references": ["à l'hôpital", "près de l'hôpital", "côté hôpital"],
        "nearby_landmarks": ["Pharmacie de l'Hôpital", "Centre de Santé", "École Technique"]
    },
    {
        "name": "Pharmacie Moderne Bonamoussadi",
        "landmark_type": "pharmacy",
        "area": "Bonamoussadi",
        "coordinates": "4.0622,-9.7035",
        "address": "Rue du Commerce, Bonamoussadi",
        "aliases": ["Pharmacie Moderne", "Pharmacie Centrale"],
        "common_references": ["près de la pharmacie", "pharmacie moderne", "derrière la pharmacie"],
        "nearby_landmarks": ["Carrefour Bonamoussadi", "Banque", "Supermarché Casino"]
    },
    {
        "name": "Centre de Santé Intégré",
        "landmark_type": "clinic",
        "area": "Bonamoussadi",
        "coordinates": "4.0595,-9.7052",
        "address": "Quartier CSI, Bonamoussadi",
        "aliases": ["CSI Bonamoussadi", "Centre de Santé", "Dispensaire"],
        "common_references": ["au CSI", "centre de santé", "dispensaire"],
        "nearby_landmarks": ["École Primaire", "Terrain de Football", "Église Catholique"]
    },
    
    # Educational Institutions
    {
        "name": "École Publique de Bonamoussadi",
        "landmark_type": "school",
        "area": "Bonamoussadi",
        "coordinates": "4.0612,-9.7025",
        "address": "Quartier École, Bonamoussadi",
        "aliases": ["École Primaire", "EP Bonamoussadi", "École Publique"],
        "common_references": ["à l'école", "près de l'école", "école primaire"],
        "nearby_landmarks": ["Marché Central", "Terrain de Sport", "Pharmacie"]
    },
    {
        "name": "Lycée Technique de Bonamoussadi",
        "landmark_type": "school",
        "area": "Bonamoussadi",
        "coordinates": "4.0598,-9.7038",
        "address": "Avenue de l'Éducation, Bonamoussadi",
        "aliases": ["Lycée Technique", "LYTEC Bona", "École Technique"],
        "common_references": ["au lycée", "école technique", "lycée technique"],
        "nearby_landmarks": ["Hôpital", "Stade Municipal", "Centre Jeunesse"]
    },
    {
        "name": "Collège Privé Saint-Michel",
        "landmark_type": "school",
        "area": "Bonamoussadi",
        "coordinates": "4.0635,-9.7015",
        "address": "Rue Saint-Michel, Bonamoussadi",
        "aliases": ["Collège Saint-Michel", "Saint-Michel", "École Saint-Michel"],
        "common_references": ["collège privé", "saint-michel", "école saint-michel"],
        "nearby_landmarks": ["Église Catholique", "Supermarché", "Banque UBC"]
    },
    
    # Religious Buildings
    {
        "name": "Église Catholique Saint-Pierre",
        "landmark_type": "church",
        "area": "Bonamoussadi",
        "coordinates": "4.0618,-9.7020",
        "address": "Paroisse Saint-Pierre, Bonamoussadi",
        "aliases": ["Église Saint-Pierre", "Paroisse Catholique", "Église Catholique"],
        "common_references": ["à l'église", "église catholique", "paroisse"],
        "nearby_landmarks": ["École", "Centre Commercial", "Poste de Police"]
    },
    {
        "name": "Mosquée Centrale de Bonamoussadi",
        "landmark_type": "mosque",
        "area": "Bonamoussadi",
        "coordinates": "4.0605,-9.7042",
        "address": "Quartier Mosquée, Bonamoussadi",
        "aliases": ["Mosquée Centrale", "Grande Mosquée", "Mosquée Bona"],
        "common_references": ["à la mosquée", "mosquée centrale", "grande mosquée"],
        "nearby_landmarks": ["Marché", "École Coranique", "Centre Islamique"]
    },
    
    # Banks and Financial Services
    {
        "name": "Banque Atlantique Bonamoussadi",
        "landmark_type": "bank",
        "area": "Bonamoussadi",
        "coordinates": "4.0628,-9.7030",
        "address": "Avenue Principale, Bonamoussadi",
        "aliases": ["BA Bonamoussadi", "Banque Atlantique", "Atlantique Bank"],
        "common_references": ["à la banque", "banque atlantique", "BA"],
        "nearby_landmarks": ["Carrefour", "Pharmacie", "Supermarché"]
    },
    {
        "name": "Express Union Bonamoussadi",
        "landmark_type": "bank",
        "area": "Bonamoussadi",
        "coordinates": "4.0615,-9.7032",
        "address": "Rue du Commerce, Bonamoussadi",
        "aliases": ["EU Bonamoussadi", "Express Union", "EU"],
        "common_references": ["express union", "EU", "transfert d'argent"],
        "nearby_landmarks": ["Marché", "Pharmacie", "Centre Commercial"]
    },
    
    # Gas Stations and Transportation
    {
        "name": "Station Total Bonamoussadi",
        "landmark_type": "gas_station",
        "area": "Bonamoussadi",
        "coordinates": "4.0620,-9.7038",
        "address": "Route Principale, Bonamoussadi",
        "aliases": ["Total Bona", "Station Total", "Essence Total"],
        "common_references": ["à la station", "station total", "total"],
        "nearby_landmarks": ["Marché Central", "Carrefour", "Supermarché"]
    },
    {
        "name": "Gare Routière Bonamoussadi",
        "landmark_type": "transport",
        "area": "Bonamoussadi",
        "coordinates": "4.0608,-9.7025",
        "address": "Place de la Gare, Bonamoussadi",
        "aliases": ["Gare Routière", "Gare Auto", "Station Taxi"],
        "common_references": ["à la gare", "gare routière", "station taxi"],
        "nearby_landmarks": ["Marché Central", "Pharmacie", "Poste de Police"]
    },
    {
        "name": "Arrêt Bus Principal",
        "landmark_type": "transport",
        "area": "Bonamoussadi",
        "coordinates": "4.0625,-9.7028",
        "address": "Avenue Principale, Bonamoussadi",
        "aliases": ["Arrêt Bus", "Station Bus", "Arrêt Principal"],
        "common_references": ["arrêt bus", "station bus", "arrêt principal"],
        "nearby_landmarks": ["Carrefour", "Banque", "Supermarché"]
    },
    
    # Supermarkets and Shops
    {
        "name": "Supermarché Casino Bonamoussadi",
        "landmark_type": "supermarket",
        "area": "Bonamoussadi",
        "coordinates": "4.0632,-9.7025",
        "address": "Centre Commercial, Bonamoussadi",
        "aliases": ["Casino Bona", "Supermarché Casino", "Casino"],
        "common_references": ["au casino", "supermarché casino", "casino"],
        "nearby_landmarks": ["Banque", "Pharmacie", "École"]
    },
    {
        "name": "Centre Commercial Bonamoussadi",
        "landmark_type": "commercial",
        "area": "Bonamoussadi",
        "coordinates": "4.0630,-9.7022",
        "address": "Place Commerciale, Bonamoussadi",
        "aliases": ["Centre Commercial", "Galerie Marchande", "Mall Bona"],
        "common_references": ["centre commercial", "galerie", "mall"],
        "nearby_landmarks": ["Supermarché", "Banque", "Pharmacie"]
    },
    
    # Sports and Recreation
    {
        "name": "Stade Municipal Bonamoussadi",
        "landmark_type": "sports",
        "area": "Bonamoussadi",
        "coordinates": "4.0590,-9.7035",
        "address": "Complexe Sportif, Bonamoussadi",
        "aliases": ["Stade Municipal", "Terrain de Football", "Stade Bona"],
        "common_references": ["au stade", "terrain de foot", "stade municipal"],
        "nearby_landmarks": ["Lycée Technique", "Centre de Santé", "Quartier Résidentiel"]
    },
    {
        "name": "Centre de Jeunesse",
        "landmark_type": "community",
        "area": "Bonamoussadi",
        "coordinates": "4.0602,-9.7040",
        "address": "Avenue de la Jeunesse, Bonamoussadi",
        "aliases": ["Maison des Jeunes", "Centre Jeunesse", "Foyer des Jeunes"],
        "common_references": ["centre jeunesse", "maison des jeunes", "foyer"],
        "nearby_landmarks": ["Stade", "École", "Hôpital"]
    },
    
    # Government and Public Services
    {
        "name": "Mairie d'Arrondissement Bonamoussadi",
        "landmark_type": "government",
        "area": "Bonamoussadi",
        "coordinates": "4.0615,-9.7018",
        "address": "Place de la Mairie, Bonamoussadi",
        "aliases": ["Mairie Bona", "Conseil Municipal", "Hôtel de Ville"],
        "common_references": ["à la mairie", "mairie", "conseil municipal"],
        "nearby_landmarks": ["Poste de Police", "École", "Banque"]
    },
    {
        "name": "Poste de Police Bonamoussadi",
        "landmark_type": "police",
        "area": "Bonamoussadi",
        "coordinates": "4.0612,-9.7015",
        "address": "Commissariat, Bonamoussadi",
        "aliases": ["Commissariat", "Police Bona", "Poste Police"],
        "common_references": ["au commissariat", "poste de police", "police"],
        "nearby_landmarks": ["Mairie", "École", "Église"]
    },
    
    # Residential Areas and Quarters
    {
        "name": "Quartier Résidentiel Nord",
        "landmark_type": "residential",
        "area": "Bonamoussadi",
        "coordinates": "4.0640,-9.7010",
        "address": "Zone Résidentielle Nord, Bonamoussadi",
        "aliases": ["Quartier Nord", "Zone Résidentielle", "Bona Nord"],
        "common_references": ["quartier résidentiel", "zone nord", "côté nord"],
        "nearby_landmarks": ["École Privée", "Supermarché", "Pharmacie"]
    },
    {
        "name": "Quartier Populaire Sud",
        "landmark_type": "residential",
        "area": "Bonamoussadi",
        "coordinates": "4.0585,-9.7048",
        "address": "Zone Populaire Sud, Bonamoussadi",
        "aliases": ["Quartier Sud", "Bona Sud", "Zone Populaire"],
        "common_references": ["quartier populaire", "zone sud", "côté sud"],
        "nearby_landmarks": ["Stade", "Centre de Santé", "Mosquée"]
    }
]

def seed_landmarks():
    """Seed the database with comprehensive Bonamoussadi landmarks"""
    
    db = get_db_session()
    
    try:
        logger.info("Starting landmark seeding for Bonamoussadi...")
        
        # Check if landmarks already exist
        existing_count = db.query(Landmark).filter(Landmark.area == "Bonamoussadi").count()
        if existing_count > 0:
            logger.info(f"Found {existing_count} existing landmarks. Skipping seeding.")
            return
        
        # Add all landmarks
        for landmark_data in BONAMOUSSADI_LANDMARKS:
            landmark = Landmark(
                name=landmark_data["name"],
                landmark_type=landmark_data["landmark_type"],
                area=landmark_data["area"],
                coordinates=landmark_data.get("coordinates"),
                address=landmark_data.get("address"),
                aliases=landmark_data.get("aliases", []),
                common_references=landmark_data.get("common_references", []),
                nearby_landmarks=landmark_data.get("nearby_landmarks", []),
                is_active=True,
                verification_status="verified"
            )
            
            db.add(landmark)
        
        db.commit()
        
        # Count inserted landmarks
        final_count = db.query(Landmark).filter(Landmark.area == "Bonamoussadi").count()
        logger.info(f"Successfully seeded {final_count} landmarks for Bonamoussadi")
        
        # Log landmark types distribution
        from sqlalchemy import func
        types_count = db.query(
            Landmark.landmark_type, 
            func.count(Landmark.id)
        ).filter(
            Landmark.area == "Bonamoussadi"
        ).group_by(
            Landmark.landmark_type
        ).all()
        
        logger.info("Landmark types distribution:")
        for landmark_type, count in types_count:
            logger.info(f"  {landmark_type}: {count}")
        
    except Exception as e:
        logger.error(f"Error seeding landmarks: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_landmarks()