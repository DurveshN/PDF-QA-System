# FRONTEND KNOWLEDGE BASE

**Scope:** Vite + React + TypeScript SPA

## OVERVIEW
React single-page application for the PDF-QA system. Bootstrapped via Vite, styled with Tailwind CSS v3, and state-managed with Zustand.

## STRUCTURE
```
frontend/
├── index.html          # Vite entry point
├── vite.config.ts      # Vite configuration
├── tailwind.config.js  # Tailwind theme + custom colors
├── postcss.config.js   # PostCSS pipeline
├── package.json        # Dependencies + scripts
├── public/             # Static assets
├── dist/               # Production build output
└── src/
    ├── main.tsx        # React bootstrap
    ├── App.tsx         # Root component + routing
    ├── index.css       # Tailwind directives + global styles
    ├── pages/          # Route-level page components
    ├── components/     # Shared, reusable UI components
    ├── hooks/          # Custom React hooks
    ├── store/          # Zustand global state modules
    ├── types/          # TypeScript type definitions
    ├── lib/            # Utility functions and helpers
    └── vite-env.d.ts   # Vite client type declarations
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Add a new page/route | `src/pages/` | Register the route in `src/App.tsx` |
| Add a shared UI component | `src/components/` | Keep components focused and reusable |
| Add a custom React hook | `src/hooks/` | Prefix with `use`, co-locate related logic |
| Add global state | `src/store/` | Uses Zustand; create a new store slice if needed |
| Add TypeScript types | `src/types/` | Share types across pages and components |
| Add utility/helper functions | `src/lib/` | Pure functions, no React dependencies |
| Change styling/theme | `tailwind.config.js` | Custom `surface` and `accent` scales defined here |
| Change the app entry point | `index.html` | Vite injects `src/main.tsx` automatically |

## CONVENTIONS
- **TypeScript strict mode** is enabled. Avoid `any`. Prefer explicit types.
- **React JSX transform** is used. Do not import `React` just for JSX.
- **Tailwind CSS v3** with custom color scales: `surface` and `accent`.
- **Dark mode** is class-based (`darkMode: 'class'`). Toggle the `dark` class on a parent element.
- **State management** uses Zustand in `src/store/`. Keep store logic flat and atomic.
- **No ESLint config file** exists. `eslint` is listed in `devDependencies` but runs without an explicit config.
- **No testing infrastructure** is set up. Do not add test files unless explicitly requested.

## ANTI-PATTERNS
- **Do NOT import `React`** just for JSX. The JSX transform handles this.
- **Do NOT use `any`** in TypeScript. Use `unknown` or proper interfaces instead.
- **Do NOT put business logic in components**. Move it to `src/hooks/` or `src/lib/`.
- **Do NOT commit the `dist/` directory**. It is a build artifact.
