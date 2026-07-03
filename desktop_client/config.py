# desktop_client/config.py

IS_DEVELOPMENT = True
BASE_DEV_URL = "http://127.0.0.1:8000"
PRODUCTION_DOMAIN = "rvc-pos.com"  # e.g., your live domain name

def get_api_routing(tenant_subdomain, endpoint_path):
    """
    Dynamically builds the URL and appropriate routing headers 
    based on the execution environment.
    """
    endpoint = endpoint_path.lstrip('/')
    
    if IS_DEVELOPMENT:
        url = f"{BASE_DEV_URL}/{endpoint}"
        headers = {
            "Host": "localhost:8000" if tenant_subdomain == "public" else f"{tenant_subdomain}.localhost:8000",
            "Content-Type": "application/json"
        }
    else:
        # In production, hit the actual cloud subdomain straight over DNS
        if tenant_subdomain == "public":
            url = f"https://api.{PRODUCTION_DOMAIN}/{endpoint}"
        else:
            url = f"https://{tenant_subdomain}.{PRODUCTION_DOMAIN}/{endpoint}"
        headers = {
            "Content-Type": "application/json"
        }
        
    return url, headers