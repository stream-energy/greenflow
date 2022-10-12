default: deploy
	@echo "No targets specified. Assuming deploy"
debug:
	python -m pdb -c continue -m greenflow deploy
deploy:
	python -m greenflow deploy
destroy:
	python -m greenflow destroy
run:
	python -m greenflow run
