import os
import logging

from cfn_resource_provider import ResourceProvider

# configure here so it cascades to nested loggers
logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))

import directory_registration_provider, directory_user_provider


def handler(request, context):
    if request["ResourceType"] == "Custom::WorkspacesDirectoryRegistration":
        return directory_registration_provider.handler(request, context)
    elif request["ResourceType"] == "Custom::DirectoryUser":
        return directory_user_provider.handler(request, context)
    else:
        # try to respond to CF request
        provider = ResourceProvider()
        provider.set_request(request, context)
        provider.fail(f'no provider found for resource: {request["ResourceType"]}')
        provider.send_response()
        raise ValueError(f'No handler found for resource: {request["ResourceType"]}')
