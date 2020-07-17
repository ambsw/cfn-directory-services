import logging

import boto3
from botocore.exceptions import ClientError

from cfn_resource_provider import ResourceProvider

log = logging.getLogger()


#
# The request schema defining the Resource Properties
#
request_schema = {
    "type": "object",
    "required": ["OrganizationId", "Username", "Password", "GivenName", "Surname"],
    "properties": {
        # create_user
        "OrganizationId": {
            "type": "string",
            "description": "The ID of the organization.",
        },
        "Username": {
            "type": "string",
            "description": "The login name of the user.",
        },
        "Password": {
            "type": "string",
            "description": "The password of the user.",
        },
        "GivenName": {
            "type": "string",
            "description": "The given name of the user.",
        },
        "Surname": {
            "type": "string",
            "description": "The surname of the user.",
        },
        "EmailAddress": {
            "type": "string",
            "description": "The email address of the user.",
        },
        "TimeZoneId": {
            "type": "string",
            "description": "The time zone ID of the user.",
        },
        "StorageRule": {
            "type": "object",
            "description": "The amount of storage for the user.",
        },
        # updated_user
        # GivenName
        # Surname
        "Type": {
            "type": "string",
            "enum": ['USER', 'ADMIN', 'POWERUSER', 'MINIMALUSER', 'WORKSPACESUSER'],
            "description": "The type of user.",
        },
        # StorageRule
        # TimeZoneId
        "Locale": {
            "type": "string",
            "enum": ['en', 'fr', 'ko', 'de', 'es', 'ja', 'ru', 'zh_CN', 'zh_TW', 'pt_BR', 'default'],
            "default": "default",
            "description": "The locale of the user.",
        },
        "GrantPoweruserPrivileges": {
            "type": "boolean",
            "description": "Boolean value to determine whether the user is granted Poweruser privileges.",
        },
        # TO SUPPORT WORKSPACES-ONLY
        "EnableWorkDocs": {
            "type": "boolean",
            "default": False,
            "description": "Boolean value to indicate whether or not the user is active on (and billed for) WorkDocs"
        }
    },
}


# TODO: Consider https://aws.amazon.com/blogs/desktop-and-application-streaming/automate-provisioning-of-amazon-workspaces-using-aws-lambda/
class DirectoryUserProvider(ResourceProvider):
    def __init__(self):
        super(ResourceProvider, self).__init__()
        self.request_schema = request_schema

    # Parameters
    @property
    def region(self):
        return self.get("Region")

    @property
    def organization_id(self):
        return self.get("DirectoryId")

    @property
    def username(self):
        return self.get("Username")

    @property
    def password(self):
        return self.get("Password")

    @property
    def given_name(self):
        return self.get("GivenName")

    @property
    def surname(self):
        return self.get("Surname")

    @property
    def email_address(self):
        return self.get("EmailAddress", None)

    @property
    def time_zone_id(self):
        return self.get("TimeZoneId", None)

    def convert_property_types(self):
        self.heuristic_convert_property_types(self.properties)

    def make_arguments(self, valid_keys):
        arguments = {
            k: v for k, v in self.properties.items()
            if k in set(self.properties.keys()).intersection(valid_keys)
        }
        # TODO: how do we "update" the values for keys if they're removed
        return arguments

    KEYS_CREATE = {
        "OrganizationId", "Username", "Password", "EmailAddress", "GivenName", "Surname", "TimeZoneId", "StorageRule",
    }
    KEYS_UPDATE = {
        "GivenName", "Surname", "Type", "StorageRule", "TimeZoneId", "Locale", "GrantPoweruserPrivileges",
    }

    # CloudFormation Handlers
    def create(self):
        workdocs = boto3.client("workdocs", region_name=self.region)
        try:
            arguments = self.make_arguments(self.KEYS_CREATE)
            response = workdocs.create_user(**arguments)
            self.physical_resource_id = response["User"]["Id"]
            # some keys are not available for create, but are available for update
            try:
                arguments = self.make_arguments(self.KEYS_UPDATE - self.KEYS_CREATE)
                if arguments:
                    arguments['UserId'] = self.physical_resource_id
                    workdocs.update_user(**arguments)
                # ensure we can make users who are not charged for WorkDocs
                if not self.get('EnableWorkDocs'):
                    workdocs.deactivate_user(UserId=self.physical_resource_id)
                self.success("User Created")
            except ClientError:
                workdocs.delete_user(UserId=self.physical_resource_id)
        except ClientError:
            self.physical_resource_id = "failed-to-create"
            raise

    def update(self):
        workdocs = boto3.client("workdocs", region_name=self.region)

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

        keys_replacement = self.KEYS_CREATE - self.KEYS_UPDATE
        if changed_properties.intersection(keys_replacement):
            if 'Username' in changed_properties:
                # crete and update a completely new object
                self.create()
                self.success("Replacement User Created")
            else:
                # complex replacement (delete + create)
                # TODO: figure out
                raise NotImplementedError(f"Complex replacement behavior required: "
                                          f"{changed_properties.intersection(keys_replacement)}")
        # ensure we can make users who are not charged for WorkDocs
        if changed_properties.intersection({'EnableWorkDocs'}):
            if self.get('EnableWorkDocs'):
                workdocs.activate_user(UserId=self.physical_resource_id)
            else:
                workdocs.deactivate_user(UserId=self.physical_resource_id)
        # simple update
        arguments = self.make_arguments(self.KEYS_UPDATE)
        arguments['UserId'] = self.physical_resource_id
        workdocs.update_user(**arguments)
        self.success("User Updated")

    def delete(self):
        if self.physical_resource_id in ['failed-to-create', 'deleted']:
            return
        workdocs = boto3.client("workdocs", region_name=self.region)
        users = workdocs.describe_users(UserIds=self.physical_resource_id)
        if not users:
            log.warning(f"Requested user no longer exist: {self.physical_resource_id}")
            self.success("User no longer exists.  This may be due to a cancellation request.")
            self.physical_resource_id = 'deleted'
            return
        workdocs.delete_user(UserId=self.physical_resource_id)
        self.physical_resource_id = 'deleted'


provider = DirectoryUserProvider()


def handler(request, context):
    return provider.handle(request, context)
