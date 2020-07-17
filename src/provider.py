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
        # try to provide reasonable responses to CF request if Resource Type is not supported
        provider = ResourceProvider()
        provider.set_request(request, context)
        if provider.request_type == 'Delete' and provider.physical_resource_id in ['create-not-found', 'deleted']:
            provider.success(f'Clean rollback when provider is not found on create.')
            provider.physical_resource_id = 'deleted'
        elif provider.request_type == 'Create':
            provider.fail(f'Provider not found on create: {request["ResourceType"]}')
            # used to indicate a clean rollback (i.e. no resources needing deleted)
            provider.physical_resource_id = 'create-not-found'
        else:
            provider.fail(f'Provider not found for resource: {request["ResourceType"]}')
        provider.send_response()
        raise KeyError(f'No handler found for resource: {request["ResourceType"]}')
