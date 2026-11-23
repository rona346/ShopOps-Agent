"""
Firebase Admin SDK initialization foundation for ShopOps Agent.
Provides lazy-loaded, safe client initialization using configuration settings.
"""

from pathlib import Path
from typing import Optional
import firebase_admin
from firebase_admin import credentials, firestore
from app.core.config import settings

_firebase_app: Optional[firebase_admin.App] = None


def is_firebase_configured() -> bool:
    """Check whether Firebase credentials or project ID are provided in configuration."""
    cred_path = (settings.FIREBASE_CREDENTIALS_PATH or "").strip()
    project_id = (settings.FIREBASE_PROJECT_ID or "").strip()

    if cred_path and cred_path not in ("", "path/to/serviceAccountKey.json", "serviceAccountKey.json"):
        return True
    if project_id and project_id not in ("", "your_firebase_project_id"):
        return True
    return False


def get_firebase_app() -> firebase_admin.App:
    """
    Safely initialize and retrieve the Firebase Admin App instance (singleton).
    Raises RuntimeError with a clear message if credentials are not configured.
    """
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    # Reuse existing default app if already initialized in runtime
    if firebase_admin._apps:
        _firebase_app = firebase_admin.get_app()
        return _firebase_app

    cred_path_str = (settings.FIREBASE_CREDENTIALS_PATH or "").strip()
    project_id_str = (settings.FIREBASE_PROJECT_ID or "").strip()

    # Case 1: Service Account Key JSON provided
    if cred_path_str and cred_path_str not in ("", "path/to/serviceAccountKey.json", "serviceAccountKey.json"):
        cert_path = Path(cred_path_str)
        if not cert_path.is_absolute():
            backend_dir = Path(__file__).resolve().parent.parent.parent
            cert_path = (backend_dir / cert_path).resolve()

        if not cert_path.is_file():
            raise FileNotFoundError(
                f"Firebase service account file not found at: {cert_path}. "
                "Please verify FIREBASE_CREDENTIALS_PATH in backend/.env."
            )

        cred = credentials.Certificate(str(cert_path))
        options = {"projectId": project_id_str} if project_id_str else None
        _firebase_app = firebase_admin.initialize_app(cred, options=options)
        return _firebase_app

    # Case 2: Project ID provided (Application Default Credentials / Cloud environment)
    if project_id_str and project_id_str not in ("", "your_firebase_project_id"):
        _firebase_app = firebase_admin.initialize_app(options={"projectId": project_id_str})
        return _firebase_app

    raise RuntimeError(
        "Firebase is not configured. Please set FIREBASE_CREDENTIALS_PATH or "
        "FIREBASE_PROJECT_ID in backend/.env before accessing Firebase services."
    )


def get_firestore_client() -> firestore.Client:
    """
    Retrieve Firestore client instance.
    Raises RuntimeError if Firebase is not properly configured.
    """
    app = get_firebase_app()
    return firestore.client(app=app)
