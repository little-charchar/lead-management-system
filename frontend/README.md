# Lexwell frontend

## Development

From `frontend/`, install dependencies and start the Next.js application:

```bash
npm install
cp .env.example .env.local
npm run dev
```

The app runs at `http://localhost:3000` and calls the FastAPI API at
`http://localhost:8000/api` by default. Change `NEXT_PUBLIC_API_URL` in
`.env.local` if the API is hosted elsewhere. Demo personas are selected in the
sticky identity bar; API calls attach the selected `X-Demo-User-Email` header.

Run `npm run typecheck` and `npm run build` to validate the application.

## API-supported case access

The current API does not provide a case-list endpoint or a way to resolve a
case from an accepted lead. Firm and plaintiff portals therefore open matters
by case reference. The firm portal displays the case reference immediately
after a lead is accepted. Admin case oversight likewise requires a known case
reference. The portals do not invent case-list data or expose private notes to
plaintiffs.
