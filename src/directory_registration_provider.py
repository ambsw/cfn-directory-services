import logging
import boto3
from botocore.exceptions import ClientError

from cfn_resource_provider import ResourceProvider

log = logging.getLogger()
#log.setLevel('INFO')


request_schema = {
    "type": "object",
    "required": ["DirectoryId", "EnableWorkDocs"],
    "properties": {
        # register_workspace_directory
        "DirectoryId": {
            "type": "string",
            "description": "The identifier of the directory.",
        },
        "SubnetIds": {
            "type": "array",
            "description": "The identifiers of the subnets for your virtual private cfud (VPC).",
        },
        "EnableWorkDocs": {
            "type": "boolean",
            "description": "Indicates whether Amazon WorkDocs is enabled or disabled.",
        },
        "EnableSelfService": {
            "type": "boolean",
            "description": "Indicates whether self-service capabilities are enabled or disabled.",
        },
        "Tenancy": {
            "type": "string",
            "description": "Indicates whether your WorkSpace directory is dedicated or shared.",
        },
        "Tags": {
            "type": "string",
            "description": "The tags associated with the directory.",
        },
        # modify_client_properties
        # DirectoryId sent as ResourceId
        # Sent in ClientProperties dict
        "ReconnectEnabled": {
            "type": "string",
            "enum": ['ENABLED', 'DISABLED'],
            "description": "Specifies whether users can cache their credentials on the Amazon WorkSpaces client.",
        },
        # modify_workspace_access_properties
        # DirectoryId sent as ResourceId
        # Sent in WorkspaceAccessProperties dict
        "DeviceTypeWindows": {
            "type": "string",
            "enum": ['ALLOW', 'DENY'],
            "description": "Specifies whether users can cache their credentials on the Amazon WorkSpaces client.",
        },
        "DeviceTypeOsx": {
            "type": "string",
            "enum": ['ALLOW', 'DENY'],
            "description": "Specifies whether users can cache their credentials on the Amazon WorkSpaces client.",
        },
        "DeviceTypeWeb": {
            "type": "string",
            "enum": ['ALLOW', 'DENY'],
            "description": "Specifies whether users can cache their credentials on the Amazon WorkSpaces client.",
        },
        "DeviceTypeIos": {
            "type": "string",
            "enum": ['ALLOW', 'DENY'],
            "description": "Specifies whether users can cache their credentials on the Amazon WorkSpaces client.",
        },
        "DeviceTypeAndroid": {
            "type": "string",
            "enum": ['ALLOW', 'DENY'],
            "description": "Specifies whether users can cache their credentials on the Amazon WorkSpaces client.",
        },
        "DeviceTypeChromeOs": {
            "type": "string",
            "enum": ['ALLOW', 'DENY'],
            "description": "Specifies whether users can cache their credentials on the Amazon WorkSpaces client.",
        },
        "DeviceTypeZeroClient": {
            "type": "string",
            "enum": ['ALLOW', 'DENY'],
            "description": "Specifies whether users can cache their credentials on the Amazon WorkSpaces client.",
        },
        # modify_workspace_creation_properties
        # DirectoryId sent as ResourceId
        # Sent in WorkspaceCreationProperties dict
        "EnableInternetAccess": {
            "type": "boolean",
            "description": "Indicates whether internet access is enabled for your WorkSpaces.",
        },
        "DefaultOu": {
            "type": "string",
            "description": "The default organizational unit (OU) for your WorkSpace directories.",
        },
        "CustomSecurityGroupId": {
            "type": "string",
            "description": "The identifier of your custom security group.",
        },
        "UserEnabledAsLocalAdministrator": {
            "type": "boolean",
            "description": "Indicates whether users are local administrators of their WorkSpaces.",
        },
        "EnableMaintenanceMode": {
            "type": "boolean",
            "description": "Indicates whether maintenance mode is enabled for your WorkSpaces.",
        },
        # modify_selfservice_permissions
        # DirectoryId sent as ResourceId
        # Sent in ClientProperties dict
        "RestartWorkspace": {
            "type": "string",
            "enum": ['ENABLED', 'DISABLED'],
            "description": "Specifies whether users can restart their WorkSpace.",
        },
        "IncreaseVolumeSize": {
            "type": "string",
            "enum": ['ENABLED', 'DISABLED'],
            "description": "Specifies whether users can increase the volume size of the drives on their WorkSpace.",
        },
        "ChangeComputeType": {
            "type": "string",
            "enum": ['ENABLED', 'DISABLED'],
            "description": "Specifies whether users can change the compute type (bundle) for their WorkSpace.",
        },
        "SwitchRunningMode": {
            "type": "string",
            "enum": ['ENABLED', 'DISABLED'],
            "description": "Specifies whether users can switch the running mode of their WorkSpace.",
        },
        "RebuildWorkspace": {
            "type": "string",
            "enum": ['ENABLED', 'DISABLED'],
            "description": "Specifies whether users can rebuild the operating system of a WorkSpace to its original state.",
        },
    },
}


class WorkspacesDirectoryRegistrationProvider(ResourceProvider):
    # see https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/workspaces.html
    def __init__(self):
        super().__init__()
        self.request_schema = request_schema
        self.workspaces = None

    @property
    def region(self):
        return self.get("Region")

    @property
    def directory_id(self):
        return self.get("DirectoryId")

    def convert_property_types(self):
        log.info(self.physical_resource_id)
        log.info(self.properties)
        self.heuristic_convert_property_types(self.properties)

    def is_valid_request(self):
        if not super().is_valid_request():
            return False
        # self-service params only make sense if self-service is enabled
        if self.get('EnableSelfService') is False:
            invalid_args = {
                'RestartWorkspace',
                'IncreaseVolumeSize',
                'ChangeComputeType',
                'SwitchRunningMode',
                'RebuildWorkspace',
            }
            invalid = self.make_arguments(invalid_args)
            if invalid:
                self.fail('Invalid Args when self service is not enabled: {}'.format(', '.join(invalid.keys())))
                return False
        return True

    # API Methods
    def make_arguments(self, valid_keys):
        arguments = {
            k: v for k, v in self.properties.items()
            if k in set(self.properties.keys()).intersection(valid_keys)
        }
        return arguments

    def describe_workspace_directory(self):
        response = self.workspaces.describe_workspace_directories(DirectoryIds=[self.directory_id])
        directories = response['Directories']
        if len(directories) == 0:
            return None
        return directories[0]

    def update_attributes(self):
        # modify_selfservice_permissions
        arguments = self.make_arguments({
            'RestartWorkspace',
            'IncreaseVolumeSize',
            'ChangeComputeType',
            'SwitchRunningMode',
            'RebuildWorkspace',
        })
        if arguments:
            self.workspaces.modify_selfservice_permissions(
                ResourceId=self.directory_id,
                SelfservicePermissions=arguments,
            )
        # modify_client_properties
        arguments = self.make_arguments(
            "ReconnectEnabled",
        )
        if arguments:
            arguments = {
                'ResourceId': self.directory_id,
                '': arguments,
            }
            self.workspaces.modify_client_properties(
                ResourceId=self.directory_id,
                ClientProperties=arguments,
            )
        # modify_workspace_access_properties
        arguments = self.make_arguments({
            "DeviceTypeOsx",
            "DeviceTypeWeb",
            "DeviceTypeIos",
            "DeviceTypeAndroid",
            "DeviceTypeChromeOs",
            "DeviceTypeZeroClient",
        })
        if arguments:
            self.workspaces.modify_workspace_access_properties(
                ResourceId=self.directory_id,
                WorkspaceAccessProperties=arguments,
            )
        # modify_workspace_creation_properties
        arguments = self.make_arguments({
            "EnableInternetAccess",
            "DefaultOu",
            "CustomSecurityGroupId",
            "UserEnabledAsLocalAdministrator",
            "EnableMaintenanceMode",
        })
        if arguments:
            self.workspaces.modify_workspace_creation_properties(
                ResourceId=self.directory_id,
                WorkspaceCreationProperties=arguments,
            )

    # CloudFormation Handlers
    def create(self):
        # must defer this since region is in the payload
        self.workspaces = boto3.client("workspaces", region_name=self.region)
        try:
            # register_workspace_directory
            arguments = self.make_arguments({
                "DirectoryId",
                "SubnetIds",
                "EnableWorkDocs",
                "EnableSelfService",
                "Tenancy",
                "Tags",
            })
            self.workspaces.register_workspace_directory(**arguments)
            self.update_attributes()
            self.success("Directory Registered")
        except ClientError:
            self.physical_resource_id = "failed-to-create"
            raise

    def update(self):
        # must defer this since region is in the payload
        self.workspaces = boto3.client("workspaces", region_name=self.region)

        new_keys = set(self.properties.keys())
        old_keys = (
            set(self.old_properties.keys())
            if "OldResourceProperties" in self.request
            else new_keys
        )
        # added/removed keys
        changed_properties = new_keys.symmetric_difference(old_keys)
        # updated keys
        for name in new_keys.union(old_keys).difference({"ServiceToken"}):
            if self.get(name, None) != self.get_old(name, self.get(name)):
                changed_properties.add(name)

        if changed_properties.intersection({'DirectoryId', 'SubnetIds', 'Tenancy', 'EnableWorkDocs',
                                            'EnableSelfService', 'Tags'}):
            if changed_properties.intersection({'DirectoryId'}):
                self.create()
                self.success("Directory Registration Recreated")
            else:
                # NEVER delete in update; create a new resource and return a different physical ID
                # CF will call the delete on the old resource when the stack update succeeds
                # see https://aws.amazon.com/premiumsupport/knowledge-center/best-practices-custom-cf-lambda/
                raise NotImplementedError("Complex replacement not implemented and required by: " +
                                          f"{changed_properties.intersection({'SubnetIds', 'Tenancy'})}")
        self.update_attributes()

    def delete(self):
        if self.physical_resource_id in ['failed-to-create', 'deleted']:
            return
        # must defer this since region is in the payload
        self.workspaces = boto3.client("workspaces", region_name=self.region)
        try:
            directory = self.describe_workspace_directory()
            if directory is None:
                # this will error in the check state
                return
            # we need to make sure we're working with the right directory or we should error in a bunch of cases
            assert directory['RegistrationCode'] == self.physical_resource_id, f'Directory {self.directory_id} is no ' \
                'longer using the same registration code.  It may have been re-registered.'
            if directory['State'] in ['DEREGISTERING', 'DEREGISTERED']:
                # this is probably a retry by CF
                return
            assert directory['State'] == 'REGISTERED', f'Invalid state for deregistration:  {directory["State"]}.'
            self.workspaces.deregister_workspace_directory(DirectoryId=self.directory_id)
            self.physical_resource_id = 'deleted'
        except ClientError as error:
            self.success("Ignore failure to delete certificate {}".format(error))

    def set_response_data(self, directory):
        self.physical_resource_id = directory['RegistrationCode']
        self.set_attribute('RegistrationCode', directory['RegistrationCode'])
        self.set_attribute('CustomerUserName ', directory['CustomerUserName'])
        # workspace role and security group
        self.set_attribute('IamRoleId', directory['IamRoleId'])
        self.set_attribute('WorkspaceSecurityGroupId', directory['WorkspaceSecurityGroupId'])

    def is_ready(self):
        log.info(f'check running for action {self.request_type}')
        directory = self.describe_workspace_directory()
        log.info(directory)
        if self.request_type in ['Create', 'Update']:
            if directory is None:
                self.fail(f'{self.directory_id} not found.')
                return True
            elif directory['State'] in ['REGISTERING']:
                log.info('... found state REGISTERING')
                return False
            elif directory['State'] == 'REGISTERED':
                log.info('... found state REGISTERED')
                self.set_response_data(directory)
                self.success("Directory registered successfully.")
                return True
            else:
                self.fail(f"Directory reached an invalid registration status: {directory['State']}")
                return True
        elif self.request_type == 'Delete':
            if directory is None:
                log.info('... found no directory')
                self.success(f'Registration for {self.directory_id} no longer found.')
                return True
            # there is a delay between the API call and the state change to DEREGISTERING
            if directory['State'] in ['REGISTERED', 'DEREGISTERING']:
                log.info(f'... found directory with state {directory["State"]}')
                return False
            elif directory['State'] == 'DEREGISTERED':
                log.info('... found state DEREGISTERED')
                self.success("Directory deregistered successfully.")
                return True
            else:
                self.fail(f"Directory reached an invalid registration status: {directory['State']}")
                return True
        else:
            raise ValueError(f"No check method for Request Type: {self.request_type}")


provider = WorkspacesDirectoryRegistrationProvider()


def handler(request, context):
    return provider.handle(request, context)
