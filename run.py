import os
from app_factory import create_app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=port,
            use_reloader=False)