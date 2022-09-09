default: deploy
	@echo "No targets specified. Assuming deploy"
deploy:
	python -m pdb -c continue -m greenflow deploy
destroy:
	python -m pdb -c continue -m greenflow destroy
