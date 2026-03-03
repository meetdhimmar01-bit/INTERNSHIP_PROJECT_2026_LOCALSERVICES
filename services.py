import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'localservices.settings')
django.setup()

from django.core.files import File
from services.models import Service, Category

# Base artifact directory for mockups
artifact_dir = r"C:\Users\dhimm\.gemini\antigravity\brain\a9f7d620-5966-4b71-aeef-28087a944749"

# We will assign category-level default images for these new 3 services per category
category_images = {
    'Plumbing': 'service_plumbing_1772573670548.png',
    'Electrical': 'service_electrical_1772573684054.png',
    'Cleaning': 'service_cleaning_1772573697333.png',
    'Carpentry': 'service_carpentry_1772573723422.png',
    'Appliance Repair': 'service_appliance_1772573736760.png',
    'Painting': 'service_painting_1772573754481.png',
}

# Add alias for just "Repair" matching "Appliance Repair" if there are any
category_images['Repair'] = category_images['Appliance Repair']

new_services = {
    'Plumbing': [
        {'name': 'Water Heater Installation', 'price': '899.00', 'desc': 'Complete installation and setup of new water heating units.'},
        {'name': 'Toilet Repair & Setup', 'price': '599.00', 'desc': 'Fixing leaks, flushes, or installing entirely new toilet bowls.'},
        {'name': 'Drain Clog Clearing', 'price': '449.00', 'desc': 'Professional clearing of severe blockages in kitchen or bathroom drains.'}
    ],
    'Electrical': [
        {'name': 'Inverter Installation', 'price': '649.00', 'desc': 'Setting up home inverters and connecting them to the main power grid.'},
        {'name': 'Chandelier Hanging', 'price': '1299.00', 'desc': 'Safe and precise installation of heavy, delicate ceiling light fixtures.'},
        {'name': 'MCB Panel Replacement', 'price': '1499.00', 'desc': 'Replacing entire main circuit breaker panels for safety.'}
    ],
    'Cleaning': [
        {'name': 'Post-Construction Cleanup', 'price': '4999.00', 'desc': 'Heavy-duty cleaning to remove dust, debris, and marks after renovation.'},
        {'name': 'Bathroom Deep Scrub', 'price': '599.00', 'desc': 'Intensive chemical scrub of tiles, grout, and all bathroom fixtures.'},
        {'name': 'Water Tank Cleaning', 'price': '899.00', 'desc': 'Draining, scrubbing, and sanitizing overhead or underground water tanks.'}
    ],
    'Carpentry': [
        {'name': 'Modular Kitchen Assembly', 'price': '3599.00', 'desc': 'Assembling and mounting pre-fabricated modular kitchen cabinets.'},
        {'name': 'Lock Replacement', 'price': '299.00', 'desc': 'Replacing old door locks with new mortise or cylinder locks.'},
        {'name': 'Bed Frame Repair', 'price': '799.00', 'desc': 'Fixing creaky, broken, or misaligned wooden bed frames.'}
    ],
    'Appliance Repair': [
        {'name': 'Microwave Oven Repair', 'price': '399.00', 'desc': 'Fixing heating issues, turntable problems, or control panels in microwaves.'},
        {'name': 'Water Purifier Service', 'price': '499.00', 'desc': 'Changing RO filters and servicing the water purifier system.'},
        {'name': 'Geyser Repair', 'price': '449.00', 'desc': 'Fixing thermostats, heating coils, or leaks in electric geysers.'}
    ],
    'Painting': [
        {'name': 'Wood Polishing', 'price': '1299.00', 'desc': 'Sanding and applying premium PU polish to wooden furniture and doors.'},
        {'name': 'Waterproofing Treatment', 'price': '3999.00', 'desc': 'Applying advanced waterproofing chemicals to roofs and external walls.'},
        {'name': 'Metal Grill Painting', 'price': '899.00', 'desc': 'Applying anti-rust primer and enamel paint to window grills and gates.'}
    ]
}

def seed_new_services():
    for cat_name, services_list in new_services.items():
        try:
            category = Category.objects.get(name=cat_name)
        except Category.DoesNotExist:
            print(f"Error: Category '{cat_name}' not found.")
            continue
            
        for svc_data in services_list:
            # Check if this service already exists to prevent duplicate runs
            if Service.objects.filter(name=svc_data['name']).exists():
                print(f"Service '{svc_data['name']}' already exists. Skipping.")
                continue
                
            new_service = Service.objects.create(
                category=category,
                name=svc_data['name'],
                description=svc_data['desc'],
                base_price=Decimal(svc_data['price']),
                is_active=True
            )
            
            # Attach the default category image to this new service
            img_name = category_images.get(cat_name)
            if img_name:
                src_path = os.path.join(artifact_dir, img_name)
                if os.path.exists(src_path):
                    with open(src_path, 'rb') as f:
                        new_service.image.save(f"{new_service.id}_{img_name}", File(f), save=True)
            
            print(f"Successfully added '{svc_data['name']}' to {cat_name}.")

if __name__ == '__main__':
    seed_new_services()
