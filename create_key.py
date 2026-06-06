# create_key.py
import sys
from auth import generer_api_key

def main():
    # Vérification des arguments en ligne de commande
    if len(sys.argv) < 2:
        print("❌ Usage: python create_key.py <nom_du_client> [scopes]")
        print("   Exemple: python create_key.py \"Application Mobile\" read")
        print("   Exemple: python create_key.py \"Dashboard Admin\" read,write")
        sys.exit(1)
    
    client_name = sys.argv[1]
    # Si des scopes sont fournis, on les sépare par la virgule, sinon on met "read" par défaut
    scopes = sys.argv[2].split(",") if len(sys.argv) > 2 else ["read"]
    
    print(f"\n⏳ Génération de la clé pour : {client_name} (scopes: {', '.join(scopes)})...")
    
    try:
        # Appel de la fonction que nous avons créée dans auth.py
        resultat = generer_api_key(client_name, scopes)
        
        print("\n" + "="*70)
        print("✅ NOUVELLE CLÉ API GÉNÉRÉE AVEC SUCCÈS")
        print("="*70)
        print(f"Client      : {resultat['client_name']}")
        print(f"Permissions : {', '.join(resultat['scopes'])}")
        print(f"Clé secrète : {resultat['api_key']}")
        print("="*70)
        print("⚠️  CONSERVEZ CETTE CLÉ PRÉCIEUSEMENT")
        print("Elle ne pourra JAMAIS être affichée à nouveau par le système.")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERREUR lors de la génération : {e}")
        print("Vérifiez que votre base de données MongoDB est bien en ligne.")
        sys.exit(1)

if __name__ == "__main__":
    main()