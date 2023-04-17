set positional-arguments

default:
	@echo "No targets specified. Assuming deploy"
deploy $ARGS:
	time python -m greenflow full $1
destroy:
	time python -m greenflow destroy
