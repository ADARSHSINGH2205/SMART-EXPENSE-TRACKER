# Deploying PayArc

PayArc's recommended deployment is one Docker service: the compiled React UI
and FastAPI API share one origin, and the SQLite database lives on a persistent
volume. This is simpler and safer than exposing a separate API URL for a
private-finance application.

## Run with Docker

1. Install Docker Desktop and start it.
2. From the project root, copy `.env.example` to `.env` if you want to change
   the default port.
3. Start the application:

   ```powershell
   docker compose up --build -d
   ```

4. Open `http://localhost:8080`. The API health check is at
   `http://localhost:8080/api/health` and interactive API docs are at
   `http://localhost:8080/docs`.

The named `payarc-data` volume preserves finance data across container rebuilds
and restarts. Do not run `docker compose down --volumes` unless you deliberately
want to erase that local database.

## Update the application

```powershell
docker compose up --build -d
```

This rebuilds the React assets and API image while retaining the `payarc-data`
volume. Check service state with `docker compose ps` and logs with
`docker compose logs -f payarc`.

## Deploy on Render

`render.yaml` defines a single Docker web service. Push this repository to a
Git provider, create a new Render Blueprint from it, and verify that the
`payarc-data` persistent disk is attached at `/data`. The service uses Render's
provided `PORT` automatically.

SQLite is appropriate for a personal or small single-instance deployment. For
multiple application instances, replace `PAYARC_DATABASE_URL` with a managed
PostgreSQL URL and run a database migration before scaling out.

## External frontend/API deployments

The default `VITE_API_URL=/api` is intentional. If the React frontend is hosted
separately, set `VITE_API_URL` to the public API base URL **at build time** and
add that frontend origin to the FastAPI CORS policy before deploying. Keeping
the bundled same-origin service avoids this extra privacy and security surface.
