.PHONY: verify down
COMPOSE = docker compose -f docker-compose.yml

verify:
	@set -eu; \
	if ! command -v docker >/dev/null 2>&1; then echo 'FAIL — Docker est requis pour make verify.'; exit 1; fi; \
	if ! docker compose version >/dev/null 2>&1; then echo 'FAIL — Docker Compose v2 est requis.'; exit 1; fi; \
	cleanup() { $(COMPOSE) --profile verify down >/dev/null 2>&1 || true; }; \
	trap cleanup EXIT; \
	echo 'Contrôle 1/7 — build API/frontend/PostgreSQL'; \
	if $(COMPOSE) --profile verify build; then echo 'PASS — build images'; else echo 'FAIL — build images'; exit 1; fi; \
	echo 'Contrôle 2/7 — démarrage DB, API et frontend'; \
	if $(COMPOSE) --profile verify up -d --wait postgres api frontend; then echo 'PASS — services prêts'; else echo 'FAIL — démarrage/healthcheck'; exit 1; fi; \
	echo 'Contrôle 3/7 — migrations PostgreSQL'; \
	if $(COMPOSE) exec -T api alembic upgrade head; then echo 'PASS — migrations'; else echo 'FAIL — migrations'; exit 1; fi; \
	echo 'Contrôle 4/7 — tests API/SITL'; \
	if $(COMPOSE) --profile verify run --rm api-test; then echo 'PASS — tests backend'; else echo 'FAIL — tests backend'; exit 1; fi; \
	echo 'Contrôle 5/7 — typecheck/tests frontend (dont cockpit → LabBench)'; \
	if $(COMPOSE) --profile verify run --rm frontend-test; then echo 'PASS — tests frontend'; else echo 'FAIL — tests frontend'; exit 1; fi; \
	echo 'Contrôle 6/7 — smoke HTTP frontend/API'; \
	if curl --fail --silent --show-error http://localhost:$${FRONTEND_PORT:-8080}/ >/dev/null && curl --fail --silent --show-error http://localhost:$${API_PORT:-10000}/api/health; then echo 'PASS — smoke HTTP'; else echo 'FAIL — smoke HTTP'; exit 1; fi; \
	echo 'Contrôle 7/7 — teardown'; \
	$(COMPOSE) --profile verify down; trap - EXIT; echo 'PASS — teardown'; \
	echo 'RÉSULTAT FINAL: PASS — tous les contrôles make verify ont réussi.'

down:
	$(COMPOSE) --profile verify down
