ntfy_url := env_var_or_default('NTFY_URL', "https://ntfy.sh/your_url_here")
gitroot := env_var_or_default('GITROOT', "./")
set positional-arguments

ingest *args:
    #!/usr/bin/env bash
    git pull || exit 1
    if ! python entrypoint.py ingest "$@"; then
        just send --priority max "Ingest failed with args: $@"
        exit 1
    fi

send *args:
    #!/usr/bin/env bash
    python entrypoint.py send "$@"

docs:
    #!/usr/bin/env bash
    pushd "{{ gitroot }}/book";
      mdbook build
    popd

test_message_delivery:
    just send "Test message"

setup *args:
    #!/usr/bin/env bash
    git pull || exit 1
    if ! python entrypoint.py setup "$@"; then
        just send --priority max "Setup failed with args: $@"
        exit 1
    fi

srun *args:
    #!/usr/bin/env bash
    git pull || exit 1
    if ! python entrypoint.py srun "$@"; then
        just send --priority max "Setup failed with args: $@"
        exit 1
    fi

test *args:
    python entrypoint.py test "$@"

exp *args:
    python entrypoint.py exp "$@"

kexp *args:
    python entrypoint.py kexp "$@"

tkexp *args:
    python entrypoint.py tkexp "$@"

i *args:
    python entrypoint.py i "$@"

killjob *args:
    #!/usr/bin/env bash
    python entrypoint.py killjob "$@"

screen:
    #!/usr/bin/env python
    from greenflow.screen import ExperimentApp
    
    TA = ExperimentApp()
    TA.run()
