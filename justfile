set positional-arguments

default:
	@echo "No targets specified. Assuming e2e"
e2e:
	time python -m greenflow e2e

setup:
	time python -m greenflow setup
provision:
	time python -m greenflow provision
deploy:
	time python -m greenflow deploy
base:
	time python -m greenflow base
strimzi:
	time python -m greenflow strimzi
theodolite:
	time python -m greenflow theodolite

exp:
	time python -m greenflow exp
blowaway:
	time python -m greenflow blowaway
destroy:
	time python -m greenflow destroy
redpanda:
	time python -m greenflow redpanda
killjob:
	time python -m greenflow killjob
mockdestroy:
	time python -m greenflow mock_destroy
vm:
	time python -m greenflow vm
