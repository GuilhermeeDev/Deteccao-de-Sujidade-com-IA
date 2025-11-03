from fastapi.middleware.cors import CORSMiddleware # pyright: ignore[reportMissingImports]

def setup_cors(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
