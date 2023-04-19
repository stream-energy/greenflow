set positional-arguments

default:
	@echo "No targets specified. Assuming deploy"
deploy $ARGS:
	time python -m greenflow full $1
e2e $ARGS:
	time python -m greenflow e2e $1
destroy:
	time python -m greenflow destroy
redpanda:
	time python -m greenflow redpanda
killjob:
	time python -m greenflow killjob
kafka:
	time python -m greenflow kafka
mockdestroy:
	time python -m greenflow mock_destroy
blowaway:
	time python -m greenflow blowaway
