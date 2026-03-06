import os
import django
import sys
from django.core.files import File

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'localservices.settings')
django.setup()

from services.models import Service

ARTIFACT_DIR = r"C:\Users\dhimm\.gemini\antigravity\brain\221f8bef-8841-4bcf-8c73-216c3080ed1e"

img_map = {
    'Waterproofing Treatment': 'waterproofing_treatment_1772823194924.png',
    'Inverter Installation': 'inverter_installation_1772823209733.png',
    'Chandelier Hanging': 'chandelier_hanging_1772823227893.png',
    'Water Heater Installation': 'water_heater_install_1772823285256.png',
    'Toilet Repair & Setup': 'toilet_repair_1772823301115.png',
    'Drain Clog Clearing': 'drain_clog_clearing_1772823324123.png',
    'MCB Panel Replacement': 'mcb_panel_replacement_1772823339283.png',
    'Geyser Repair': 'geyser_repair_1772823357615.png',
    'Room Interior Painting': 'room_interior_painting_1772823379753.png',
    'Metal Grill Painting': 'metal_grill_painting_1772823395703.png',
    'Exterior Wall Painting': 'exterior_wall_painting_1772823418336.png',
    'Wall Texture / Design': 'wall_texture_design_1772823436196.png',
    'Wood Polishing': 'wood_polishing_1772823453751.png'
}

def apply_images():
    print("Applying generated images...")
    for svc_name, img_file in img_map.items():
        src_path = os.path.join(ARTIFACT_DIR, img_file)
        if not os.path.exists(src_path):
            print(f"MISSING FILE: {src_path}")
            continue
            
        try:
            # We don't filter safely by get() in case multiple exist, filter and take first
            services = Service.objects.filter(name=svc_name)
            if not services.exists():
                print(f"Service not found: {svc_name}")
                continue
                
            for svc in services:
                # If the image field isn't empty, it might still have a dead ref, let's overwrite it
                # Because earlier we saw the image names were present but files were missing!
                # Actually, earlier query was: missing = [s.name for s in Service.objects.all() if s.image and not os.path.exists(os.path.join(MEDIA_ROOT, s.image.name))]
                # So we KNOW these services have dead image references. We just overwrite it.
                with open(src_path, 'rb') as f:
                    svc.image.save(f"{svc.id}_{img_file}", File(f), save=True)
                print(f"SUCCESS: Updated '{svc.name}' with {img_file}")
        except Exception as e:
            print(f"ERROR on {svc_name}: {e}")

if __name__ == '__main__':
    apply_images()
