import boto3
from botocore.exceptions import ClientError

from cfn_resource_provider import ResourceProvider

#
# The request schema defining the Resource Properties
#
request_schema = {
    "type": "object",
    "required": ["DirectoryId", "Username", "Password", "GivenName", "Surname"],
    "properties": {
        "DirectoryId": {
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
            "type": "dict",
            "description": "The amount of storage for the user.",
        },
    },
}


class CustomProvider(ResourceProvider):
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

    def create_user(self):
        workdocs = boto3.client("workdocs", region_name=self.region)

        arguments = self.make_arguments({
            "OrganizationId", "Username", "EmailAddress", "GivenName", "Surname", "Password", "TimeZoneId",
            "StorageRule", "IdempotencyToken", "AuthenticationToken",
        })
        response = workdocs.create_user(**arguments)
        self.physical_resource_id = response["Id"]

    def update_user(self, arguments):
        workdocs = boto3.client("workdocs", region_name=self.region)

        arguments = self.make_arguments({
            "GivenName", "Surname", "TimeZoneId", "StorageRule", "IdempotencyToken", "AuthenticationToken",
        })
        arguments['UserId'] = self.physical_resource_id
        response = workdocs.create_user(**arguments)

    def delete_user(self):
        workdocs = boto3.client("workdocs", region_name=self.region)

        response = workdocs.delete_user(UserId=self.physical_resource_id)
        self.physical_resource_id = None

    # CloudFormation Handlers
    def create(self):
        try:
            self.create_user()
        except ClientError as error:
            self.fail("{}".format(error))

    def update(self):
        new_keys = set(self.properties.keys())
        old_keys = (
            set(self.old_properties.keys())
            if "OldResourceProperties" in self.request
            else new_keys
        )

        changed_properties = new_keys.symmetric_difference(old_keys)
        for name in new_keys.union(old_keys).difference({"ServiceToken"}):
            if self.get(name, None) != self.get_old(name, self.get(name)):
                changed_properties.add(name)

        try:
            if changed_properties.intersection({'OrganizationId', 'Username'}):
                # NEVER delete in update; create a new resource and return a different physical ID
                # CF will call the delete on the old resource when the stack update succeeds
                # see https://aws.amazon.com/premiumsupport/knowledge-center/best-practices-custom-cf-lambda/
                return self.create_user()
            elif changed_properties.intersection({'EmailAddress', 'Password'}):
                # not supported
                self.fail(
                    'The following parameters may not be changed except in combination with "Username" or ' +
                    '"OrganizationId" since changing these keys triggers a full replacement: '.format(
                        ", ".join(changed_properties.intersection({'EmailAddress', 'Password'}))
                    )
                )
            elif changed_properties:
                self.update_user(changed_properties)
            else:
                self.success("nothing to change")
        except ClientError as error:
            self.fail("{}".format(error))

    def delete(self):
        if not self.physical_resource_id or not self.physical_resource_id.startswith(
            "arn:aws:acm:"
        ):
            return

        try:
            self.delete_user()
        except ClientError as error:
            self.success("Ignore failure to delete certificate {}".format(error))


provider = CustomProvider()


def handler(request, context):
    return provider.handle(request, context)
