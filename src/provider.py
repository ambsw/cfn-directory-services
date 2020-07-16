import os
import logging
import directory_registration_provider, directory_user_provider

logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))


def handler(request, context):
    if request["ResourceType"] == "Custom::WorkspacesDirectoryRegistration":
        return directory_registration_provider.handler(request, context)
    elif request["ResourceType"] == "Custom::WorkspacesUser":
        return directory_user_provider.handler(request, context)
    else:
        raise ValueError(f'No handler found for custom resource {request["ResourceType"]}')
