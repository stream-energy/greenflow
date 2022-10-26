default: run
	@echo "No targets specified. Assuming deploy"
debug:
	python -m pdb -c continue -m greenflow run
deploy:
	time python -m greenflow deploy
destroy:
	time python -m greenflow destroy
run:
	time python -m greenflow run
mock:
	time python -m greenflow mock
