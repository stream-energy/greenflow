from pulumi_ovh import BaremetalServer


@gin.register()
class OvhBaremetalPlatform(Platform):
    def __init__(self):
        self.metadata = {}

    def set_platform_metadata(self):
        self.metadata = {
            "provider": "ovh",
            "type": "baremetal",
            "region": "EU",  # Example region
            # Add other metadata as needed
        }

    def pre_provision(self):
        print("Pre-provisioning steps for OVH Baremetal")

    def provision(self):
        print("Provisioning OVH Baremetal server with Pulumi")

        # Create a Pulumi stack
        config = pulumi.Config()
        project_name = config.require("project_name")
        stack_name = config.require("stack_name")

        stack = pulumi.automation.create_or_select_stack(stack_name, project_name)

        def pulumi_program():
            # Define the OVH Baremetal server
            server = BaremetalServer(
                "my-server", flavor="eg-15", image="ubuntu-20.04", region="GRA1"
            )
            pulumi.export("server_ip", server.public_ip)

        # Run the Pulumi program
        stack.up(on_output=print)

        # Retrieve the server IP
        outputs = stack.outputs()
        server_ip = outputs.get("server_ip").value

        self.metadata["server_ip"] = server_ip
        return self.metadata

    def post_provision(self):
        print("Post-provisioning steps for OVH Baremetal")
        self.set_platform_metadata()
        with open("ansible/inventory/hosts.yaml", "w") as f:
            yaml.dump(self.get_ansible_inventory(), f)
        transaction.commit()

    def pre_teardown(self):
        print("Pre-teardown steps for OVH Baremetal")

    def teardown(self):
        self.pre_teardown()
        print("Tearing down OVH Baremetal server with Pulumi")

        # Create a Pulumi stack
        config = pulumi.Config()
        project_name = config.require("project_name")
        stack_name = config.require("stack_name")

        stack = pulumi.automation.create_or_select_stack(stack_name, project_name)

        # Destroy the Pulumi stack
        stack.destroy(on_output=print)

        self.post_teardown()

    def post_teardown(self):
        print("Post-teardown steps for OVH Baremetal")

    def get_platform_metadata(self) -> dict:
        return self.metadata

    def get_ansible_inventory(self) -> dict:
        return {
            "all": {
                "hosts": {
                    "ovh_baremetal": {
                        "ansible_host": self.metadata.get("server_ip"),
                        "ansible_user": "root",
                        "ansible_ssh_private_key_file": "/path/to/private/key",
                    }
                }
            }
        }
