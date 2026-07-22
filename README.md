# Vietnam PM2.5 Multi-Horizon Forecast

Production deployment source for the FastAPI + React application that forecasts
PM2.5 at every horizon from `t+1` through `t+24` for Ha Noi, Ho Chi Minh City,
and Da Nang.

## Render deployment

The repository includes a Render Blueprint in `render.yaml`. The service uses
`web_2/Dockerfile`, builds the Vite frontend, packages the trained XGBoost
multi-horizon artifact, and starts FastAPI with Uvicorn.

Health endpoint: `GET /api/health`.

## Local Docker

```bash
docker build -f web_2/Dockerfile -t aqi-vietnam-multihorizon .
docker run --rm -p 8000:8000 aqi-vietnam-multihorizon
```
