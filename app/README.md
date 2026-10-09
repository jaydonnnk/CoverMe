# Cover app — Francesco

Next.js App Router, TypeScript, Tailwind and ESLint, generated with
`create-next-app@latest`. npm is the only package manager; commit changes to
`package.json` and `package-lock.json` together.

From this folder:

```sh
npm ci
cp .env.example .env.local
npm run dev
```

Open http://localhost:3000. `/`, `/ana` and `/maker` are static scaffold pages,
not the F5 product screens. The runtime has no external font downloads.

```sh
npm run lint
npm run typecheck
npm run build
```

The outer `app/` is the Next.js project; its inner `app/` holds App Router routes.
Use `@/` for files within this project. Keep wallet code reserved for Jaydon in
`lib/wallet.ts`; use the shared definitions in `../shared/` and deployments in
`../deployments/` rather than duplicating them.

Future browser calls to the service use `NEXT_PUBLIC_SERVICE_URL`. Only public
values belong in `.env.local`. Never import the root `.env` or expose private keys.
Read [../CONTRIBUTING.md](../CONTRIBUTING.md) before changing shared files.
