# FleetIQ frontend

React + Vite dashboard for the FleetIQ demand prediction & fleet allocation API.

## Setup

```bash
npm install
cp .env.example .env   # edit VITE_API_BASE_URL if the backend isn't on localhost:8000
npm run dev
```

Open http://localhost:5173. The backend (see ../backend) must be running for the
dashboard to load data.

## Build

```bash
npm run build   # outputs to dist/
npm run preview # serve the production build locally
```
