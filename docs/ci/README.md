# Continuous integration

`github-actions-ci.yml` is the pipeline for this project. It is stored here
rather than in `.github/workflows/` because the token used to push these
commits lacks GitHub's `workflows` permission, so the push is rejected when
that path is touched.

## Activate it

```bash
mkdir -p .github/workflows
cp docs/ci/github-actions-ci.yml .github/workflows/ci.yml
git add .github/workflows/ci.yml
git commit -m "ci: enable GitHub Actions"
git push
```

Pushing from your own account carries the `workflow` scope, so this succeeds.

## What it runs

| Job | Steps |
|---|---|
| **backend** | Python 3.11 + 3.12 · architecture check · `print()` check · pytest with coverage |
| **frontend** | `npm ci` · lint · tests · production build · upload bundle |
| **docker** | build both images · boot the API container · register a user · assert an unauthenticated request is refused |

The Docker job deliberately does more than `docker build`: it starts the image
and exercises it, because a build can succeed and the container still crash on
startup. That is exactly what happened in v11.1.0, when the auth dependencies
were missing from `pyproject.toml`.

## Running the same checks locally

```bash
python scripts/check_architecture.py                    # DDD boundary
QUANTNEST_MARKET_PROVIDER=fake pytest -q                # 118 backend tests
cd frontend && npm run lint && npm test && npm run build
```
