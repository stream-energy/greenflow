set positional-arguments

base:
	time python -m greenflow base
default:
	@echo "No targets specified. Assuming deploy"
deploy $ARGS:
	time python -m greenflow full $1
e2e:
	time python -m greenflow e2e
destroy:
	time python -m greenflow destroy
redpanda:
	time python -m greenflow redpanda
theo:
	time python -m greenflow theo
killjob:
	time python -m greenflow killjob
kafka:
	time python -m greenflow kafka
mockdestroy:
	time python -m greenflow mock_destroy
blowaway:
	time python -m greenflow blowaway
vm:
	time python -m greenflow vm
exp:
	time python -m greenflow exp
