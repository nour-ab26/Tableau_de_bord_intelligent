import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = os.getenv("DB_PORT")

def get_db_connection():
    """Établit et retourne une connexion à la base de données PostgreSQL."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        print("Connexion à la base de données établie avec succès.")
        return conn
    except psycopg2.OperationalError as e:
        print(f"Erreur de connexion à la base de données: {e}") 
        raise 

if __name__ == "__main__":
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM equipments;")
            count = cursor.fetchone()[0]
            print(f"Nombre d'équipements dans la base : {count}")
            cursor.close()
        except Exception as e:
            print(f"Erreur lors du test de requête : {e}")
        finally:
            conn.close()
            print("Connexion fermée.")