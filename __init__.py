#  This function is not intended to be invoked directly. Instead it will be
# triggered by an orchestrator function.
# Before running this sample, please:
# - create a Durable orchestration function
# - create a Durable HTTP starter function
# - add azure-functions-durable to requirements.txt
# - run pip install -r requirements.txt
import datetime
import logging
import random
import string
import time
import sys
from os import getenv
from azure.common.client_factory import get_client_from_json_dict
# from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.containerinstance.models.image_registry_credential import ImageRegistryCredential
# from azure.common.client_factory import get_client_from_auth_file
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.containerinstance import ContainerInstanceManagementClient
from azure.mgmt.containerinstance.models import (ContainerGroup,
                                                 Container,
                                                 ContainerGroupNetworkProtocol,
                                                 ContainerGroupRestartPolicy,
                                                 ContainerPort,
                                                 EnvironmentVariable,
                                                 IpAddress,
                                                 Port,
                                                 ResourceRequests,
                                                 ResourceRequirements,
                                                 OperatingSystemTypes)
myAzureuth = {
  "clientId": "2563c19c-5c49-4b24-9df0-14c417dbac62",
  "clientSecret": "FPNxLStt0Ea8Wd7WMEO7V6w.S8__x6k0-C",
  "subscriptionId": "87c17826-ee80-4f60-b162-f0775b6bf032",
  "tenantId": "00b4578d-d017-4492-bd71-61c1acd8feec",
  "activeDirectoryEndpointUrl": "https://login.microsoftonline.com",
  "resourceManagerEndpointUrl": "https://management.azure.com/",
  "activeDirectoryGraphResourceId": "https://graph.windows.net/",
  "sqlManagementEndpointUrl": "https://management.core.windows.net:8443/",
  "galleryEndpointUrl": "https://gallery.azure.com/",
  "managementEndpointUrl": "https://management.core.windows.net/"
}


 # define the random module  
S = 10  # number of characters in the string.  
# call random.choices() string module to find the string in Uppercase + numeric data.  
today = datetime.datetime.now()
date_time = today.strftime("%m-%d-%Y-%H-%M-%S")
ran_string = ''.join(random.choices(string.ascii_lowercase, k = S))

ran_name=ran_string+"-"+date_time


def main(output: str) -> str:
    """Main entry point for the application.
    """
    azure_region = 'eastus'
    resource_group_name = 'Rush'

    container_group_name = ran_name
    # pip install azure==4.0.0
    # container_image_app = "mcr.microsoft.com/azuredocs/aci-helloworld"
    container_image_app = "ctakesimageregistry.azurecr.io/dockerctakes:latest"
    # container_image_app = "a3eacr.azurecr.io/simplepythonapp:latest"
    # logging.info(container_image_app)

    # Authenticate the management clients with Azure.
    # Set the AZURE_AUTH_LOCATION environment variable to the full path to an
    # auth file. Generate an auth file with the Azure CLI or Cloud Shell:
    # az ad sp create-for-rbac --role Contributor --scopes /subscriptions/{subscriptionId}/resourceGroups/{resourceGroup1} --sdk-auth > my.azureauth
    # set evironment variable:=> AZURE_AUTH_LOCATION = 'D:\Azure\create ACI\my.azureauth'
    # auth_file_path = getenv('AZURE_AUTH_LOCATION', None)
    AZURE_AUTH_LOCATION='https://rushstorageacc.file.core.windows.net/aciauthfile/aciauthfiledirectory/my.azureauth'
    auth_file_path = AZURE_AUTH_LOCATION
    # print(auth_file_path)
    if auth_file_path is not None:
        print("Authenticating with Azure using credentials in file at {0}"
              .format(auth_file_path))

        aciclient = get_client_from_json_dict(
            ContainerInstanceManagementClient, myAzureuth)
        resclient = get_client_from_json_dict(ResourceManagementClient, myAzureuth)
    else:
        print("\nFailed to authenticate to Azure. Have you set the"
              " AZURE_AUTH_LOCATION environment variable?\n")

    # Create (and then get) a resource group into which the container groups
    # are to be created
    print("Creating resource group '{0}'...".format(resource_group_name))
    resclient.resource_groups.create_or_update(resource_group_name,
                                               {'location': azure_region})
    resource_group = resclient.resource_groups.get(resource_group_name)


    def create_container_group(aci_client, resource_group,
                            container_group_name, container_image_name, start_command_line=None):
        """Creates a container group with a single container.
        Arguments:
            aci_client {azure.mgmt.containerinstance.ContainerInstanceManagementClient}
                        -- An authenticated container instance management client.
            resource_group {azure.mgmt.resource.resources.models.ResourceGroup}
                        -- The resource group in which to create the container group.
            container_group_name {str}
                        -- The name of the container group to create.
            =container_image_name {str}
                        -- The container image name and tag, for example:
                        microsoft\aci-helloworld:latest
        """
        # Configure some environment variables in the container which the
        # wordcount.py or other script can read to modify its behavior.
        env_var_1 = EnvironmentVariable(name='blobDownload', value=output)

        print("Creating container group '{0}' withss start command '{1}'"
            .format(container_group_name, start_command_line))
        # print("Creating container group '{0}'...".format(container_group_name))

        # Configure the container
        container_resource_requests = ResourceRequests(memory_in_gb=1, cpu=1.0)
        container_resource_requirements = ResourceRequirements(
            requests=container_resource_requests)
        container = Container(name=container_group_name,
                            image=container_image_name,
                            resources=container_resource_requirements,
                            ports=[ContainerPort(port=80)],
                            environment_variables=[env_var_1])

        # Configure the container group
        ports = [Port(protocol=ContainerGroupNetworkProtocol.tcp, port=80)]
        group_ip_address = IpAddress(ports=ports,
                                    dns_name_label=container_group_name,
                                    type="Public")
        credentials = [ImageRegistryCredential(server='ctakesimageregistry.azurecr.io', username='ctakesimageregistry', password='JU4M6fqyFWxVIUalsTNO5u4I4t/sBHSR')]
        group = ContainerGroup(location=resource_group.location,
                            containers=[container],
                            os_type=OperatingSystemTypes.linux,
                            restart_policy=ContainerGroupRestartPolicy.on_failure,
                            ip_address=group_ip_address,
                            image_registry_credentials=credentials)

        # Create the container group
        result = aci_client.container_groups.create_or_update(resource_group.name,
                                                    container_group_name,
                                                    group)

        # Wait for the container create operation to complete. The operation is
        # "done" when the container group provisioning state is one of:
        # Succeeded, Canceled, Failed
        while result.done() is False:
            sys.stdout.write('.')
            time.sleep(1)

        # Get the provisioning state of the container group.
        container_group = aci_client.container_groups.get(resource_group.name,
                                                        container_group_name)
        if str(container_group.provisioning_state).lower() == 'succeeded':
            print("\nCreation of container group '{}' succeeded."
                .format(container_group_name))
        else:
            print("\nCreation of container group '{}' failed. Provisioning state"
                "is: {}".format(container_group_name,
                                container_group.provisioning_state))

        # Get the logs for the container
        logs = aci_client.container.list_logs(resource_group.name,
                                            container_group_name,
                                            container.name)

        print("Logs for container '{0}':".format(container_group_name))
        print("{0}".format(logs.content))

        # Get the created container group
        container_group = aci_client.container_groups.get(resource_group.name,
                                                        container_group_name)

        print("Once DNS has propagated, container group '{0}' will be reachable at"
            " http://{1}".format(container_group_name,
                                container_group.ip_address.fqdn))

    def list_container_groups(aci_client, resource_group):
        """Lists the container groups in the specified resource group.
        Arguments:
        aci_client {azure.mgmt.containerinstance.ContainerInstanceManagementClient}
                    -- An authenticated container instance management client.
        resource_group {azure.mgmt.resource.resources.models.ResourceGroup}
                    -- The resource group containing the container group(s).
        """
        print("Listing container groups in resource group '{0}'...".format(
            resource_group.name))

        container_groups = aci_client.container_groups.list_by_resource_group(
            resource_group.name)

        for container_group in container_groups:
            print("{0}".format(container_group.name))


    def print_container_group_details(aci_client, resource_group, container_group_name):
        """Gets the specified container group and then prints a few of its properties and their values.
        Arguments:
            aci_client {azure.mgmt.containerinstance.ContainerInstanceManagementClient}
                        -- An authenticated container instance management client.
            resource_group {azure.mgmt.resource.resources.models.ResourceGroup}
                        -- The name of the resource group containing the container
                        group.
            container_group_name {str}
                        -- The name of the container group whose details should be
                        printed.
        """
        print("Getting container group details for container group '{0}'..."
            .format(container_group_name))

        container_group = aci_client.container_groups.get(resource_group.name,
                                                        container_group_name)
        print("------------------------")
        print("Name:   {0}".format(container_group.name))
        print("State:  {0}".format(container_group.provisioning_state))
        print("FQDN:   {0}".format(container_group.ip_address.fqdn))
        print("IP:     {0}".format(container_group.ip_address.ip))
        print("Region: {0}".format(container_group.location))
        print("Containers:")
        for container in container_group.containers:
            print("  Name:  {0}".format(container.name))
            print("  Image: {0}".format(container.image))
            print("  State: {0}".format(
                container.instance_view.current_state.state))
            print("  ----------")
    
    # Demonstrate various container group operations
    create_container_group(aciclient, resource_group, container_group_name,
                           container_image_app, None)

    list_container_groups(aciclient, resource_group)
    print_container_group_details(aciclient,
                                  resource_group,
                                  container_group_name)

    logging.info(output)
    return f"{output}"

# def create_container_group(aci_client, resource_group,
#                            container_group_name, container_image_name):
#     """Creates a container group with a single container.
#     Arguments:
#         aci_client {azure.mgmt.containerinstance.ContainerInstanceManagementClient}
#                     -- An authenticated container instance management client.
#         resource_group {azure.mgmt.resource.resources.models.ResourceGroup}
#                     -- The resource group in which to create the container group.
#         container_group_name {str}
#                     -- The name of the container group to create.
#         container_image_name {str}
#                     -- The container image name and tag, for example:
#                        microsoft\aci-helloworld:latest
#     """
#     print("Creating container group '{0}'...".format(container_group_name))

#     # Configure the container
#     container_resource_requests = ResourceRequests(memory_in_gb=1, cpu=1.0)
#     container_resource_requirements = ResourceRequirements(
#         requests=container_resource_requests)
#     container = Container(name=container_group_name,
#                           image=container_image_name,
#                           resources=container_resource_requirements,
#                           ports=[ContainerPort(port=80)])

#     # Configure the container group
#     ports = [Port(protocol=ContainerGroupNetworkProtocol.tcp, port=80)]
#     group_ip_address = IpAddress(ports=ports,
#                                  dns_name_label=container_group_name,
#                                  type="Public")
#     credentials = [ImageRegistryCredential(server='ctakesdemoacr.azurecr.io', username='ctakesdemoacr', password='NWeCl=+9W3kKWykQ5gEph2XfYz8BBOr+')]
#     group = ContainerGroup(location=resource_group.location,
#                            containers=[container],
#                            os_type=OperatingSystemTypes.linux,
#                            restart_policy=ContainerGroupRestartPolicy.on_failure,
#                            ip_address=group_ip_address,
#                            image_registry_credentials=credentials)

#     # Create the container group
#     aci_client.container_groups.create_or_update(resource_group.name,
#                                                  container_group_name,
#                                                  group)

#     # Get the created container group
#     container_group = aci_client.container_groups.get(resource_group.name,
#                                                       container_group_name)

#     print("Once DNS has propagated, container group '{0}' will be reachable at"
#           " http://{1}".format(container_group_name,
#                                container_group.ip_address.fqdn))

# def list_container_groups(aci_client, resource_group):
#     """Lists the container groups in the specified resource group.
#     Arguments:
#        aci_client {azure.mgmt.containerinstance.ContainerInstanceManagementClient}
#                    -- An authenticated container instance management client.
#        resource_group {azure.mgmt.resource.resources.models.ResourceGroup}
#                    -- The resource group containing the container group(s).
#     """
#     print("Listing container groups in resource group '{0}'...".format(
#         resource_group.name))

#     container_groups = aci_client.container_groups.list_by_resource_group(
#         resource_group.name)

#     for container_group in container_groups:
#         print("{0}".format(container_group.name))


# def print_container_group_details(aci_client, resource_group, container_group_name):
#     """Gets the specified container group and then prints a few of its properties and their values.
#     Arguments:
#         aci_client {azure.mgmt.containerinstance.ContainerInstanceManagementClient}
#                     -- An authenticated container instance management client.
#         resource_group {azure.mgmt.resource.resources.models.ResourceGroup}
#                     -- The name of the resource group containing the container
#                        group.
#         container_group_name {str}
#                     -- The name of the container group whose details should be
#                        printed.
#     """
#     print("Getting container group details for container group '{0}'..."
#           .format(container_group_name))

#     container_group = aci_client.container_groups.get(resource_group.name,
#                                                       container_group_name)
#     print("------------------------")
#     print("Name:   {0}".format(container_group.name))
#     print("State:  {0}".format(container_group.provisioning_state))
#     print("FQDN:   {0}".format(container_group.ip_address.fqdn))
#     print("IP:     {0}".format(container_group.ip_address.ip))
#     print("Region: {0}".format(container_group.location))
#     print("Containers:")
#     for container in container_group.containers:
#         print("  Name:  {0}".format(container.name))
#         print("  Image: {0}".format(container.image))
#         print("  State: {0}".format(
#             container.instance_view.current_state.state))
#         print("  ----------")

#     # return f"Hello {name}!"
