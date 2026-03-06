"""
images.py  –  Apply service images to the database.

Contains two mappings:
  1. image_map  → by service NAME  (older entries, artifact dir from session a9f7d620)
  2. id_map     → by service ID    (newer specific images, artifact dir from session 920d8f64)

Run with:
    python images.py
"""

import os
import django
from django.core.files import File

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'localservices.settings')
django.setup()

from services.models import Service

# ── Artifact directories ──────────────────────────────────────────────────────
ARTIFACT_OLD = r"C:\Users\dhimm\.gemini\antigravity\brain\a9f7d620-5966-4b71-aeef-28087a944749"
ARTIFACT_NEW = r"C:\Users\dhimm\.gemini\antigravity\brain\920d8f64-512a-4595-b46a-af4afa3c3517"

MEDIA_DIR = r"d:\PROJECT\INTERNSHIP_PROJECT_2026_LOCALSERVICES\localservices\media\services"
os.makedirs(MEDIA_DIR, exist_ok=True)


# ── Mapping 1: by Service NAME (uses ARTIFACT_OLD) ───────────────────────────
image_map = {
    # Plumbing
    'Pipe Leak Repair':         'service_pipe_leak_1772575526788.png',
    'Tap / Faucet Installation':'service_faucet_install_1772575541497.png',
    'Bathroom Fitting':         'service_bathroom_fitting_1772575565195.png',

    # Electrical
    'Wiring & Rewiring':        'service_wiring_1772575581039.png',
    'Switchboard Repair':       'service_switchboard_1772575595790.png',
    'Fan / Light Installation': 'service_fan_install_1772575612555.png',

    # Cleaning
    'Full Home Deep Cleaning':  'service_deep_clean_1772576082463.png',
    'Sofa / Carpet Cleaning':   'service_sofa_clean_1772576100138.png',
    'Kitchen Deep Clean':       'service_kitchen_clean_1772576135607.png',

    # Carpentry (fallback to category image)
    'Furniture Assembly':        'service_carpentry_1772573723422.png',
    'Door / Window Repair':      'service_carpentry_1772573723422.png',
    'Custom Shelf Installation': 'service_carpentry_1772573723422.png',

    # Appliance (fallback to category image)
    'AC Service & Repair':       'service_appliance_1772573736760.png',
    'Washing Machine Repair':    'service_appliance_1772573736760.png',
    'Refrigerator Repair':       'service_appliance_1772573736760.png',

    # Painting (fallback to category image)
    'Room Interior Painting':    'service_painting_1772573754481.png',
    'Exterior Wall Painting':    'service_painting_1772573754481.png',
    'Wall Texture / Design':     'service_painting_1772573754481.png',
}


# ── Mapping 2: by Service ID (uses ARTIFACT_NEW — specific images) ────────────
id_map = {
    # Cleaning
    7:  'clean_home_cleaning_1772649274901.png',
    8:  'clean_sofa_carpet_1772649295275.png',
    9:  'clean_kitchen_deep_1772649311467.png',
    25: 'clean_post_construction_1772649326759.png',
    26: 'clean_bathroom_scrub_1772649350342.png',
    27: 'clean_water_tank_1772649370794.png',

    # Carpentry
    10: 'carpentry_furniture_assembly_1772649395704.png',
    11: 'carpentry_door_repair_1772649412062.png',
    12: 'carpentry_shelf_install_1772649427016.png',
    28: 'carpentry_kitchen_assembly_1772649442739.png',
    29: 'carpentry_lock_install_1772649462496.png',
    30: 'carpentry_bed_repair_1772649481140.png',

    # Appliance Repair
    13: 'appliance_ac_repair_1772649508894.png',
    14: 'appliance_washing_machine_1772649524463.png',
    15: 'appliance_refrigerator_1772649538956.png',
    31: 'appliance_microwave_1772649553901.png',
    32: 'appliance_water_purifier_1772649571533.png',
}


def apply_by_name():
    """Apply images to services matched by name (uses older artifact directory)."""
    print("\n-- Applying images by SERVICE NAME --")
    for svc in Service.objects.all():
        img_name = image_map.get(svc.name)
        if not img_name:
            print(f"  [SKIP]  No mapping: {svc.name}")
            continue
        src = os.path.join(ARTIFACT_OLD, img_name)
        if os.path.exists(src):
            with open(src, 'rb') as f:
                svc.image.save(f"{svc.id}_{img_name}", File(f), save=True)
            print(f"  [OK]    {svc.name} <- {img_name}")
        else:
            print(f"  [MISS]  File not found: {src}")


def apply_by_id():
    """Apply images to services matched by ID (uses newer artifact directory)."""
    print("\n-- Applying images by SERVICE ID --")
    for s_id, img_name in id_map.items():
        src = os.path.join(ARTIFACT_NEW, img_name)
        try:
            svc = Service.objects.get(id=s_id)
        except Service.DoesNotExist:
            print(f"  [MISS]  Service ID {s_id} not found.")
            continue
        if os.path.exists(src):
            with open(src, 'rb') as f:
                svc.image.save(f"{s_id}_{img_name}", File(f), save=True)
            print(f"  [OK]    ID={s_id} {svc.name} <- {img_name}")
        else:
            print(f"  [MISS]  File not found: {src}")


def check_missing_images():
    """Check and print any services that are still missing an image."""
    print("\n-- Checking for missing images --")
    services = Service.objects.all()
    missing = [s.name for s in services if not s.image]
    print(f"Total services: {services.count()}")
    print(f"Total missing: {len(missing)}")
    if missing:
        for idx, name in enumerate(missing, 1):
            print(f"  {idx}. {name}")
    else:
        print("  All services have an image assigned!")

if __name__ == '__main__':
    apply_by_name()
    apply_by_id()
    check_missing_images()
    print("\nDone!")
