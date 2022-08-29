default: deploy
	@echo "No targets specified. Assuming deploy"
deploy:
	python -m greenflow deploy
destroy:
	python -m greenflow destroy
