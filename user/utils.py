import requests
from .models import Portal, PortalUserMapping
from .serializers import PortalUserMappingSerializer

def map_user_to_portals(user_id, username):
    """
    Maps a given user across all portals by checking the username.
    Returns serialized mapping results.
    """
    results = []
    portals = Portal.objects.all()

    for portal in portals:
        try:
            url = f"{portal.base_url}/api/check-username/"
            r = requests.get(url, params={"username": username}, timeout=60)

            if r.status_code == 200 and r.json().get("status"):
                user_data = r.json().get("data", {})
                mapping, created = PortalUserMapping.objects.update_or_create(
                    user_id=user_id,
                    portal=portal,
                    defaults={
                        "portal_user_id": user_data.get("id"),
                        "status": "MATCHED",
                    },
                )
            else:
                mapping, created = PortalUserMapping.objects.update_or_create(
                    user_id=user_id,
                    portal=portal,
                    defaults={
                        "portal_user_id": None,
                        "status": "PENDING",
                    },
                )
        except Exception as e:
            mapping, created = PortalUserMapping.objects.update_or_create(
                user_id=user_id,
                portal=portal,
                defaults={
                    "portal_user_id": None,
                    "status": "PENDING",
                },
            )
            # Add error info only to result, not DB
            serializer = PortalUserMappingSerializer(mapping)
            results.append({**serializer.data, "error": str(e)})
            continue

        serializer = PortalUserMappingSerializer(mapping)
        results.append(serializer.data)

    return results