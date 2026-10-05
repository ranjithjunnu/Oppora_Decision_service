# Decision Lab frontend

Run `npm ci`, then `npm run dev` from this directory. Start the backend on port
8000 first; open http://127.0.0.1:5173. `npm run build` type-checks and bundles;
`npm run preview` serves the production build locally on port 4173.

See ../docs/MANUAL_EVALUATION.md for configuration, API contracts and limitations.
Secrets belong only in the backend .env. Optional proxy settings are documented
in .env.example. Session history is held only in memory.
