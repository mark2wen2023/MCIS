# Stored-result unmounted component checks

From web with project dependencies installed:

```sh
./node_modules/.bin/esbuild tests/stored-primary.tsx --bundle --platform=node --format=cjs --outfile=/tmp/stored-primary.cjs --jsx=automatic
node /tmp/stored-primary.cjs
./node_modules/.bin/esbuild tests/stored-independent.tsx --bundle --platform=node --format=cjs --outfile=/tmp/stored-independent.cjs --jsx=automatic
node /tmp/stored-independent.cjs
./node_modules/.bin/tsc --noEmit --strict --target es2022 --module esnext --moduleResolution bundler --jsx react-jsx --skipLibCheck src/storedUnreviewed/*.ts src/storedUnreviewed/*.tsx
```

Primary25 checks; independent29 cases passed; targeted TypeScript exits0. Counts
are separate scripts, overlap in behavior. React SSR, not browser or user E2E.
Synthetic fixture comes from current backend GET with controlled core result;
no sessions/tokens/raw evidence text. Expected request/generation are test fixtures,
not an implemented authenticated browser provider. Product component not routed
or connected. Do not configure production by passing fixture scopes.

Real backend/W2 save-read acceptance is separately documented; this suite does
not exercise W2 or live HTTP. No login/LLM/browser/whole-frontend-build/CI claim.
