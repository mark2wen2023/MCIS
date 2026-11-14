# Registered preview independent acceptance

From web/, install the normal web dependencies, then run:

```sh
npm install --prefix tests/registered-acceptance
bash tests/registered-acceptance/run.sh
```

The isolated test dependency is happy-dom 21.0.4. It is not a production dependency. The run covers 23 assertions using React + HappyDOM + controlled fetch; it is not browser E2E. The JSON fixture was captured from a separate local uvicorn + actual W2 run with two explicitly synthetic CSVs at 45 and 50 degrees. Reading this saved fixture only verifies parser regression, not a new HTTP run. No real accident evidence, authentication or live LLM is used.
