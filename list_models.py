"""List available models/deployments in SAP AI Core."""
from dotenv import load_dotenv
from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client

load_dotenv()

def list_deployments():
    try:
        proxy_client = get_proxy_client("gen-ai-hub")
        
        # Try to list deployments
        print("Fetching available deployments from SAP AI Core...")
        print("-" * 50)
        
        # The proxy client may have methods to list deployments
        if hasattr(proxy_client, 'deployments'):
            deployments = proxy_client.deployments
            for d in deployments:
                print(f"Model: {d}")
        elif hasattr(proxy_client, 'get_deployments'):
            deployments = proxy_client.get_deployments()
            for d in deployments:
                print(f"Model: {d}")
        else:
            # Try listing attributes
            print("Proxy client attributes:")
            for attr in dir(proxy_client):
                if not attr.startswith('_'):
                    print(f"  - {attr}")
                    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_deployments()
