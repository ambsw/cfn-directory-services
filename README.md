# cfn-directory-services
A set of Custom CloudFormation resources to automate Directory Services and WorkSpace provisioning.

***WARNING:  Due to limitations in the official AWS API, these resources are NOT fully reversible.  When deleting these 
resources, the WorkDocs site must be manually removed AFTER users are deleted but BEFORE the Directory Service can be 
removed.  As a result, Users SHOULD NOT be created in the same stack as the Directory Service (even though this will
not result in a `create`-time error).***

##Deploying

This package includes helper files for deployment in `/cloudformation`.  If you have Docker, the recommended procedure is:

     docker build -t cfn-workspace-provider -f Dockerfile.build .
     docker run -it cfn-workspace-provider bash
     
     (in the container)
     # configura AWS credentials e.g.
     AWS_ACCESSS_KEY_ID=...
     AWS_SECRET_ACCESS_KEY=...
     # set up deployment configurations
     AWS_REGION=us-east-1  # default is eu-central-1
     S3_BUCKET_PREFIX=myorg  # this ensures s3 buckets don't collide
     
     make -f Makefile.local deploy 
     make -f Makefile.local deploy-provider 

If you do not have docker, the make files may be run locally on Debian/Ubuntu (and possibly others) after installing 
`jq` and `zip` and pip-installing `pipenv` and `awscli`.

## Usage

A demo stack demonstrating usage can be found in `/cloudformation` and deployed using `make  -f Makefile.local demo`.

###Custom::WorkspacesDirectoryRegistration

This resource will register a Directory Service with WorkSpaces.  Due to the way API calls are partitioned, it accepts
valid combinations of the arguments from 
[RegisterWorkspaceDirectory](https://docs.aws.amazon.com/workspaces/latest/api/API_RegisterWorkspaceDirectory.html),
[ModifyClientProperties](https://docs.aws.amazon.com/workspaces/latest/api/API_ModifyClientProperties.html),
[ModifySelfservicePermissions](https://docs.aws.amazon.com/workspaces/latest/api/API_ModifySelfservicePermissions.html),
[ModifyWorkspaceAccessProperties](https://docs.aws.amazon.com/workspaces/latest/api/API_ModifyWorkspaceAccessProperties.html), and
[ModifyWorkspaceCreationProperties](https://docs.aws.amazon.com/workspaces/latest/api/API_ModifyWorkspaceCreationProperties.html).
Most combinations are valid except for disabling self-service permissions in the Register call while attempting to 
enable individual self-service permissions.

    DirectoryRegistration:
      Type: 'Custom::WorkspacesDirectoryRegistration'
      Properties:
        ServiceToken: !Sub 'arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:${FunctionName}'
        # Register Workspace Directory
        DirectoryId: !Ref SimpleDirectory
        SubnetIds: [!Ref SubnetA, !Ref SubnetB]
        EnableWorkDocs: <boolean>  # default=True
        EnableSelfService: <boolean>
        Tenancy: DEDICATED | SHARED
        Tags: <array<object>>
        # Client Properties
        ReconnectEnabled: ENABLED | DISABLED
        # Workspace Access Properties
        DeviceTypeWindows: ALLOW | DENY
        DeviceTypeOsx: ALLOW | DENY
        DeviceTypeWeb: ALLOW | DENY
        DeviceTypeIos: ALLOW | DENY
        DeviceTypeAndroid: ALLOW | DENY
        DeviceTypeChromeOs: ALLOW | DENY
        DeviceTypeZeroClient: ALLOW | DENY
        # Workspace Creation Properties
        EnableInternetAccess: <boolean>
        DefaultOu: <string>
        CustomSecurityGroupId: <string>
        UserEnabledAsLocalAdministrator: <boolean>
        EnableMaintenanceMode: <boolean>
        # Self-Service Permissions (to enable, EnableSelfService must be true)
        RestartWorkspace: ENABLED | DISABLED 
        IncreaseVolumeSize: ENABLED | DISABLED
        ChangeComputeType: ENABLED | DISABLED
        SwitchRunningMode: ENABLED | DISABLED
        RebuildWorkspace: ENABLED | DISABLED

**NOTE: As documented in the API, an `AWs::IAM::Role` called`workspaces_DefaultRole` must exist prior to creating this
resource.**

Since the Register call is asynchronous, this resource will retry for approximately 12 minutes (of the 15 minute Lambda 
timeout) and then re-invoke itself to continue to wait.  Normally registration happens in the first 30 second so this is not required.

###Custom::DirectoryUser

This resource hijacks the WorkDocs API to create Directory Service users that are available for WorkSpaces.  By default,
the resource deactivates the WorkDocs features (this is a *workspaces* provider after all), but this behavior can be
overridden (preserving the WorkDocs functionality) by setting `EnableWorkDocs` to `true`.

This resource accepts parameters from both
[CreateUser](https://docs.aws.amazon.com/workdocs/latest/APIReference/API_CreateUser.html) and
[UpdateUser](https://docs.aws.amazon.com/workdocs/latest/APIReference/API_UpdateUser.html); however, seme documented 
options have not worked in testing (e.g. setting `Type` to `WORKSPACEUSER`).

    TestUser:
      # must wait for registration!
      DependsOn: DirectoryRegistration
      Type: 'Custom::DirectoryUser'
      Properties:
        ServiceToken: !Sub 'arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:${FunctionName}'
        OrganizationId: !Ref SimpleDirectory
        Username: <string>
        Password: <string>
        GivenName: <string>
        Surname: <string>
        EmailAddress: <string>
        TimeZoneId: <string>
        StorageRule: <object>
        Type: 'USER' | 'ADMIN' | 'POWERUSER' | 'MINIMALUSER' | 'WORKSPACESUSER'
        Locale: 'en' | 'fr' | 'ko' | 'de' | 'es' | 'ja' | 'ru' | 'zh_CN' | 'zh_TW' | 'pt_BR' | 'default'
        GrantPoweruserPrivileges: <boolean>
        EnableWorkDocs: <boolean>

## Tests

Test cases are not yet implemented (see `test/`).  If you implement them, they can be run using:

    make -f Makefile.local test