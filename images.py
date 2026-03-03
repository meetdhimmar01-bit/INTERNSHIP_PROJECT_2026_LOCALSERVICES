import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'localservices.settings')
django.setup()

from django.core.files import File
from services.models import Service, Category

artifact_dir = r"C:\Users\dhimm\.gemini\antigravity\brain\a9f7d620-5966-4b71-aeef-28087a944749"
media_dir = r"d:\PROJECT\INTERNSHIP_PROJECT_2026_LOCALSERVICES\localservices\media\services"

os.makedirs(media_dir, exist_ok=True)

image_map = {
    # Plumbing Services
    'Pipe Leak Repair': 'service_pipe_leak_1772575526788.png',
    'Tap / Faucet Installation': 'service_faucet_install_1772575541497.png',
    'Bathroom Fitting': 'service_bathroom_fitting_1772575565195.png',
    
    # Electrical Services
    'Wiring & Rewiring': 'service_wiring_1772575581039.png',
    'Switchboard Repair': 'service_switchboard_1772575595790.png',
    'Fan / Light Installation': 'service_fan_install_1772575612555.png',
    
    # Cleaning Services
    'Full Home Deep Cleaning': 'service_deep_clean_1772576082463.png',
    'Sofa / Carpet Cleaning': 'service_sofa_clean_1772576100138.png',
    'Kitchen Deep Clean': 'service_kitchen_clean_1772576135607.png',
    
    # Fallback to category base for the remaining ones for now
    'Furniture Assembly': 'service_carpentry_1772573723422.png',
    'Door / Window Repair': 'service_carpentry_1772573723422.png',
    'Custom Shelf Installation': 'service_carpentry_1772573723422.png',
    
    'AC Service & Repair': 'service_appliance_1772573736760.png',
    'Washing Machine Repair': 'service_appliance_1772573736760.png',
    'Refrigerator Repair': 'service_appliance_1772573736760.png',
    
    'Room Interior Painting': 'service_painting_1772573754481.png',
    'Exterior Wall Painting': 'service_painting_1772573754481.png',
    'Wall Texture / Design': 'service_painting_1772573754481.png',
}

services = Service.objects.all()
for svc in services:
    img_name = image_map.get(svc.name)
    if img_name:
        src_path = os.path.join(artifact_dir, img_name)
        if os.path.exists(src_path):
            with open(src_path, 'rb') as f:
                svc.image.save(f"{svc.id}_{img_name}", File(f), save=True)
                print(f"Saved {img_name} to Service: {svc.name}")
        else:
            print(f"File not found: {src_path}")
    else:
        print(f"No image mapped for service: {svc.name}")
