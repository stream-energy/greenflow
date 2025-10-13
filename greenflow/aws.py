from functools import cached_property
import os
from pathlib import Path

import pendulum
import pulumi
import pulumi_aws as aws
import requests
import yaml
from pulumi import automation as auto
from pulumi_aws import ec2

import gin

from .platform import Platform


@gin.register()
class AwsPlatform(Platform):
    @gin.register()
    def get_conf(
        self,
        *,
        instance_type: str = "t3.small",
        region: str = "eu-west-1",
        cluster: str = gin.REQUIRED,
        num_control: int = gin.REQUIRED,
        num_worker: int = gin.REQUIRED,
        num_broker: int = gin.REQUIRED,
        walltime: str = gin.REQUIRED,
        queue: str = gin.REQUIRED,
        project: str = gin.REQUIRED,
    ):
        return {
            "instance_type": instance_type,
            "region": region,
            "cluster": cluster,
            "num_control": num_control,
            "num_worker": num_worker,
            "num_broker": num_broker,
            "walltime": walltime,
            "queue": queue,
            "project": project,
        }

    def __init__(self):
        super().__init__()
        os.environ["PULUMI_CONFIG_PASSPHRASE"] = ""
        self.metadata = {}
        self.stack = None

    def pre_provision(self):
        os.environ["AWS_DEFAULT_REGION"] = self.get_conf()["region"]

    def _get_pulumi_program(self):
        conf = self.get_conf()
        num_control = conf["num_control"]
        num_worker = conf["num_worker"]
        num_broker = conf["num_broker"]
        instance_type = conf["instance_type"]

        def pulumi_program():
            try:
                ssh_public_key = Path("~/.ssh/aws.pub").expanduser().read_text()
            except FileNotFoundError:
                raise Exception(
                    "SSH public key not found at ~/.ssh/aws.pub. Please generate it first."
                )

            aws_key_pair = ec2.KeyPair(
                "aws-key-pulumi",
                public_key=ssh_public_key,
            )

            default_vpc = ec2.get_vpc(default=True)
            k3s_cluster_sg = ec2.SecurityGroup(
                "k3s-cluster-sg",
                vpc_id=default_vpc.id,
                description="Security group for the K3s cluster",
                tags={"Name": "k3s-cluster-sg"},
                ingress=[
                    ec2.SecurityGroupIngressArgs(
                        protocol="tcp",
                        from_port=22,
                        to_port=22,
                        cidr_blocks=["0.0.0.0/0"], 
                        description="Allow SSH access from a specific IP",
                    ),
                    ec2.SecurityGroupIngressArgs(
                        protocol="tcp",
                        from_port=6443,
                        to_port=6443,
                        cidr_blocks=["0.0.0.0/0"], 
                        description="Allow SSH access from a specific IP",
                    ),
                    # K3s rules for inter-node communication
                    ec2.SecurityGroupIngressArgs(
                        protocol="tcp",
                        from_port=0,
                        to_port=65535,
                        self=True, # Allows all TCP from other members of this SG
                        description="Allow all internal TCP traffic for K3s",
                    ),
                    ec2.SecurityGroupIngressArgs(
                        protocol="udp",
                        from_port=0,
                        to_port=65535,
                        self=True, # Allows all UDP from other members of this SG
                        description="Allow all internal UDP traffic for K3s",
                    ),
                ],
                egress=[
                    ec2.SecurityGroupEgressArgs(
                        protocol="-1", from_port=0, to_port=0, cidr_blocks=["0.0.0.0/0"]
                    )
                ],
            )


            ami = ec2.get_ami(
                most_recent=True,
                owners=["443870713157"],
                filters=[
                    ec2.GetAmiFilterArgs(
                        name="name",
                        values=["nixos-x86_64-*"],
                    ),
                ],
            )

            outputs = {"control": [], "worker": [], "broker": []}

            for i in range(num_control):
                instance = ec2.Instance(
                    f"control-{i}",
                    instance_type=instance_type,
                    vpc_security_group_ids=[k3s_cluster_sg.id],
                    ami=ami.id,
                    key_name=aws_key_pair.key_name,
                    tags={"Name": f"control-{i}"},
                    root_block_device=ec2.InstanceRootBlockDeviceArgs(
                        volume_size=30,
                    ),
                )
                outputs["control"].append(
                    {
                        "id": instance.id,
                        "public_ip": instance.public_ip,
                        "private_ip": instance.private_ip,
                        "public_dns": instance.public_dns,
                    }
                )

            for i in range(num_worker):
                instance = ec2.Instance(
                    f"worker-{i}",
                    instance_type=instance_type,
                    vpc_security_group_ids=[k3s_cluster_sg.id],
                    ami=ami.id,
                    key_name=aws_key_pair.key_name,
                    tags={"Name": f"worker-{i}"},
                    root_block_device=ec2.InstanceRootBlockDeviceArgs(
                        volume_size=30,
                    ),
                )
                outputs["worker"].append(
                    {
                        "id": instance.id,
                        "public_ip": instance.public_ip,
                        "private_ip": instance.private_ip,
                        "public_dns": instance.public_dns,
                    }
                )

            for i in range(num_broker):
                instance = ec2.Instance(
                    f"broker-{i}",
                    instance_type=instance_type,
                    vpc_security_group_ids=[k3s_cluster_sg.id],
                    ami=ami.id,
                    key_name=aws_key_pair.key_name,
                    tags={"Name": f"broker-{i}"},
                    root_block_device=ec2.InstanceRootBlockDeviceArgs(
                        volume_size=30,
                    ),
                )
                outputs["broker"].append(
                    {
                        "id": instance.id,
                        "public_ip": instance.public_ip,
                        "private_ip": instance.private_ip,
                        "public_dns": instance.public_dns,
                    }
                )

            pulumi.export("outputs", outputs)

        return pulumi_program

    @gin.register
    def provision(self):
        conf = self.get_conf()
        project_name = f"aws-greenflow-{conf['cluster']}"
        stack_name = "dev"

        # Ensure Pulumi local backend dir exists
        os.makedirs("/tmp/.pulumi/stacks", exist_ok=True)

        # Need to run first, let's automate it here
        project_settings = auto.ProjectSettings(
            name=project_name,
            runtime="python",
            backend=auto.ProjectBackend("file:///tmp/.pulumi/stacks"),
        )

        ws = auto.LocalWorkspace(project_settings=project_settings)
        ws.program = self._get_pulumi_program()

        # try:
        #     stack = ws.select_stack(stack_name)
        #     print(f"Stack '{stack_name}' successfully selected.")
        # except Exception:
        #     print(f"Stack '{stack_name}' not found, creating it...")
        #     stack = ws.create_stack(stack_name)
        #     print(f"Stack '{stack_name}' created.")
        #     stack = ws.select_stack(stack_name)

        st = auto.Stack(
            stack_name,
            ws,
            auto._stack.StackInitMode.CREATE_OR_SELECT,
        )
        # store the stack on the instance for later use
        self.stack = st

        # self.stack.set_config("aws:region", {"value": conf["region"]})
        try:
            print("🔓 Clearing any existing locks...")
            st.cancel()
            print("✅ Lock cleared.")

            st.refresh(on_output=print)
            # Run the deployment
            up_res = st.up(on_output=print)
            print("✅ Deployment successful!")

            # Print outputs
            for key, value in up_res.outputs.items():
                print(f"{key}: {value.value}")

        except Exception as e:
            print(f"ℹ️  An error occurred: {e}")
            # In case of an error, it's good practice to try to cancel any lingering lock.
            try:
                st.cancel()
                print("✅ Lock cleared after error.")
            except Exception as cancel_e:
                print(f"ℹ️  Could not clear lock after error: {cancel_e}")
                raise cancel_e
            raise e

        self.metadata["pulumi_outputs"] = up_res.outputs["outputs"].value
        return self.metadata["pulumi_outputs"]

    def set_platform_metadata(self):
        from .g import g

        self.metadata["type"] = "aws"
        self.metadata["job_started_ts"] = pendulum.now("UTC").format(
            "YYYY-MM-DDTHH:mm:ssZ"
        )

        inventory = {"all": {"children": {}}}
        outputs = self.metadata["pulumi_outputs"]

        for role in ["control", "worker", "broker"]:
            inventory["all"]["children"][role] = {"hosts": {}}
            for i, node in enumerate(outputs[role]):
                host_alias = node["public_dns"]
                inventory["all"]["children"][role]["hosts"][host_alias] = {
                    "ansible_host": node["public_ip"],
                    "ansible_user": "root",
                    "ansible_interpreter": "/run/current-system/sw/bin/python3",
                    "private_ip": node["private_ip"],
                    "instance_id": node["id"],
                    "role": role,
                    "role_id": i,
                }
                if role == "control":
                    inventory["all"]["children"][role]["hosts"][host_alias][
                        "kubernetes_role"
                    ] = "control_plane"
                elif role == "worker":
                    inventory["all"]["children"][role]["hosts"][host_alias][
                        "kubernetes_role"
                    ] = "node"
                elif role == "broker":
                    inventory["all"]["children"][role]["hosts"][host_alias][
                        "kubernetes_role"
                    ] = "broker"

        self.metadata["ansible_inventory"] = inventory
        g.reinit_deployment(self)

    def handle_hardware_quirks(self):
        pass

    def _wait_for_nodes_to_be_ready(self, timeout_per_node=10, total_timeout=300):
        import socket
        import time

        inventory = self.get_ansible_inventory()
        hosts_to_check = []
        for role in ["control", "worker", "broker"]:
            if role in inventory["all"]["children"]:
                for host_details in inventory["all"]["children"][role]["hosts"].values():
                    hosts_to_check.append(host_details["ansible_host"])

        if not hosts_to_check:
            print("No hosts to check, continuing.")
            return

        print("Waiting for instances to be reachable on SSH port 22...")
        start_time = time.time()
        unreachable_hosts = set(hosts_to_check)

        while unreachable_hosts and (time.time() - start_time) < total_timeout:
            reachable_this_round = set()
            for host_ip in list(unreachable_hosts):
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(timeout_per_node)
                        s.connect((host_ip, 22))
                    print(f"✅ Host {host_ip} is reachable.")
                    reachable_this_round.add(host_ip)
                except (socket.timeout, ConnectionRefusedError, OSError):
                    print(f"⏳ Host {host_ip} is not yet reachable...")

            unreachable_hosts -= reachable_this_round
            if unreachable_hosts:
                time.sleep(5)

        if unreachable_hosts:
            raise Exception(
                f"Timeout reached. The following hosts are still not reachable: {', '.join(unreachable_hosts)}"
            )

        print("✅ All instances are reachable.")

    def post_provision(self):
        from .g import g
        from .playbook import deploy_aws_k3s

        self.set_platform_metadata()

        with open(f"{g.gitroot}/ansible/inventory/hosts.yaml", "w") as f:
            yaml.dump(self.get_ansible_inventory(), f)

        self._wait_for_nodes_to_be_ready()

        deploy_aws_k3s()

        self.handle_hardware_quirks()

    def pre_teardown(self):
        pass

    def teardown(self):
        self.pre_teardown()
        
        try:
            if not self.stack:
                print("⚠️  Stack not found in instance, attempting to load from backend...")
                conf = self.get_conf()
                project_name = f"aws-greenflow-{conf['cluster']}"
                stack_name = "dev"
                work_dir = "/tmp/.pulumi/stacks"

                project_settings = auto.ProjectSettings(
                    name=project_name,
                    runtime="python",
                    backend=auto.ProjectBackend(f"file://{work_dir}"),
                )

                ws = auto.LocalWorkspace(
                    project_settings=project_settings, work_dir=work_dir
                )

                st = auto.Stack(
                    stack_name,
                    ws,
                    auto._stack.StackInitMode.SELECT,
                )
            else:
                st = self.stack
                print("✅ Using existing stack instance.")

            # Clear any existing locks before attempting destroy
            print("🔓 Clearing any existing locks before teardown...")
            try:
                st.cancel()
                print("✅ Lock cleared successfully.")
            except Exception as cancel_e:
                print(f"ℹ️  No lock to clear or lock clearing failed: {cancel_e}")
                # Continue anyway - there might not be a lock

            # Perform the destroy operation
            print("🗑️  Starting stack destruction...")
            st.destroy(on_output=print)
            print("✅ Stack destroyed successfully!")
            
            self.post_teardown()
            
        except auto.CommandError as e:
            print(f"❌ Pulumi command error during teardown: {e}")
            # Try to clear lock one more time
            try:
                print("🔓 Attempting to clear lock after error...")
                st.cancel()
                print("✅ Lock cleared after error.")
            except Exception as final_cancel_e:
                print(f"⚠️  Could not clear lock after error: {final_cancel_e}")
            raise e
        except Exception as e:
            print(f"❌ Unexpected error during teardown: {e}")
            raise e


    def get_ansible_inventory(self) -> dict:
        return self.metadata["ansible_inventory"]

    def post_teardown(self):
        pass
