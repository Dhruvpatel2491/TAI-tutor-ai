import os
import sys
import types


def _inject_stubs():
    """Inject lightweight stubs for modules that backend.server imports at import-time
    so tests can import the Flask app without heavy external dependencies.
    """
    # minimal stub for llama_index.llms.ollama
    mod_ollama = types.ModuleType("llama_index.llms.ollama")

    class Ollama:
        def __init__(self, *args, **kwargs):
            pass

    mod_ollama.Ollama = Ollama
    sys.modules["llama_index.llms.ollama"] = mod_ollama

    # minimal stub for llama_index.embeddings.ollama
    mod_embed = types.ModuleType("llama_index.embeddings.ollama")

    class OllamaEmbedding:
        def __init__(self, *args, **kwargs):
            pass

    mod_embed.OllamaEmbedding = OllamaEmbedding
    sys.modules["llama_index.embeddings.ollama"] = mod_embed

    # minimal stub for llama_index.core.settings
    mod_settings = types.ModuleType("llama_index.core.settings")

    class Settings:
        embed_model = None
        llm = None

    mod_settings.Settings = Settings
    sys.modules["llama_index.core.settings"] = mod_settings

    # minimal stub for llm_methods.get_or_create_index
    mod_llm_methods = types.ModuleType("llm_methods")

    def get_or_create_index(index_dir=None, data_dir=None, force_rebuild=False, indexing=None):
        class IndexObj:
            def as_query_engine(self, **kwargs):
                class QE:
                    def query(self, q):
                        return "dummy-response"

                return QE()

        return IndexObj(), IndexObj().as_query_engine()

    mod_llm_methods.get_or_create_index = get_or_create_index
    sys.modules["llm_methods"] = mod_llm_methods

    # stub flask_cors.CORS
    mod_cors = types.ModuleType("flask_cors")
    def CORS(app):
        return None
    mod_cors.CORS = CORS
    sys.modules["flask_cors"] = mod_cors


def test_register_login_and_plans_endpoints(tmp_path, monkeypatch):
    # ensure deterministic secret for tests
    os.environ["BACKEND_JWT_SECRET"] = "tests-secret"
    # Inject stubs before importing the server (prevents heavy imports)
    _inject_stubs()

    # Ensure project root is on sys.path for imports
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

    # Now import the Flask app
    from backend import auth
    from backend import server

    app = server.app
    client = app.test_client()

    # Register a user (dev flow issues token)
    rv = client.post("/auth/register", json={"user_id": "alice"})
    assert rv.status_code == 200
    token = rv.get_json().get("token")
    assert token

    headers = {"Authorization": f"Bearer {token}"}

    # Create a plan as alice
    rv2 = client.post("/plans", json={"topics": ["math", "py"] , "notes": "start"}, headers=headers)
    assert rv2.status_code == 201
    plan = rv2.get_json()
    assert plan.get("user_id") == "alice"
    plan_id = plan.get("id")

    # Listing plans for alice
    rv3 = client.get("/plans", headers=headers)
    assert rv3.status_code == 200
    assert any(p.get("id") == plan_id for p in rv3.get_json())

    # Fetch single plan
    rv4 = client.get(f"/plans/{plan_id}", headers=headers)
    assert rv4.status_code == 200

    # Token for other user should be forbidden to access alice's plan
    bob_token = auth.create_jwt_for_user("bob", exp_seconds=60)
    rv5 = client.get(f"/plans/{plan_id}", headers={"Authorization": f"Bearer {bob_token}"})
    assert rv5.status_code == 403
