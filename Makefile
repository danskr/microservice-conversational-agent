.PHONY: test build load secrets deploy port-forward smoke clean

test:
	pytest -q

build:
	docker build -t order-fulfillment-conversational-agent:1.0.0 .

load:
	./scripts/build-and-load.sh

secrets:
	./scripts/create-secrets.sh

deploy:
	./scripts/deploy.sh

port-forward:
	./scripts/port-forward.sh

smoke:
	./scripts/smoke-knowledge.sh
	./scripts/smoke-runtime-read.sh

clean:
	./scripts/delete.sh
