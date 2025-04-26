import os
from app import create_app
from config import config

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    env = os.environ.get("APP_ENV", "development")
    app = create_app(config[env])
    app.run(debug=app.config.get("DEBUG", False), host='0.0.0.0', port=port, use_reloader=False)